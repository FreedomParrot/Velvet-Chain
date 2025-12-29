#!/usr/bin/env python3
"""
Velvet Chain - Decentralized EVM-Compatible Blockchain
Community Mining Edition - SYNC FIX

Key fixes:
- Better initial sync with retries
- Stop mining when longer chain detected
- Improved peer connection handling
"""

import argparse
import hashlib
import json
import time
import threading
from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import sys

# ==================== VELVET CHAIN CONFIGURATION ====================

CHAIN_ID = 16523431
VERSION = "1.0.2-fixed"

GENESIS_ADDRESS = "0xd7e0aa3f99cc4addfd6797897df438a146a9e328"
INITIAL_SUPPLY = 1000000 * 10**18
GENESIS_TIMESTAMP = 1735488000
GENESIS_HASH = "0xa1c02b7107092ccef5e3a48711178e27018d74558fbb8cb564e235a4f2788eb1"

BLOCK_TIME = 10
MINING_REWARD = 50 * 10**18
DIFFICULTY_ADJUSTMENT = 100
TARGET_DIFFICULTY = 5  # Increased from 3 to 5 (much harder)

DEFAULT_PORT = 8545
BOOTSTRAP_NODES = ["http://173.255.229.107:8545"]

MAX_PEERS = 25
PEER_DISCOVERY_INTERVAL = 30
SYNC_INTERVAL = 15  # Check every 15 seconds instead of 30
PEER_ANNOUNCE_INTERVAL = 45

# ==================== BLOCKCHAIN CORE ====================

class Transaction:
    def __init__(self, nonce, gas_price, gas_limit, to, value, data, v=0, r=0, s=0, from_addr=None):
        self.nonce = nonce
        self.gas_price = gas_price
        self.gas_limit = gas_limit
        self.to = to
        self.value = value
        self.data = data
        self.v = v
        self.r = r
        self.s = s
        self.from_addr = from_addr
        self.hash = self._calculate_hash()
    
    def _calculate_hash(self):
        tx_data = {
            'nonce': self.nonce,
            'gasPrice': self.gas_price,
            'gas': self.gas_limit,
            'to': self.to,
            'value': self.value,
            'data': self.data,
            'v': self.v,
            'r': self.r,
            's': self.s
        }
        return '0x' + hashlib.sha256(json.dumps(tx_data, sort_keys=True).encode()).hexdigest()
    
    def to_dict(self):
        return {
            'hash': self.hash,
            'nonce': hex(self.nonce),
            'gasPrice': hex(self.gas_price),
            'gas': hex(self.gas_limit),
            'to': self.to,
            'from': self.from_addr or '0x0',
            'value': hex(self.value),
            'data': self.data,
            'v': hex(self.v),
            'r': hex(self.r),
            's': hex(self.s)
        }
    
    @staticmethod
    def from_dict(data):
        return Transaction(
            nonce=int(data['nonce'], 16),
            gas_price=int(data['gasPrice'], 16),
            gas_limit=int(data['gas'], 16),
            to=data['to'],
            value=int(data['value'], 16),
            data=data['data'],
            v=int(data['v'], 16),
            r=int(data['r'], 16),
            s=int(data['s'], 16),
            from_addr=data.get('from', '0x0')
        )

class Block:
    def __init__(self, number, timestamp, transactions, previous_hash, miner, difficulty=TARGET_DIFFICULTY):
        self.number = number
        self.timestamp = timestamp
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.miner = miner
        self.difficulty = difficulty
        self.nonce = 0
        self.gas_used = sum(21000 for _ in transactions)
        self.gas_limit = 8000000
        self.hash = None
    
    def calculate_hash(self):
        block_data = {
            'number': self.number,
            'timestamp': self.timestamp,
            'transactions': [tx.hash for tx in self.transactions],
            'previous_hash': self.previous_hash,
            'miner': self.miner,
            'nonce': self.nonce,
            'difficulty': self.difficulty
        }
        return '0x' + hashlib.sha256(json.dumps(block_data, sort_keys=True).encode()).hexdigest()
    
    def mine(self, should_continue_callback):
        target = '0' * self.difficulty
        start_time = time.time()
        
        while should_continue_callback():
            self.hash = self.calculate_hash()
            if self.hash[2:2+self.difficulty] == target:
                elapsed = time.time() - start_time
                hashrate = self.nonce / elapsed if elapsed > 0 else 0
                print(f"\n⛏️  Block #{self.number} mined! Hash: {self.hash[:16]}... ({hashrate:.0f} H/s)")
                sys.stdout.flush()
                return True
            self.nonce += 1
            
            if self.nonce % 50000 == 0:
                elapsed = time.time() - start_time
                hashrate = self.nonce / elapsed if elapsed > 0 else 0
                print(f"   Mining block #{self.number}... {self.nonce:,} attempts ({hashrate:.0f} H/s)", end='\r')
                sys.stdout.flush()
        
        return False  # Mining was interrupted
    
    def to_dict(self):
        return {
            'number': hex(self.number),
            'hash': self.hash,
            'parentHash': self.previous_hash,
            'nonce': hex(self.nonce),
            'timestamp': hex(self.timestamp),
            'miner': self.miner,
            'difficulty': hex(self.difficulty),
            'gasLimit': hex(self.gas_limit),
            'gasUsed': hex(self.gas_used),
            'transactions': [tx.to_dict() for tx in self.transactions],
            'transactionsRoot': '0x56e81f171bcc55a6ff8345e692c0f86e5b48e01b996cadc001622fb5e363b421',
            'stateRoot': '0x0',
            'receiptsRoot': '0x56e81f171bcc55a6ff8345e692c0f86e5b48e01b996cadc001622fb5e363b421'
        }
    
    @staticmethod
    def from_dict(data):
        txs = [Transaction.from_dict(tx) for tx in data['transactions']]
        block = Block(
            number=int(data['number'], 16),
            timestamp=int(data['timestamp'], 16),
            transactions=txs,
            previous_hash=data['parentHash'],
            miner=data['miner'],
            difficulty=int(data['difficulty'], 16)
        )
        block.nonce = int(data['nonce'], 16)
        block.hash = data['hash']
        block.gas_used = int(data['gasUsed'], 16)
        block.gas_limit = int(data['gasLimit'], 16)
        return block

class VelvetChain:
    def __init__(self, miner_address=None, is_bootstrap=False):
        self.chain = []
        self.pending_transactions = []
        self.balances = {}
        self.nonces = {}
        self.miner_address = miner_address
        self.is_mining = False
        self.mining_should_stop = False  # NEW: flag to stop mining
        self.difficulty = TARGET_DIFFICULTY
        self.total_difficulty = 0
        self.mining_thread = None
        self.chain_lock = threading.Lock()
        self.is_bootstrap = is_bootstrap
        self.synced = False
        
        if self.is_bootstrap and len(self.chain) == 0:
            self._create_genesis()
            self.synced = True
    
    def _create_genesis(self):
        genesis = Block(0, GENESIS_TIMESTAMP, [], '0x' + '0' * 64, GENESIS_ADDRESS, difficulty=1)
        genesis.nonce = 0
        genesis.hash = genesis.calculate_hash()
        
        print(f"🔐 Genesis hash: {genesis.hash}")
        
        if genesis.hash != GENESIS_HASH:
            print(f"⚠️  Genesis hash mismatch - using hardcoded genesis")
            genesis.hash = GENESIS_HASH
        
        self.chain.append(genesis)
        self.balances[GENESIS_ADDRESS.lower()] = INITIAL_SUPPLY
        self.nonces[GENESIS_ADDRESS.lower()] = 0
        
        print(f"✅ Genesis block created")
        print(f"💰 Initial supply: {INITIAL_SUPPLY / 10**18:,.0f} VELVET → {GENESIS_ADDRESS}")
    
    def get_latest_block(self):
        with self.chain_lock:
            return self.chain[-1] if self.chain else None
    
    def add_transaction(self, tx):
        if tx.value < 0:
            return None
        
        sender = tx.from_addr
        if sender:
            sender = sender.lower()
            if self.balances.get(sender, 0) < tx.value:
                return None
        
        self.pending_transactions.append(tx)
        return tx.hash
    
    def mine_block(self):
        if not self.miner_address:
            return None
        
        with self.chain_lock:
            latest = self.chain[-1]
            mining_block_num = latest.number + 1
            
            coinbase_tx = Transaction(
                nonce=0, gas_price=0, gas_limit=0,
                to=self.miner_address, value=MINING_REWARD, data='0x',
                from_addr='0x0000000000000000000000000000000000000000'
            )
            
            block_txs = [coinbase_tx] + self.pending_transactions[:100]
            difficulty = self._calculate_difficulty()
            
            new_block = Block(
                number=mining_block_num,
                timestamp=int(time.time()),
                transactions=block_txs,
                previous_hash=latest.hash,
                miner=self.miner_address,
                difficulty=difficulty
            )
        
        print(f"⛏️  Mining block #{new_block.number} (difficulty: {difficulty})...")
        sys.stdout.flush()
        
        self.mining_should_stop = False
        
        # Pass callback to check if we should continue mining
        success = new_block.mine(lambda: not self.mining_should_stop and self.is_mining)
        
        if not success:
            print(f"\n⚠️  Mining interrupted for block #{new_block.number}")
            return None
        
        with self.chain_lock:
            # CRITICAL: Check if chain changed while we were mining
            current_latest = self.chain[-1]
            if current_latest.hash != new_block.previous_hash:
                print(f"\n⚠️  Block #{new_block.number} discarded - peer block arrived first")
                return None
            
            # Apply transactions
            for tx in block_txs:
                if tx == coinbase_tx:
                    addr = self.miner_address.lower()
                    self.balances[addr] = self.balances.get(addr, 0) + MINING_REWARD
                else:
                    sender = tx.from_addr.lower() if tx.from_addr else None
                    recipient = tx.to.lower() if tx.to else None
                    
                    if sender and recipient:
                        self.balances[sender] = self.balances.get(sender, 0) - tx.value
                        self.balances[recipient] = self.balances.get(recipient, 0) + tx.value
                        self.nonces[sender] = self.nonces.get(sender, 0) + 1
            
            self.chain.append(new_block)
            self.total_difficulty += 2 ** difficulty
            self.pending_transactions = self.pending_transactions[100:]
        
        print(f"✅ Block #{new_block.number} added to chain")
        print(f"💰 Mining reward: {MINING_REWARD / 10**18} VELVET → {self.miner_address}\n")
        
        return new_block
    
    def _calculate_difficulty(self):
        if len(self.chain) < DIFFICULTY_ADJUSTMENT:
            return TARGET_DIFFICULTY
        
        recent_blocks = self.chain[-DIFFICULTY_ADJUSTMENT:]
        time_taken = recent_blocks[-1].timestamp - recent_blocks[0].timestamp
        expected_time = BLOCK_TIME * (DIFFICULTY_ADJUSTMENT - 1)
        
        if time_taken < expected_time * 0.75:
            return min(TARGET_DIFFICULTY + 1, 10)
        elif time_taken > expected_time * 1.25:
            return max(TARGET_DIFFICULTY - 1, 2)
        
        return TARGET_DIFFICULTY
    
    def start_mining(self):
        if self.is_mining:
            return
        
        if not self.is_bootstrap and not self.synced:
            print("⚠️  Cannot start mining - waiting for blockchain sync...")
            return
        
        self.is_mining = True
        
        def mining_loop():
            print(f"⛏️  Mining started! Rewards → {self.miner_address}")
            print(f"🎯 Target: {BLOCK_TIME}s/block | Reward: {MINING_REWARD / 10**18} VELVET\n")
            sys.stdout.flush()
            time.sleep(2)
            
            while self.is_mining:
                try:
                    # Wait a bit to allow peer blocks to arrive before starting mining
                    print("⏳ Checking for peer blocks...")
                    time.sleep(3)  # Give network time to propagate
                    
                    block = self.mine_block()
                    if block and p2p_network:
                        p2p_network.broadcast_block(block)
                    
                    # Small delay after broadcasting
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"❌ Mining error: {e}")
                    time.sleep(5)
        
        self.mining_thread = threading.Thread(target=mining_loop, daemon=True)
        self.mining_thread.start()
    
    def stop_mining(self):
        self.is_mining = False
        self.mining_should_stop = True
    
    def get_balance(self, address):
        return self.balances.get(address.lower(), 0)
    
    def get_nonce(self, address):
        return self.nonces.get(address.lower(), 0)
    
    def replace_chain(self, new_chain_data):
        try:
            new_blocks = [Block.from_dict(b) for b in new_chain_data]
            
            # ONLY replace if longer
            if len(new_blocks) <= len(self.chain):
                return False
            
            # Validate genesis
            if new_blocks[0].hash != GENESIS_HASH:
                print(f"❌ REJECTED: Invalid genesis!")
                print(f"   Expected: {GENESIS_HASH}")
                print(f"   Got: {new_blocks[0].hash}")
                return False
            
            # Validate chain integrity
            for i in range(1, len(new_blocks)):
                if new_blocks[i].previous_hash != new_blocks[i-1].hash:
                    print("❌ Invalid chain: broken links")
                    return False
            
            # Stop mining before replacing chain
            was_mining = self.is_mining
            if was_mining:
                print("⏸️  Pausing mining for chain sync...")
                self.mining_should_stop = True
                time.sleep(0.5)  # Let current mining iteration finish
            
            with self.chain_lock:
                print(f"🔄 Syncing {len(new_blocks)} blocks...")
                
                self.chain = new_blocks
                self.balances = {GENESIS_ADDRESS.lower(): INITIAL_SUPPLY}
                self.nonces = {GENESIS_ADDRESS.lower(): 0}
                
                # Replay all transactions
                for block in self.chain[1:]:
                    for tx in block.transactions:
                        sender = tx.from_addr.lower() if tx.from_addr else None
                        recipient = tx.to.lower() if tx.to else None
                        
                        if sender == '0x0000000000000000000000000000000000000000':
                            self.balances[recipient] = self.balances.get(recipient, 0) + tx.value
                        elif sender and recipient:
                            self.balances[sender] = self.balances.get(sender, 0) - tx.value
                            self.balances[recipient] = self.balances.get(recipient, 0) + tx.value
                            self.nonces[sender] = self.nonces.get(sender, 0) + 1
                
                print(f"✅ Chain synced to height {len(self.chain)-1}!")
                self.synced = True
            
            # Resume mining if it was active
            if was_mining:
                print("▶️  Resuming mining...")
            
            return True
                
        except Exception as e:
            print(f"❌ Sync error: {e}")
            return False
    
    def add_block_from_peer(self, block_data):
        try:
            new_block = Block.from_dict(block_data)
            
            with self.chain_lock:
                if len(self.chain) == 0:
                    return False
                
                latest = self.chain[-1]
                
                print(f"📨 Peer block #{new_block.number} | Our height: #{latest.number}")
                
                # EXACT MATCH - next block
                if new_block.previous_hash == latest.hash and new_block.number == latest.number + 1:
                    target = '0' * new_block.difficulty
                    if not new_block.hash.startswith('0x' + target):
                        return False
                    
                    if self.is_mining:
                        self.mining_should_stop = True
                    
                    for tx in new_block.transactions:
                        sender = tx.from_addr.lower() if tx.from_addr else None
                        recipient = tx.to.lower() if tx.to else None
                        
                        if sender == '0x0000000000000000000000000000000000000000':
                            self.balances[recipient] = self.balances.get(recipient, 0) + tx.value
                        elif sender and recipient:
                            self.balances[sender] = self.balances.get(sender, 0) - tx.value
                            self.balances[recipient] = self.balances.get(recipient, 0) + tx.value
                            self.nonces[sender] = self.nonces.get(sender, 0) + 1
                    
                    self.chain.append(new_block)
                    print(f"   ✅ Accepted from peer")
                    return True
                
                # Same block number as our latest - FORK!
                elif new_block.number == latest.number:
                    if new_block.hash != latest.hash:
                        print(f"   🔀 FORK! Different block #{new_block.number}")
                        print(f"      Our hash: {latest.hash[:16]}...")
                        print(f"      Peer hash: {new_block.hash[:16]}...")
                        return "FORK_DETECTED"
                    else:
                        print(f"   ⏭️  Duplicate block (same hash)")
                        return False
                
                # OLD BLOCK - Check if we have different history
                elif new_block.number < latest.number:
                    if new_block.number < len(self.chain):
                        our_block = self.chain[new_block.number]
                        if our_block.hash != new_block.hash:
                            print(f"   🔀 FORK at block #{new_block.number}!")
                            print(f"      Our hash: {our_block.hash[:16]}...")
                            print(f"      Peer hash: {new_block.hash[:16]}...")
                            return "FORK_DETECTED"
                    print(f"   ⏭️  Old block rejected")
                    return False
                
                # FUTURE BLOCK - we're behind
                elif new_block.number > latest.number + 1:
                    print(f"   ⚠️  Gap! Peer is {new_block.number - latest.number} blocks ahead")
                    return "NEED_SYNC"
                
                return False
                
        except Exception as e:
            print(f"❌ Block validation error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_block_by_number(self, number):
        with self.chain_lock:
            if number < len(self.chain):
                return self.chain[number]
        return None
    
    def get_transaction_by_hash(self, tx_hash):
        with self.chain_lock:
            for block in self.chain:
                for tx in block.transactions:
                    if tx.hash == tx_hash:
                        return tx, block
        return None, None

# ==================== P2P NETWORKING ====================

class P2PNetwork:
    def __init__(self, port, blockchain, manual_peer=None):
        self.port = port
        self.blockchain = blockchain
        self.peers = set()
        self.my_address = self._get_my_address()
        self.manual_peer = manual_peer
    
    def _get_my_address(self):
        try:
            response = requests.get('https://api.ipify.org?format=json', timeout=5)
            public_ip = response.json()['ip']
            return f"http://{public_ip}:{self.port}"
        except:
            return f"http://localhost:{self.port}"
    
    def start(self):
        threading.Thread(target=self._discover_peers, daemon=True).start()
        threading.Thread(target=self._sync_chain, daemon=True).start()
        threading.Thread(target=self._announce_to_peers, daemon=True).start()
        print(f"🌐 P2P started on port {self.port}")
    
    def _discover_peers(self):
        while True:
            try:
                peers_to_try = []
                if self.manual_peer:
                    peers_to_try.append(self.manual_peer)
                peers_to_try.extend(BOOTSTRAP_NODES)
                
                for bootstrap in peers_to_try:
                    if bootstrap not in self.peers and bootstrap != self.my_address:
                        try:
                            response = requests.get(f"{bootstrap}/api/peers", timeout=5)
                            if response.status_code == 200:
                                if bootstrap not in self.peers:
                                    self.peers.add(bootstrap)
                                    print(f"✅ Connected to peer: {bootstrap}")
                                
                                peer_list = response.json()
                                for peer in peer_list[:MAX_PEERS]:
                                    if peer not in self.peers and peer != self.my_address and len(self.peers) < MAX_PEERS:
                                        self.peers.add(peer)
                        except:
                            pass
                
                time.sleep(PEER_DISCOVERY_INTERVAL)
            except:
                time.sleep(PEER_DISCOVERY_INTERVAL)
    
    def _sync_chain(self):
        # Initial sync with better retry logic
        if not self.blockchain.is_bootstrap and not self.blockchain.synced:
            print("🔄 Starting initial blockchain sync...")
            
            for attempt in range(10):  # More attempts
                time.sleep(2)  # Wait a bit before each attempt
                
                peers_to_try = []
                if self.manual_peer:
                    peers_to_try.append(self.manual_peer)
                peers_to_try.extend(BOOTSTRAP_NODES)
                
                for peer in peers_to_try:
                    try:
                        print(f"   Attempting sync from {peer}...")
                        response = requests.get(f"{peer}/api/chain", timeout=15)
                        
                        if response.status_code == 200:
                            peer_chain = response.json()
                            
                            if len(peer_chain) > 0:
                                print(f"   📥 Received {len(peer_chain)} blocks")
                                
                                if self.blockchain.replace_chain(peer_chain):
                                    print(f"✅ Successfully synced from {peer}!")
                                    time.sleep(2)
                                    break
                    except Exception as e:
                        print(f"   ❌ Sync failed: {e}")
                
                if self.blockchain.synced:
                    break
                
                if attempt < 9:
                    wait_time = min(5 * (attempt + 1), 30)
                    print(f"   ⏳ Retry {attempt+1}/10 in {wait_time}s...")
                    time.sleep(wait_time)
            
            if not self.blockchain.synced:
                print("❌ Could not sync blockchain after 10 attempts")
                print("   Make sure bootstrap node is running and accessible")
        
        # Continuous sync
        while True:
            try:
                time.sleep(SYNC_INTERVAL)
                
                for peer in list(self.peers):
                    try:
                        response = requests.get(f"{peer}/api/chain", timeout=10)
                        if response.status_code == 200:
                            peer_chain = response.json()
                            
                            our_height = len(self.blockchain.chain)
                            peer_height = len(peer_chain)
                            
                            # If peer has longer chain, sync it
                            if peer_height > our_height:
                                print(f"\n🔄 Peer has longer chain ({peer_height} vs {our_height})")
                                if self.blockchain.replace_chain(peer_chain):
                                    print(f"✅ Synced to peer's chain!")
                                    break
                            # If same height but we detect fork, compare
                            elif peer_height == our_height and our_height > 1:
                                # Check if last block matches
                                peer_last = peer_chain[-1]
                                our_last = self.blockchain.chain[-1].to_dict()
                                
                                if peer_last['hash'] != our_last['hash']:
                                    print(f"\n🔀 FORK DETECTED! Same height ({our_height}) but different blocks")
                                    print(f"   Comparing chains...")
                                    # For now, accept the peer's chain (in real blockchain, would use difficulty)
                                    if self.blockchain.replace_chain(peer_chain):
                                        print(f"✅ Resolved fork - using peer's chain")
                                        break
                    except Exception as e:
                        # Remove dead peers
                        self.peers.discard(peer)
            except:
                pass
    
    def _announce_to_peers(self):
        while True:
            try:
                time.sleep(PEER_ANNOUNCE_INTERVAL)
                for peer in list(self.peers):
                    try:
                        requests.post(f"{peer}/api/peer/announce", 
                                    json={'peer': self.my_address}, timeout=5)
                    except:
                        pass
            except:
                pass
    
    def broadcast_block(self, block):
        for peer in list(self.peers):
            try:
                requests.post(f"{peer}/api/block", json=block.to_dict(), timeout=5)
            except:
                pass
    
    def add_peer(self, peer_url):
        if peer_url not in self.peers and peer_url != self.my_address and len(self.peers) < MAX_PEERS:
            self.peers.add(peer_url)
            return True
        return False
    
    def force_sync(self):
        """Force an immediate chain sync when fork is detected"""
        print("🔄 Force sync initiated...")
        for peer in list(self.peers):
            try:
                response = requests.get(f"{peer}/api/chain", timeout=10)
                if response.status_code == 200:
                    peer_chain = response.json()
                    if len(peer_chain) > len(self.blockchain.chain):
                        print(f"   Found longer chain ({len(peer_chain)} blocks)")
                        self.blockchain.replace_chain(peer_chain)
                        return
            except:
                pass
        print("   No longer chain found")

# ==================== API ====================

app = Flask(__name__)
CORS(app)

blockchain = None
p2p_network = None

@app.route('/', methods=['POST'])
def json_rpc():
    data = request.json
    method = data.get('method')
    params = data.get('params', [])
    rpc_id = data.get('id', 1)
    
    try:
        if method == 'eth_chainId':
            result = hex(CHAIN_ID)
        elif method == 'eth_blockNumber':
            result = hex(blockchain.get_latest_block().number)
        elif method == 'eth_getBalance':
            address = params[0] if params else None
            result = hex(blockchain.get_balance(address)) if address else '0x0'
        elif method == 'eth_getTransactionCount':
            address = params[0] if params else None
            result = hex(blockchain.get_nonce(address)) if address else '0x0'
        elif method == 'eth_gasPrice':
            result = '0x3b9aca00'
        elif method == 'net_version':
            result = str(CHAIN_ID)
        elif method == 'eth_accounts':
            result = []
        elif method == 'eth_getBlockByNumber':
            block_param = params[0] if params else 'latest'
            if block_param == 'latest':
                block = blockchain.get_latest_block()
            else:
                block_num = int(block_param, 16)
                block = blockchain.get_block_by_number(block_num)
            result = block.to_dict() if block else None
        elif method == 'web3_clientVersion':
            result = f'VelvetChain/v{VERSION}'
        elif method == 'net_peerCount':
            result = hex(len(p2p_network.peers))
        else:
            return jsonify({'jsonrpc': '2.0', 'id': rpc_id, 
                          'error': {'code': -32601, 'message': f'Method {method} not found'}})
        
        return jsonify({'jsonrpc': '2.0', 'id': rpc_id, 'result': result})
    except Exception as e:
        return jsonify({'jsonrpc': '2.0', 'id': rpc_id,
                       'error': {'code': -32603, 'message': str(e)}})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    latest = blockchain.get_latest_block()
    return jsonify({
        'blockHeight': latest.number if latest else 0,
        'difficulty': blockchain.difficulty,
        'pendingTransactions': len(blockchain.pending_transactions),
        'chainId': CHAIN_ID,
        'peers': len(p2p_network.peers),
        'version': VERSION,
        'isMining': blockchain.is_mining,
        'synced': blockchain.synced
    })

@app.route('/api/chain', methods=['GET'])
def get_chain():
    limit = request.args.get('limit', 1000, type=int)
    with blockchain.chain_lock:
        return jsonify([block.to_dict() for block in blockchain.chain[-limit:]])

@app.route('/api/peers', methods=['GET'])
def get_peers():
    return jsonify(list(p2p_network.peers))

@app.route('/api/address/<address>', methods=['GET'])
def get_address(address):
    return jsonify({
        'address': address,
        'balance': blockchain.get_balance(address),
        'balanceVELVET': blockchain.get_balance(address) / 10**18,
        'nonce': blockchain.get_nonce(address)
    })

@app.route('/api/block', methods=['POST'])
def receive_block():
    try:
        block_data = request.json
        print(f"\n📨 Received block #{int(block_data['number'], 16)}")
        result = blockchain.add_block_from_peer(block_data)
        
        print(f"   Result: {result}")
        
        # If fork detected or need sync, trigger it in background
        if result == "FORK_DETECTED" or result == "NEED_SYNC":
            threading.Thread(target=p2p_network.force_sync, daemon=True).start()
            return jsonify({'status': 'sync_triggered'})
        
        return jsonify({'status': 'accepted' if result else 'rejected'})
    except Exception as e:
        print(f"❌ API Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/peer/announce', methods=['POST'])
def announce_peer():
    peer_url = request.json.get('peer')
    if peer_url and peer_url != p2p_network.my_address:
        p2p_network.add_peer(peer_url)
    return jsonify({'status': 'ok'})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'blockHeight': blockchain.get_latest_block().number if blockchain.chain else 0,
        'peers': len(p2p_network.peers),
        'synced': blockchain.synced
    })

# ==================== MAIN ====================

def main():
    global blockchain, p2p_network
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=DEFAULT_PORT)
    parser.add_argument('--mine', action='store_true')
    parser.add_argument('--wallet', type=str)
    parser.add_argument('--peer', type=str)
    parser.add_argument('--bootstrap', action='store_true')
    args = parser.parse_args()
    
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║              🔗 VELVET CHAIN v1.0.2-fixed              ║
    ║         Decentralized EVM-Compatible Blockchain          ║
    ║                  SYNC ISSUES RESOLVED                    ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    if args.mine and not args.wallet:
        print("❌ --wallet required for mining")
        sys.exit(1)
    
    if args.wallet and not (args.wallet.startswith('0x') and len(args.wallet) == 42):
        print("❌ Invalid wallet format")
        sys.exit(1)
    
    blockchain = VelvetChain(miner_address=args.wallet, is_bootstrap=args.bootstrap)
    p2p_network = P2PNetwork(args.port, blockchain, manual_peer=args.peer)
    p2p_network.start()
    
    # Wait for sync if not bootstrap
    if not args.bootstrap:
        print("⏳ Waiting for initial sync...")
        for i in range(120):  # 2 minutes max wait
            if blockchain.synced:
                break
            time.sleep(1)
            if i % 10 == 0 and i > 0:
                print(f"   Still syncing... ({i}s)")
    
    if args.mine:
        if blockchain.synced or args.bootstrap:
            blockchain.start_mining()
        else:
            print("❌ Cannot mine - blockchain not synced!")
            print("   Make sure bootstrap node is accessible")
    
    print(f"\n{'='*60}")
    print(f"🚀 Node Running")
    print(f"{'='*60}")
    print(f"RPC:      http://localhost:{args.port}")
    print(f"Chain ID: {CHAIN_ID}")
    print(f"Type:     {'🏛️  BOOTSTRAP' if args.bootstrap else '🌐 Regular'}")
    print(f"Mining:   {'✅' if args.mine and blockchain.is_mining else '❌'}")
    print(f"Synced:   {'✅' if blockchain.synced else '❌'}")
    if args.wallet:
        print(f"Wallet:   {args.wallet}")
        print(f"Balance:  {blockchain.get_balance(args.wallet) / 10**18:,.2f} VELVET")
    print(f"Height:   {blockchain.get_latest_block().number if blockchain.chain else 0}")
    print(f"Peers:    {len(p2p_network.peers)}")
    print(f"{'='*60}\n")
    
    if args.bootstrap:
        print("🏛️  BOOTSTRAP NODE - Others connect with:")
        print("   --peer http://173.255.229.107:8545\n")
    
    try:
        app.run(host='0.0.0.0', port=args.port, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        if blockchain.is_mining:
            blockchain.stop_mining()
        sys.exit(0)

if __name__ == '__main__':
    main()
