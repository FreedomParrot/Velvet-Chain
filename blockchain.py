#!/usr/bin/env python3
"""
Velvet Chain - Decentralized EVM-Compatible Blockchain
Community Mining Edition - Fixed P2P Version

Installation:
    pip install flask flask-cors requests web3 eth-account

Quick Start:
    # First Bootstrap Node (on 173.255.229.107)
    python node.py --mine --wallet YOUR_WALLET_ADDRESS
    
    # Additional Nodes (connect to bootstrap)
    python node.py --mine --wallet YOUR_WALLET_ADDRESS --peer http://173.255.229.107:8545
    
    # Full Node (No Mining)
    python node.py --peer http://173.255.229.107:8545
"""

import argparse
import hashlib
import json
import time
import threading
import socket
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import requests
from web3 import Web3
from eth_account import Account
import os
import sys

# ==================== VELVET CHAIN CONFIGURATION ====================

CHAIN_ID = 16523431
NETWORK_MAGIC = b"VELVET"
VERSION = "1.0.1"

# Genesis Configuration
GENESIS_ADDRESS = "0xd7e0aa3f99cc4addfd6797897df438a146a9e328"  # OWNER WALLET - DO NOT CHANGE
INITIAL_SUPPLY = 1000000 * 10**18  # 1 million VELVET
GENESIS_TIMESTAMP = 1735488000

# Mining Configuration
BLOCK_TIME = 10  # Target: 10 seconds per block
MINING_REWARD = 50 * 10**18  # 50 VELVET per block
DIFFICULTY_ADJUSTMENT = 100
TARGET_DIFFICULTY = 3  # Lower = faster mining (3 zeros instead of 4)

# Network Configuration
DEFAULT_PORT = 8545
BOOTSTRAP_NODES = [
    "http://173.255.229.107:8545",  # Primary bootstrap node
]

# P2P Configuration
MAX_PEERS = 25
PEER_DISCOVERY_INTERVAL = 30
SYNC_INTERVAL = 60
PEER_ANNOUNCE_INTERVAL = 45

# ==================== BLOCKCHAIN CORE ====================

class Transaction:
    """EVM-compatible transaction"""
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
        """Reconstruct transaction from dict"""
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
    """Blockchain block with Proof of Work"""
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
    
    def mine(self):
        """Proof of Work mining"""
        target = '0' * self.difficulty
        start_time = time.time()
        
        print(f"[DEBUG] Starting PoW mining, target: {target}, difficulty: {self.difficulty}")
        sys.stdout.flush()
        
        while True:
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
        """Reconstruct block from dict"""
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
    """Decentralized Blockchain Core"""
    def __init__(self, miner_address=None, is_bootstrap=False):
        self.chain = []
        self.pending_transactions = []
        self.balances = {}
        self.nonces = {}
        self.miner_address = miner_address
        self.is_mining = False
        self.difficulty = TARGET_DIFFICULTY
        self.total_difficulty = 0
        self.mining_thread = None
        self.chain_lock = threading.Lock()
        self.is_bootstrap = is_bootstrap
        self.synced = False
        
        # Only bootstrap node creates genesis
        if self.is_bootstrap and len(self.chain) == 0:
            self._create_genesis()
            self.synced = True
    
    def _create_genesis(self):
        """Create genesis block"""
        genesis = Block(0, GENESIS_TIMESTAMP, [], '0x' + '0' * 64, GENESIS_ADDRESS, difficulty=1)
        genesis.hash = genesis.calculate_hash()
        self.chain.append(genesis)
        
        self.balances[GENESIS_ADDRESS.lower()] = INITIAL_SUPPLY
        self.nonces[GENESIS_ADDRESS.lower()] = 0
        
        print(f"✅ Genesis block created")
        print(f"💰 Initial supply: {INITIAL_SUPPLY / 10**18:,.0f} VELVET → {GENESIS_ADDRESS}")
    
    def get_latest_block(self):
        with self.chain_lock:
            return self.chain[-1] if self.chain else None
    
    def add_transaction(self, tx):
        """Add transaction to mempool"""
        if tx.value < 0:
            return None
        
        sender = tx.from_addr
        if sender:
            sender = sender.lower()
            if self.balances.get(sender, 0) < tx.value:
                print(f"❌ Insufficient balance: {sender}")
                return None
        
        self.pending_transactions.append(tx)
        print(f"📝 Transaction added: {tx.hash[:16]}...")
        return tx.hash
    
    def mine_block(self):
        """Mine a new block with pending transactions"""
        if not self.miner_address:
            print("❌ No miner address set")
            return None
        
        print(f"[DEBUG] Starting to mine block...")
        sys.stdout.flush()
        
        with self.chain_lock:
            latest = self.chain[-1]  # Direct access, we already have the lock
            print(f"[DEBUG] Latest block: #{latest.number}")
            sys.stdout.flush()
            
            coinbase_tx = Transaction(
                nonce=0,
                gas_price=0,
                gas_limit=0,
                to=self.miner_address,
                value=MINING_REWARD,
                data='0x',
                from_addr='0x0000000000000000000000000000000000000000'
            )
            print(f"[DEBUG] Coinbase tx created")
            sys.stdout.flush()
            
            block_txs = [coinbase_tx] + self.pending_transactions[:100]
            difficulty = self._calculate_difficulty()
            print(f"[DEBUG] Difficulty calculated: {difficulty}")
            sys.stdout.flush()
            
            new_block = Block(
                number=latest.number + 1,
                timestamp=int(time.time()),
                transactions=block_txs,
                previous_hash=latest.hash,
                miner=self.miner_address,
                difficulty=difficulty
            )
            print(f"[DEBUG] New block created: #{new_block.number}")
            sys.stdout.flush()
        
        print(f"⛏️  Mining block #{new_block.number} (difficulty: {difficulty})...")
        sys.stdout.flush()
        
        try:
            print(f"[DEBUG] About to call new_block.mine()")
            sys.stdout.flush()
            new_block.mine()
            print(f"[DEBUG] Mining completed!")
            sys.stdout.flush()
        except Exception as e:
            print(f"[DEBUG] Mining exception: {e}")
            import traceback
            traceback.print_exc()
            sys.stdout.flush()
            return None
        
        with self.chain_lock:
            # Re-check chain hasn't changed
            if self.chain[-1].hash != new_block.previous_hash:
                print("⚠️  Chain changed during mining, discarding block")
                return None
            
            # Process transactions
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
        """Adjust difficulty based on block time"""
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
        """Start mining loop"""
        if self.is_mining:
            return
        
        # Non-bootstrap nodes must sync first
        if not self.is_bootstrap and not self.synced:
            print("⚠️  Cannot start mining - waiting for blockchain sync...")
            return
        
        self.is_mining = True
        
        def mining_loop():
            print(f"⛏️  Mining thread started! Rewards → {self.miner_address}")
            print(f"🎯 Target block time: {BLOCK_TIME}s | Reward: {MINING_REWARD / 10**18} VELVET")
            sys.stdout.flush()
            time.sleep(2)  # Give Flask time to start
            
            while self.is_mining:
                try:
                    print("[DEBUG] Mining loop iteration starting...")
                    sys.stdout.flush()
                    block = self.mine_block()
                    if block and p2p_network:
                        p2p_network.broadcast_block(block)
                    time.sleep(1)
                except Exception as e:
                    print(f"❌ Mining error: {e}")
                    import traceback
                    traceback.print_exc()
                    time.sleep(5)
        
        self.mining_thread = threading.Thread(target=mining_loop, daemon=True)
        self.mining_thread.start()
        print("[DEBUG] Mining thread created and started")
        sys.stdout.flush()
    
    def stop_mining(self):
        """Stop mining"""
        self.is_mining = False
        print("🛑 Mining stopped")
    
    def get_balance(self, address):
        return self.balances.get(address.lower(), 0)
    
    def get_nonce(self, address):
        return self.nonces.get(address.lower(), 0)
    
    def validate_chain(self):
        """Validate entire blockchain"""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i-1]
            
            if current.previous_hash != previous.hash:
                return False
            
            if current.hash != current.calculate_hash():
                return False
        
        return True
    
    def replace_chain(self, new_chain_data):
        """Replace chain if new chain is longer and valid"""
        try:
            new_blocks = [Block.from_dict(b) for b in new_chain_data]
            
            if len(new_blocks) <= len(self.chain):
                return False
            
            # Basic validation
            for i in range(1, len(new_blocks)):
                if new_blocks[i].previous_hash != new_blocks[i-1].hash:
                    print("❌ Invalid chain: broken links")
                    return False
            
            with self.chain_lock:
                print(f"🔄 Replacing chain with longer chain ({len(new_blocks)} blocks)")
                
                # Rebuild state from scratch
                self.chain = new_blocks
                self.balances = {GENESIS_ADDRESS.lower(): INITIAL_SUPPLY}
                self.nonces = {GENESIS_ADDRESS.lower(): 0}
                
                # Replay all transactions
                for block in self.chain[1:]:  # Skip genesis
                    for tx in block.transactions:
                        sender = tx.from_addr.lower() if tx.from_addr else None
                        recipient = tx.to.lower() if tx.to else None
                        
                        if sender == '0x0000000000000000000000000000000000000000':
                            # Coinbase
                            self.balances[recipient] = self.balances.get(recipient, 0) + tx.value
                        elif sender and recipient:
                            self.balances[sender] = self.balances.get(sender, 0) - tx.value
                            self.balances[recipient] = self.balances.get(recipient, 0) + tx.value
                            self.nonces[sender] = self.nonces.get(sender, 0) + 1
                
                print(f"✅ Chain synced successfully")
                self.synced = True  # Mark as synced
                return True
                
        except Exception as e:
            print(f"❌ Chain sync error: {e}")
            return False
    
    def add_block_from_peer(self, block_data):
        """Add a new block received from a peer"""
        try:
            new_block = Block.from_dict(block_data)
            
            with self.chain_lock:
                latest = self.chain[-1]
                
                # Check if block connects to our chain
                if new_block.previous_hash != latest.hash:
                    print(f"⚠️  Block #{new_block.number} doesn't connect to our chain")
                    return False
                
                # Verify hash meets difficulty
                target = '0' * new_block.difficulty
                if not new_block.hash.startswith('0x' + target):
                    print(f"❌ Block #{new_block.number} invalid PoW")
                    return False
                
                # Add block and update state
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
                print(f"✅ Received block #{new_block.number} from peer")
                return True
                
        except Exception as e:
            print(f"❌ Error adding peer block: {e}")
            return False
    
    def get_block_by_number(self, number):
        """Get block by number"""
        with self.chain_lock:
            if number < len(self.chain):
                return self.chain[number]
        return None
    
    def get_transaction_by_hash(self, tx_hash):
        """Get transaction by hash"""
        with self.chain_lock:
            for block in self.chain:
                for tx in block.transactions:
                    if tx.hash == tx_hash:
                        return tx, block
        return None, None

# ==================== P2P NETWORKING ====================

class P2PNetwork:
    """Peer-to-peer network manager"""
    def __init__(self, port, blockchain, manual_peer=None):
        self.port = port
        self.blockchain = blockchain
        self.peers = set()
        self.server_thread = None
        self.discovery_thread = None
        self.my_address = self._get_my_address()
        self.manual_peer = manual_peer
    
    def _get_my_address(self):
        """Get this node's public address"""
        try:
            response = requests.get('https://api.ipify.org?format=json', timeout=5)
            public_ip = response.json()['ip']
            return f"http://{public_ip}:{self.port}"
        except:
            return f"http://localhost:{self.port}"
    
    def start(self):
        """Start P2P services"""
        self.discovery_thread = threading.Thread(target=self._discover_peers, daemon=True)
        self.discovery_thread.start()
        
        sync_thread = threading.Thread(target=self._sync_chain, daemon=True)
        sync_thread.start()
        
        announce_thread = threading.Thread(target=self._announce_to_peers, daemon=True)
        announce_thread.start()
        
        print(f"🌐 P2P network started on port {self.port}")
        print(f"📍 Node address: {self.my_address}")
    
    def _discover_peers(self):
        """Discover and connect to peers"""
        while True:
            try:
                # Try manual peer first
                peers_to_try = []
                if self.manual_peer:
                    peers_to_try.append(self.manual_peer)
                peers_to_try.extend(BOOTSTRAP_NODES)
                
                for bootstrap in peers_to_try:
                    if bootstrap not in self.peers and bootstrap != self.my_address:
                        try:
                            response = requests.get(f"{bootstrap}/api/peers", timeout=5)
                            if response.status_code == 200:
                                self.peers.add(bootstrap)
                                print(f"✅ Connected to peer: {bootstrap}")
                                
                                peer_list = response.json()
                                for peer in peer_list[:MAX_PEERS]:
                                    if peer not in self.peers and peer != self.my_address and len(self.peers) < MAX_PEERS:
                                        self.peers.add(peer)
                                        print(f"✅ Discovered peer: {peer}")
                        except Exception as e:
                            pass
                
                time.sleep(PEER_DISCOVERY_INTERVAL)
            except Exception as e:
                print(f"❌ Peer discovery error: {e}")
                time.sleep(PEER_DISCOVERY_INTERVAL)
    
    def _sync_chain(self):
        """Sync blockchain with peers"""
        time.sleep(5)  # Initial delay
        
        # Non-bootstrap nodes need initial sync
        if not self.blockchain.is_bootstrap and not self.blockchain.synced:
            print("🔄 Performing initial blockchain sync...")
            for peer in BOOTSTRAP_NODES:
                try:
                    response = requests.get(f"{peer}/api/chain", timeout=10)
                    if response.status_code == 200:
                        peer_chain = response.json()
                        if len(peer_chain) > 0:
                            print(f"📥 Downloading blockchain from {peer}...")
                            if self.blockchain.replace_chain(peer_chain):
                                print(f"✅ Initial sync complete!")
                                break
                except Exception as e:
                    print(f"❌ Could not sync from {peer}: {e}")
            
            if not self.blockchain.synced and len(self.blockchain.chain) == 0:
                print("❌ ERROR: Could not sync blockchain from any peer!")
                print("   The bootstrap node may be offline.")
                return
        
        # Continue with regular sync
        while True:
            try:
                for peer in list(self.peers):
                    try:
                        response = requests.get(f"{peer}/api/chain", timeout=10)
                        if response.status_code == 200:
                            peer_chain = response.json()
                            if len(peer_chain) > len(self.blockchain.chain):
                                print(f"🔄 Found longer chain at {peer}")
                                self.blockchain.replace_chain(peer_chain)
                                break
                    except Exception as e:
                        self.peers.discard(peer)
                
                time.sleep(SYNC_INTERVAL)
            except Exception as e:
                print(f"❌ Sync error: {e}")
                time.sleep(SYNC_INTERVAL)
    
    def _announce_to_peers(self):
        """Announce our existence to peers"""
        while True:
            try:
                time.sleep(PEER_ANNOUNCE_INTERVAL)
                for peer in list(self.peers):
                    try:
                        requests.post(
                            f"{peer}/api/peer/announce",
                            json={'peer': self.my_address},
                            timeout=5
                        )
                    except:
                        pass
            except Exception as e:
                print(f"❌ Announce error: {e}")
    
    def broadcast_block(self, block):
        """Broadcast new block to all peers"""
        for peer in list(self.peers):
            try:
                requests.post(f"{peer}/api/block", json=block.to_dict(), timeout=5)
            except:
                pass
    
    def broadcast_transaction(self, tx):
        """Broadcast transaction to all peers"""
        for peer in list(self.peers):
            try:
                requests.post(f"{peer}/api/transaction", json=tx.to_dict(), timeout=5)
            except:
                pass
    
    def add_peer(self, peer_url):
        """Manually add a peer"""
        if peer_url not in self.peers and peer_url != self.my_address and len(self.peers) < MAX_PEERS:
            self.peers.add(peer_url)
            print(f"✅ Added peer: {peer_url}")
            return True
        return False

# ==================== JSON-RPC API ====================

app = Flask(__name__)
CORS(app)

blockchain = None
p2p_network = None

@app.route('/', methods=['POST'])
def json_rpc():
    """Main JSON-RPC endpoint (MetaMask compatible)"""
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
        elif method == 'eth_getBlockByHash':
            result = None
        elif method == 'eth_getTransactionByHash':
            tx_hash = params[0] if params else None
            tx, block = blockchain.get_transaction_by_hash(tx_hash)
            result = tx.to_dict() if tx else None
        elif method == 'eth_sendRawTransaction':
            raw_tx = params[0] if params else None
            result = '0x' + hashlib.sha256(raw_tx.encode()).hexdigest()
        elif method == 'eth_call':
            result = '0x'
        elif method == 'eth_estimateGas':
            result = '0x5208'
        elif method == 'web3_clientVersion':
            result = f'VelvetChain/v{VERSION}/python'
        elif method == 'net_listening':
            result = True
        elif method == 'net_peerCount':
            result = hex(len(p2p_network.peers))
        else:
            return jsonify({
                'jsonrpc': '2.0',
                'id': rpc_id,
                'error': {'code': -32601, 'message': f'Method {method} not found'}
            })
        
        return jsonify({'jsonrpc': '2.0', 'id': rpc_id, 'result': result})
    
    except Exception as e:
        return jsonify({
            'jsonrpc': '2.0',
            'id': rpc_id,
            'error': {'code': -32603, 'message': f'Internal error: {str(e)}'}
        })

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get blockchain statistics"""
    latest = blockchain.get_latest_block()
    return jsonify({
        'blockHeight': latest.number,
        'difficulty': blockchain.difficulty,
        'totalDifficulty': blockchain.total_difficulty,
        'pendingTransactions': len(blockchain.pending_transactions),
        'miningReward': MINING_REWARD / 10**18,
        'chainId': CHAIN_ID,
        'peers': len(p2p_network.peers),
        'peerList': list(p2p_network.peers),
        'version': VERSION,
        'isMining': blockchain.is_mining,
        'minerAddress': blockchain.miner_address,
        'nodeAddress': p2p_network.my_address
    })

@app.route('/api/chain', methods=['GET'])
def get_chain():
    """Get blockchain"""
    limit = request.args.get('limit', 100, type=int)
    with blockchain.chain_lock:
        return jsonify([block.to_dict() for block in blockchain.chain[-limit:]])

@app.route('/api/peers', methods=['GET'])
def get_peers():
    """Get connected peers"""
    return jsonify(list(p2p_network.peers))

@app.route('/api/block/<int:number>', methods=['GET'])
def get_block(number):
    """Get specific block by number"""
    block = blockchain.get_block_by_number(number)
    if block:
        return jsonify(block.to_dict())
    return jsonify({'error': 'Block not found'}), 404

@app.route('/api/address/<address>', methods=['GET'])
def get_address(address):
    """Get address information"""
    return jsonify({
        'address': address,
        'balance': blockchain.get_balance(address),
        'balanceVELVET': blockchain.get_balance(address) / 10**18,
        'nonce': blockchain.get_nonce(address)
    })

@app.route('/api/transaction/<tx_hash>', methods=['GET'])
def get_transaction(tx_hash):
    """Get transaction by hash"""
    tx, block = blockchain.get_transaction_by_hash(tx_hash)
    if tx:
        return jsonify({
            'transaction': tx.to_dict(),
            'blockNumber': block.number,
            'blockHash': block.hash
        })
    return jsonify({'error': 'Transaction not found'}), 404

@app.route('/api/block', methods=['POST'])
def receive_block():
    """Receive block from peer"""
    block_data = request.json
    success = blockchain.add_block_from_peer(block_data)
    return jsonify({'status': 'accepted' if success else 'rejected'})

@app.route('/api/transaction', methods=['POST'])
def receive_transaction():
    """Receive transaction from peer"""
    try:
        tx_data = request.json
        tx = Transaction.from_dict(tx_data)
        tx_hash = blockchain.add_transaction(tx)
        return jsonify({'status': 'accepted', 'hash': tx_hash})
    except Exception as e:
        return jsonify({'status': 'rejected', 'error': str(e)})

@app.route('/api/peer/add', methods=['POST'])
def add_peer():
    """Manually add a peer"""
    peer_url = request.json.get('peer')
    if peer_url:
        success = p2p_network.add_peer(peer_url)
        return jsonify({'success': success, 'peers': len(p2p_network.peers)})
    return jsonify({'error': 'Invalid peer URL'}), 400

@app.route('/api/peer/announce', methods=['POST'])
def announce_peer():
    """Receive peer announcement"""
    peer_url = request.json.get('peer')
    if peer_url and peer_url != p2p_network.my_address:
        p2p_network.add_peer(peer_url)
        return jsonify({'status': 'acknowledged', 'your_peer': p2p_network.my_address})
    return jsonify({'status': 'ignored'})

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'chain': 'velvet',
        'version': VERSION,
        'blockHeight': blockchain.get_latest_block().number,
        'peers': len(p2p_network.peers)
    })

# ==================== MAIN ====================

def print_banner():
    """Print startup banner"""
    banner = f"""
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║              🔗 VELVET CHAIN v{VERSION}                    ║
    ║         Decentralized EVM-Compatible Blockchain          ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """
    print(banner)

def main():
    """Main entry point"""
    global blockchain, p2p_network
    
    parser = argparse.ArgumentParser(description='Velvet Chain Node')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help='RPC port (default: 8545)')
    parser.add_argument('--mine', action='store_true', help='Enable mining')
    parser.add_argument('--wallet', type=str, help='Mining wallet address (required for mining)')
    parser.add_argument('--peer', type=str, help='Connect to specific peer (e.g., http://173.255.229.107:8545)')
    parser.add_argument('--bootstrap', action='store_true', help='Run as bootstrap node (OWNER ONLY)')
    
    args = parser.parse_args()
    
    print_banner()
    
    # Validate mining setup
    if args.mine and not args.wallet:
        print("❌ Error: --wallet required when mining is enabled")
        print("   Example: python node.py --mine --wallet 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb1")
        sys.exit(1)
    
    # Validate wallet address format
    if args.wallet and not (args.wallet.startswith('0x') and len(args.wallet) == 42):
        print("❌ Error: Invalid wallet address format")
        print("   Address must start with 0x and be 42 characters long")
        print("   Example: 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb1")
        sys.exit(1)
    
    # Initialize blockchain
    print("🔧 Initializing blockchain...")
    blockchain = VelvetChain(miner_address=args.wallet, is_bootstrap=args.bootstrap)
    
    # Initialize P2P network
    print("🔧 Initializing P2P network...")
    p2p_network = P2PNetwork(args.port, blockchain, manual_peer=args.peer)
    p2p_network.start()
    
    # Wait for sync if not bootstrap
    if not args.bootstrap:
        print("⏳ Waiting for blockchain sync...")
        time.sleep(8)  # Give time for initial sync
    
    # Start mining if enabled
    if args.mine:
        blockchain.start_mining()
    
    # Print node information
    print(f"\n{'='*60}")
    print(f"🚀 Node Running")
    print(f"{'='*60}")
    print(f"RPC Endpoint:     http://localhost:{args.port}")
    print(f"Chain ID:         {CHAIN_ID}")
    print(f"Network:          Velvet Chain")
    print(f"Node Type:        {'🏛️  BOOTSTRAP (Owner)' if args.bootstrap else '🌐 Regular Node'}")
    print(f"Mining:           {'✅ Active' if args.mine else '❌ Disabled'}")
    if args.wallet:
        print(f"Wallet:           {args.wallet}")
        balance = blockchain.get_balance(args.wallet)
        print(f"Balance:          {balance / 10**18:,.2f} VELVET")
    print(f"Block Height:     {blockchain.get_latest_block().number if blockchain.chain else 0}")
    print(f"Connected Peers:  {len(p2p_network.peers)}")
    if p2p_network.peers:
        print(f"Peers:")
        for peer in list(p2p_network.peers)[:5]:
            print(f"  • {peer}")
    print(f"{'='*60}\n")
    
    print("💡 Add to MetaMask:")
    print(f"   Network Name: Velvet Chain")
    print(f"   RPC URL:      http://localhost:{args.port}")
    print(f"   Chain ID:     {CHAIN_ID}")
    print(f"   Symbol:       VELVET")
    print()
    
    if args.bootstrap:
        print("🏛️  BOOTSTRAP NODE RUNNING")
        print("   This node created the genesis block")
        print("   Other nodes can connect with: --peer http://173.255.229.107:8545")
        print()
    
    # Start API server
    try:
        print("🌐 Starting API server...")
        app.run(host='0.0.0.0', port=args.port, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down Velvet Chain node...")
        if blockchain.is_mining:
            blockchain.stop_mining()
        print("👋 Goodbye!")
        sys.exit(0)

if __name__ == '__main__':
    main()
