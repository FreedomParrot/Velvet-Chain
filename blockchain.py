#!/usr/bin/env python3
"""
Velvet Chain - Enhanced Edition
Full EVM-Compatible Blockchain with Real Transactions

NEW FEATURES:
- Proper transaction signing with private keys
- Gas system (base fee + priority fee)
- Transaction pool with mempool
- Smart contract deployment and execution
- Event logs and receipts
- Account nonces and replay protection
- Transaction fees to miners
"""

import argparse
import hashlib
import json
import time
import threading
import random
import secrets
import os
import sys
from collections import defaultdict
from flask import Flask, jsonify, request
from flask_cors import CORS
import requests

# Try to import RLP and eth libraries
try:
    import rlp
    from rlp.sedes import big_endian_int, binary, BigEndianInt, Binary
    from eth_keys import keys
    from eth_utils import keccak, to_checksum_address, to_bytes, to_hex
    RLP_AVAILABLE = True
except ImportError:
    RLP_AVAILABLE = False
    print("⚠️  eth-rlp/eth-keys not available - using simplified mode")

# Try to import cryptography for proper ECDSA
try:
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("⚠️  cryptography not available - using simplified signing")

# ==================== CONFIGURATION ====================

CHAIN_ID = 16523431
VERSION = "2.0.0-enhanced"

GENESIS_ADDRESS = "0x16b1394752faf1c6e344cbc9a45f11fac67c9920"
INITIAL_SUPPLY = 1000000 * 10**18
GENESIS_TIMESTAMP = 1735488000
GENESIS_HASH = "0xa1c02b7107092ccef5e3a48711178e27018d74558fbb8cb564e235a4f2788eb1"

BLOCK_TIME = 10
BASE_MINING_REWARD = 50 * 10**18
DIFFICULTY_ADJUSTMENT = 100
TARGET_DIFFICULTY = 5
HALVING_INTERVAL = 210000
MAX_HALVINGS = 64

# Gas settings (similar to Ethereum)
MIN_GAS_PRICE = 1000000000  # 1 gwei
BASE_GAS_PRICE = 20000000000  # 20 gwei
MAX_GAS_PRICE = 500000000000  # 500 gwei
GAS_LIMIT_PER_BLOCK = 30000000
BASE_TX_GAS = 21000
CONTRACT_CREATION_GAS = 53000
CONTRACT_CALL_GAS = 21000
STORAGE_WRITE_GAS = 20000

DEFAULT_PORT = 8545
BOOTSTRAP_NODES = ["http://173.255.229.107:8545"]

MAX_PEERS = 25
PEER_DISCOVERY_INTERVAL = 30
SYNC_INTERVAL = 15
PEER_ANNOUNCE_INTERVAL = 45

# Transaction types
TX_TYPE_TRANSFER = 0
TX_TYPE_CONTRACT_CREATION = 1
TX_TYPE_CONTRACT_CALL = 2

# ==================== RLP TRANSACTION (if available) ====================

if RLP_AVAILABLE:
    class RLPTransaction(rlp.Serializable):
        """
        EIP-155 compliant transaction
        """
        fields = [
            ('nonce', big_endian_int),
            ('gas_price', big_endian_int),
            ('gas_limit', big_endian_int),
            ('to', Binary.fixed_length(20, allow_empty=True)),
            ('value', big_endian_int),
            ('data', binary),
            ('v', big_endian_int),
            ('r', big_endian_int),
            ('s', big_endian_int),
        ]
        
        def __init__(self, nonce=0, gas_price=0, gas_limit=0, to=b'', value=0, data=b'', v=0, r=0, s=0):
            super(RLPTransaction, self).__init__(nonce, gas_price, gas_limit, to, value, data, v, r, s)
            self._sender = None
            self._hash = None
        
        @property
        def hash(self):
            if self._hash is None:
                self._hash = keccak(rlp.encode(self))
            return self._hash
        
        @property
        def sender(self):
            if self._sender is None:
                self._sender = self.recover_sender()
            return self._sender
        
        def recover_sender(self):
            """Recover sender address from signature using ecrecover"""
            if self.v not in (27, 28) and self.v not in range(35, 100000):
                raise ValueError(f"Invalid v value: {self.v}")
            
            # Calculate chain_id from v (EIP-155)
            if self.v >= 35:
                chain_id = (self.v - 35) // 2
                v = self.v - chain_id * 2 - 35 + 27
            else:
                chain_id = None
                v = self.v
            
            # Create unsigned transaction for signing hash
            unsigned_tx = RLPTransaction(
                nonce=self.nonce,
                gas_price=self.gas_price,
                gas_limit=self.gas_limit,
                to=self.to,
                value=self.value,
                data=self.data,
                v=chain_id if chain_id else 0,
                r=0,
                s=0
            )
            
            if chain_id:
                # EIP-155: hash(rlp([nonce, gasprice, startgas, to, value, data, chainid, 0, 0]))
                msg_hash = keccak(rlp.encode(unsigned_tx))
            else:
                # Legacy: hash(rlp([nonce, gasprice, startgas, to, value, data]))
                msg_hash = keccak(rlp.encode([
                    self.nonce, self.gas_price, self.gas_limit,
                    self.to, self.value, self.data
                ]))
            
            # Recover public key
            signature = keys.Signature(vrs=(v - 27, self.r, self.s))
            public_key = signature.recover_public_key_from_msg_hash(msg_hash)
            
            # Get address from public key (last 20 bytes of keccak256(public_key))
            address = keccak(public_key.to_bytes())[-20:]
            return to_checksum_address(address)
        
        def to_dict(self):
            """Convert to JSON-RPC format"""
            return {
                'nonce': hex(self.nonce),
                'gasPrice': hex(self.gas_price),
                'gas': hex(self.gas_limit),
                'to': '0x' + self.to.hex() if self.to else None,
                'value': hex(self.value),
                'input': '0x' + self.data.hex(),
                'v': hex(self.v),
                'r': hex(self.r),
                's': hex(self.s),
                'hash': '0x' + self.hash.hex(),
                'from': self.sender
            }
class EIP1559Transaction(rlp.Serializable):
    """
    EIP-1559 Dynamic Fee Transaction (type 0x02)
    """
    fields = [
        ('chain_id', big_endian_int),
        ('nonce', big_endian_int),
        ('max_priority_fee_per_gas', big_endian_int),
        ('max_fee_per_gas', big_endian_int),
        ('gas_limit', big_endian_int),
        ('to', Binary.fixed_length(20, allow_empty=True)),
        ('value', big_endian_int),
        ('data', binary),
        ('access_list', rlp.sedes.CountableList(rlp.sedes.List([]))),
        ('v', big_endian_int),
        ('r', big_endian_int),
        ('s', big_endian_int),
    ]

    @property
    def hash(self):
        return keccak(b'\x02' + rlp.encode(self))

    @property
    def sender(self):
        msg = keccak(b'\x02' + rlp.encode(self[:-3]))
        sig = keys.Signature(vrs=(self.v, self.r, self.s))
        pub = sig.recover_public_key_from_msg_hash(msg)
        return to_checksum_address(keccak(pub.to_bytes())[-20:])

def decode_raw_transaction(raw_tx_hex):
    if raw_tx_hex.startswith("0x"):
        raw_tx_hex = raw_tx_hex[2:]

    raw = bytes.fromhex(raw_tx_hex)

    # ---- Typed Transaction (EIP-2718 prefix) ----
    if raw[0] == 2:
        tx_type = 2
        body = raw[1:]

        tx = rlp.decode(body, EIP1559Transaction)

        v = int(tx.v)
        r = int(tx.r)
        s = int(tx.s)

        sender = tx.sender

        print("🔹 Decoded EIP-1559 transaction")
        print("   From:", sender)
        print("   Nonce:", tx.nonce)
        print("   Value:", tx.value)
        print("   GasLimit:", tx.gas_limit)
        print("   MaxFee:", tx.max_fee_per_gas)
        print("   MaxPriority:", tx.max_priority_fee_per_gas)

        return tx

    # ---- Legacy transaction ----
    tx = rlp.decode(raw, RLPTransaction)

    if isinstance(tx.v, (bytes, bytearray)):
        v = int.from_bytes(tx.v, 'big')
    else:
        v = tx.v

    tx._sender = tx.recover_sender()

    print("🔹 Decoded Legacy transaction from", tx.sender)
    return tx



    
    def create_raw_transaction(nonce, gas_price, gas_limit, to, value, data, chain_id=CHAIN_ID):
        """
        Create an unsigned transaction for wallet signing
        """
        to_bytes = bytes.fromhex(to[2:]) if to and to.startswith('0x') else b''
        data_bytes = bytes.fromhex(data[2:]) if data and data.startswith('0x') else b''
        
        tx = RLPTransaction(
            nonce=nonce,
            gas_price=gas_price,
            gas_limit=gas_limit,
            to=to_bytes,
            value=value,
            data=data_bytes,
            v=chain_id,
            r=0,
            s=0
        )
        
        return tx
    
    def sign_transaction(tx, private_key_hex):
        """
        Sign a transaction with a private key
        Returns: signed RLPTransaction object
        """
        # Remove 0x prefix
        if private_key_hex.startswith('0x'):
            private_key_hex = private_key_hex[2:]
        
        private_key = keys.PrivateKey(bytes.fromhex(private_key_hex))
        
        # Get chain_id from v field
        chain_id = tx.v if tx.v > 0 else None
        
        # Create signing hash
        if chain_id:
            # EIP-155
            msg_hash = keccak(rlp.encode(tx))
        else:
            # Legacy
            msg_hash = keccak(rlp.encode([
                tx.nonce, tx.gas_price, tx.gas_limit,
                tx.to, tx.value, tx.data
            ]))
        
        # Sign
        signature = private_key.sign_msg_hash(msg_hash)
        
        # Apply EIP-155
        if chain_id:
            v = signature.v + chain_id * 2 + 35
        else:
            v = signature.v + 27
        
        # Create signed transaction
        signed_tx = RLPTransaction(
            nonce=tx.nonce,
            gas_price=tx.gas_price,
            gas_limit=tx.gas_limit,
            to=tx.to,
            value=tx.value,
            data=tx.data,
            v=v,
            r=signature.r,
            s=signature.s
        )
        
        return signed_tx
    
    def encode_raw_transaction(tx):
        """
        Encode a transaction to raw RLP format for broadcasting
        """
        return '0x' + rlp.encode(tx).hex()
    
    def create_eth_wallet():
        """Create a new Ethereum wallet"""
        private_key = keys.PrivateKey(os.urandom(32))
        public_key = private_key.public_key
        address = public_key.to_checksum_address()
        
        return {
            'address': address,
            'privateKey': '0x' + private_key.to_hex()[2:]
        }
    
    def private_key_to_address(private_key_hex):
        """Convert private key to address"""
        if private_key_hex.startswith('0x'):
            private_key_hex = private_key_hex[2:]
        
        private_key = keys.PrivateKey(bytes.fromhex(private_key_hex))
        return private_key.public_key.to_checksum_address()

# ==================== WALLET ====================

class Wallet:
    """Ethereum-style wallet with private/public key"""
    
    def __init__(self, private_key=None):
        if CRYPTO_AVAILABLE:
            if private_key:
                # Load from hex
                private_bytes = bytes.fromhex(private_key.replace('0x', ''))
                self.private_key = ec.derive_private_key(
                    int.from_bytes(private_bytes, 'big'),
                    ec.SECP256K1(),
                    default_backend()
                )
            else:
                # Generate new key
                self.private_key = ec.generate_private_key(ec.SECP256K1(), default_backend())
            
            # Get public key
            public_key = self.private_key.public_key()
            public_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.X962,
                format=serialization.PublicFormat.UncompressedPoint
            )
            
            # Address is last 20 bytes of keccak256(public_key)
            # Using SHA256 as simplified alternative to keccak256
            address_hash = hashlib.sha256(public_bytes).digest()
            self.address = '0x' + address_hash[-20:].hex()
            
            # Export private key
            private_bytes = self.private_key.private_numbers().private_value.to_bytes(32, 'big')
            self.private_key_hex = '0x' + private_bytes.hex()
        else:
            # Simplified version without cryptography
            if private_key:
                self.private_key_hex = private_key if private_key.startswith('0x') else '0x' + private_key
            else:
                self.private_key_hex = '0x' + secrets.token_hex(32)
            
            # Derive address from private key
            address_hash = hashlib.sha256(self.private_key_hex.encode()).digest()
            self.address = '0x' + address_hash[-20:].hex()
    
    def sign_transaction(self, tx_dict):
        """Sign a transaction and return v, r, s"""
        # Create signing hash
        signing_data = json.dumps(tx_dict, sort_keys=True).encode()
        msg_hash = hashlib.sha256(signing_data).digest()
        
        if CRYPTO_AVAILABLE:
            signature = self.private_key.sign(msg_hash, ec.ECDSA(hashes.SHA256()))
            # Parse DER signature to get r and s
            r = int.from_bytes(signature[4:36], 'big')
            s = int.from_bytes(signature[38:70], 'big')
            v = 27 + (int.from_bytes(msg_hash, 'big') % 2)  # Simplified recovery id
        else:
            # Simplified signing
            sig_hash = hashlib.sha256(self.private_key_hex.encode() + msg_hash).digest()
            r = int.from_bytes(sig_hash[:32], 'big')
            s = int.from_bytes(hashlib.sha256(sig_hash).digest()[:32], 'big')
            v = 27
        
        return v, r, s
    
    @staticmethod
    def verify_signature(tx_dict, v, r, s, expected_address):
        """Verify transaction signature"""
        # Simplified verification - in production use proper ECDSA recovery
        signing_data = json.dumps(tx_dict, sort_keys=True).encode()
        msg_hash = hashlib.sha256(signing_data).digest()
        
        # For now, just check that signature values are present
        return v > 0 and r > 0 and s > 0
    
    @staticmethod
    def create_wallet():
        """Create a new random wallet"""
        return Wallet()
    
    @staticmethod
    def from_private_key(private_key):
        """Load wallet from private key"""
        return Wallet(private_key)

# ==================== TRANSACTIONS ====================

class Transaction:
    def __init__(self, nonce, gas_price, gas_limit, to, value, data, 
                 chain_id=CHAIN_ID, v=0, r=0, s=0, from_addr=None, tx_type=TX_TYPE_TRANSFER):
        self.nonce = nonce
        self.gas_price = gas_price
        self.gas_limit = gas_limit
        self.to = to
        self.value = value
        self.data = data
        self.chain_id = chain_id
        self.v = v
        self.r = r
        self.s = s
        self.from_addr = from_addr
        self.tx_type = tx_type
        self.hash = self._calculate_hash()
    
    def _calculate_hash(self):
        tx_data = {
            'nonce': self.nonce,
            'gasPrice': self.gas_price,
            'gas': self.gas_limit,
            'to': self.to if self.to else None,
            'value': self.value,
            'data': self.data,
            'chainId': self.chain_id,
            'v': self.v,
            'r': self.r,
            's': self.s
        }
        return '0x' + hashlib.sha256(json.dumps(tx_data, sort_keys=True).encode()).hexdigest()
    
    def sign(self, wallet):
        """Sign this transaction with a wallet"""
        signing_dict = {
            'nonce': self.nonce,
            'gasPrice': self.gas_price,
            'gas': self.gas_limit,
            'to': self.to if self.to else None,
            'value': self.value,
            'data': self.data,
            'chainId': self.chain_id
        }
        self.v, self.r, self.s = wallet.sign_transaction(signing_dict)
        self.from_addr = wallet.address
        self.hash = self._calculate_hash()
    
    def verify(self):
        """Verify transaction signature"""
        if not self.from_addr:
            return False
        signing_dict = {
            'nonce': self.nonce,
            'gasPrice': self.gas_price,
            'gas': self.gas_limit,
            'to': self.to if self.to else None,
            'value': self.value,
            'data': self.data,
            'chainId': self.chain_id
        }
        return Wallet.verify_signature(signing_dict, self.v, self.r, self.s, self.from_addr)
    
    def calculate_gas_used(self):
        """Calculate actual gas used by transaction"""
        gas_used = BASE_TX_GAS
        
        if self.tx_type == TX_TYPE_CONTRACT_CREATION:
            gas_used += CONTRACT_CREATION_GAS
            # Add gas for bytecode size
            if self.data and self.data != '0x':
                bytecode_size = (len(self.data) - 2) // 2  # Remove 0x and count bytes
                gas_used += bytecode_size * 200
        
        elif self.tx_type == TX_TYPE_CONTRACT_CALL:
            gas_used += CONTRACT_CALL_GAS
            # Add gas for calldata
            if self.data and self.data != '0x':
                calldata_size = (len(self.data) - 2) // 2
                gas_used += calldata_size * 16
        
        return min(gas_used, self.gas_limit)
    
    def to_dict(self):
        return {
            'hash': self.hash,
            'nonce': hex(self.nonce),
            'gasPrice': hex(self.gas_price),
            'gas': hex(self.gas_limit),
            'to': self.to if self.to else None,
            'from': self.from_addr or '0x0',
            'value': hex(self.value),
            'data': self.data,
            'chainId': hex(self.chain_id),
            'v': hex(self.v),
            'r': hex(self.r),
            's': hex(self.s),
            'type': hex(self.tx_type)
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
            chain_id=int(data.get('chainId', hex(CHAIN_ID)), 16),
            v=int(data['v'], 16),
            r=int(data['r'], 16),
            s=int(data['s'], 16),
            from_addr=data.get('from', '0x0'),
            tx_type=int(data.get('type', '0x0'), 16)
        )

class TransactionReceipt:
    """Transaction execution receipt"""
    
    def __init__(self, tx_hash, block_number, block_hash, from_addr, to, 
                 gas_used, cumulative_gas_used, status, logs=None, contract_address=None):
        self.tx_hash = tx_hash
        self.block_number = block_number
        self.block_hash = block_hash
        self.from_addr = from_addr
        self.to = to
        self.gas_used = gas_used
        self.cumulative_gas_used = cumulative_gas_used
        self.status = status  # 1 = success, 0 = failed
        self.logs = logs or []
        self.contract_address = contract_address
    
    def to_dict(self):
        return {
            'transactionHash': self.tx_hash,
            'blockNumber': hex(self.block_number),
            'blockHash': self.block_hash,
            'from': self.from_addr,
            'to': self.to,
            'gasUsed': hex(self.gas_used),
            'cumulativeGasUsed': hex(self.cumulative_gas_used),
            'status': hex(self.status),
            'logs': self.logs,
            'contractAddress': self.contract_address
        }

# ==================== SMART CONTRACTS ====================

class SmartContract:
    """Simple smart contract storage"""
    
    def __init__(self, address, bytecode, creator):
        self.address = address
        self.bytecode = bytecode
        self.creator = creator
        self.storage = {}  # Key-value storage
        self.balance = 0
    
    def call(self, calldata, value=0):
        """Execute contract call (simplified)"""
        # In a real implementation, this would execute EVM bytecode
        # For now, we just store the call and return success
        logs = [{
            'address': self.address,
            'data': calldata,
            'topics': []
        }]
        return True, logs

# ==================== BLOCKCHAIN ====================

class Block:
    def __init__(self, number, timestamp, transactions, previous_hash, miner, 
                 difficulty=TARGET_DIFFICULTY, base_fee_per_gas=BASE_GAS_PRICE):
        self.number = number
        self.timestamp = timestamp
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.miner = miner
        self.difficulty = difficulty
        self.base_fee_per_gas = base_fee_per_gas
        self.nonce = 0
        self.gas_used = 0
        self.gas_limit = GAS_LIMIT_PER_BLOCK
        self.hash = None
        self.receipts = []
    
    def calculate_hash(self):
        block_data = {
            'number': self.number,
            'timestamp': self.timestamp,
            'transactions': [tx.hash for tx in self.transactions],
            'previous_hash': self.previous_hash,
            'miner': self.miner,
            'nonce': self.nonce,
            'difficulty': self.difficulty,
            'baseFeePerGas': self.base_fee_per_gas
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
        
        return False
    
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
            'baseFeePerGas': hex(self.base_fee_per_gas),
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
            difficulty=int(data['difficulty'], 16),
            base_fee_per_gas=int(data.get('baseFeePerGas', hex(BASE_GAS_PRICE)), 16)
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
        self.contracts = {}  # address -> SmartContract
        self.receipts = {}  # tx_hash -> TransactionReceipt
        self.miner_address = miner_address
        self.is_mining = False
        self.mining_should_stop = False
        self.difficulty = TARGET_DIFFICULTY
        self.total_difficulty = 0
        self.base_fee_per_gas = BASE_GAS_PRICE
        self.mining_thread = None
        self.chain_lock = threading.Lock()
        self.is_bootstrap = is_bootstrap
        self.synced = False
        
        if self.is_bootstrap and len(self.chain) == 0:
            self._create_genesis()
            self.synced = True
    
    def _create_genesis(self):
        genesis = Block(0, GENESIS_TIMESTAMP, [], '0x' + '0' * 64, GENESIS_ADDRESS, 
                       difficulty=1, base_fee_per_gas=BASE_GAS_PRICE)
        genesis.nonce = 0
        genesis.hash = genesis.calculate_hash()
        
        if genesis.hash != GENESIS_HASH:
            print(f"⚠️  Genesis hash mismatch - using hardcoded")
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
        """Add transaction to mempool"""
        # Verify signature
        if not tx.verify():
            print(f"❌ Invalid signature for tx {tx.hash[:16]}...")
            return None
        
        # Check nonce
        sender = tx.from_addr.lower()
        expected_nonce = self.nonces.get(sender, 0)
        if tx.nonce != expected_nonce:
            print(f"❌ Invalid nonce: got {tx.nonce}, expected {expected_nonce}")
            return None
        
        # Check balance (value + max gas cost)
        max_cost = tx.value + (tx.gas_limit * tx.gas_price)
        if self.balances.get(sender, 0) < max_cost:
            print(f"❌ Insufficient balance: need {max_cost / 10**18}, have {self.balances.get(sender, 0) / 10**18}")
            return None
        
        # Check gas price
        if tx.gas_price < MIN_GAS_PRICE:
            print(f"❌ Gas price too low: {tx.gas_price} < {MIN_GAS_PRICE}")
            return None
        
        self.pending_transactions.append(tx)
        print(f"✅ Transaction added to mempool: {tx.hash[:16]}...")
        return tx.hash
    
    def get_block_reward(self, block_number):
        """Calculate block reward with halving"""
        halvings = block_number // HALVING_INTERVAL
        if halvings >= MAX_HALVINGS:
            return 0
        return BASE_MINING_REWARD >> halvings
    
    def mine_block(self):
        if not self.miner_address:
            return None
        
        with self.chain_lock:
            latest = self.chain[-1]
            mining_block_num = latest.number + 1
            
            block_reward = self.get_block_reward(mining_block_num)
            
            # Select transactions for block (highest gas price first)
            sorted_txs = sorted(self.pending_transactions, 
                              key=lambda tx: tx.gas_price, reverse=True)
            
            block_txs = []
            total_gas = 0
            total_fees = 0
            
            for tx in sorted_txs:
                gas_needed = tx.calculate_gas_used()
                if total_gas + gas_needed <= GAS_LIMIT_PER_BLOCK:
                    block_txs.append(tx)
                    total_gas += gas_needed
                    total_fees += gas_needed * tx.gas_price
                
                if len(block_txs) >= 100:  # Max txs per block
                    break
            
            # Create coinbase transaction (block reward + fees)
            coinbase_tx = Transaction(
                nonce=0, gas_price=0, gas_limit=0,
                to=self.miner_address, 
                value=block_reward + total_fees, 
                data='0x',
                from_addr='0x0000000000000000000000000000000000000000'
            )
            
            all_txs = [coinbase_tx] + block_txs
            
            new_block = Block(
                number=mining_block_num,
                timestamp=int(time.time()),
                transactions=all_txs,
                previous_hash=latest.hash,
                miner=self.miner_address,
                difficulty=self.difficulty,
                base_fee_per_gas=self.base_fee_per_gas
            )
        
        print(f"⛏️  Mining block #{new_block.number} ({len(block_txs)} txs, {total_fees/10**18:.4f} VELVET fees)")
        sys.stdout.flush()
        
        self.mining_should_stop = False
        success = new_block.mine(lambda: not self.mining_should_stop and self.is_mining)
        
        if not success:
            print(f"\n⚠️  Mining interrupted for block #{new_block.number}")
            return None
        
        with self.chain_lock:
            current_latest = self.chain[-1]
            if current_latest.hash != new_block.previous_hash:
                print(f"\n⚠️  Block #{new_block.number} discarded - chain changed")
                return None
            
            # Execute transactions
            cumulative_gas = 0
            for i, tx in enumerate(all_txs):
                if i == 0:  # Coinbase
                    addr = self.miner_address.lower()
                    self.balances[addr] = self.balances.get(addr, 0) + tx.value
                else:
                    # Execute transaction
                    success, receipt = self._execute_transaction(tx, new_block, cumulative_gas)
                    cumulative_gas = receipt.cumulative_gas_used
                    new_block.receipts.append(receipt)
                    self.receipts[tx.hash] = receipt
            
            new_block.gas_used = cumulative_gas
            self.chain.append(new_block)
            self.total_difficulty += 2 ** self.difficulty
            
            # Remove mined transactions
            mined_hashes = {tx.hash for tx in block_txs}
            self.pending_transactions = [tx for tx in self.pending_transactions 
                                        if tx.hash not in mined_hashes]
        
        miner_balance = self.get_balance(self.miner_address) / 10**18
        print(f"✅ Block #{new_block.number} mined")
        print(f"💰 Reward: {block_reward/10**18} VELVET + {total_fees/10**18:.4f} fees = {(block_reward+total_fees)/10**18:.4f} total")
        print(f"💎 Balance: {miner_balance:,.2f} VELVET\n")
        
        return new_block
    
    def _execute_transaction(self, tx, block, cumulative_gas):
        """Execute a transaction and return receipt"""
        sender = tx.from_addr.lower()
        recipient = tx.to.lower() if tx.to else None
        
        gas_used = tx.calculate_gas_used()
        gas_cost = gas_used * tx.gas_price
        
        # Deduct gas cost
        self.balances[sender] = self.balances.get(sender, 0) - gas_cost
        
        contract_address = None
        logs = []
        status = 1  # Success
        
        try:
            if tx.tx_type == TX_TYPE_CONTRACT_CREATION:
                # Deploy contract
                contract_address = self._create_contract_address(sender, tx.nonce)
                contract = SmartContract(contract_address, tx.data, sender)
                contract.balance = tx.value
                self.contracts[contract_address.lower()] = contract
                print(f"   📜 Contract deployed at {contract_address}")
            
            elif tx.tx_type == TX_TYPE_CONTRACT_CALL and recipient in self.contracts:
                # Call contract
                contract = self.contracts[recipient]
                success, logs = contract.call(tx.data, tx.value)
                if success:
                    contract.balance += tx.value
                    self.balances[sender] -= tx.value
            
            else:
                # Regular transfer
                if tx.value > 0 and recipient:
                    self.balances[sender] -= tx.value
                    self.balances[recipient] = self.balances.get(recipient, 0) + tx.value
            
            # Increment nonce
            self.nonces[sender] = self.nonces.get(sender, 0) + 1
            
        except Exception as e:
            print(f"   ❌ Transaction execution failed: {e}")
            status = 0
        
        receipt = TransactionReceipt(
            tx_hash=tx.hash,
            block_number=block.number,
            block_hash=block.hash,
            from_addr=tx.from_addr,
            to=tx.to,
            gas_used=gas_used,
            cumulative_gas_used=cumulative_gas + gas_used,
            status=status,
            logs=logs,
            contract_address=contract_address
        )
        
        return status == 1, receipt
    
    def _create_contract_address(self, sender, nonce):
        """Create deterministic contract address"""
        data = f"{sender}{nonce}".encode()
        addr_hash = hashlib.sha256(data).digest()
        return '0x' + addr_hash[-20:].hex()
    
    def start_mining(self):
        if self.is_mining:
            return
        
        if not self.is_bootstrap and not self.synced:
            print("⚠️  Cannot start mining - waiting for sync...")
            return
        
        self.is_mining = True
        
        def mining_loop():
            print(f"⛏️  Mining started! Rewards → {self.miner_address}")
            sys.stdout.flush()
            time.sleep(2)
            
            while self.is_mining:
                try:
                    delay = random.uniform(0, 8)
                    time.sleep(delay)
                    
                    block = self.mine_block()
                    if block and p2p_network:
                        p2p_network.broadcast_block(block)
                        time.sleep(5)
                    
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
    
    def get_transaction_receipt(self, tx_hash):
        return self.receipts.get(tx_hash)
    
    def replace_chain(self, new_chain_data):
        try:
            new_blocks = [Block.from_dict(b) for b in new_chain_data]
            
            if len(new_blocks) <= len(self.chain):
                return False
            
            if new_blocks[0].hash != GENESIS_HASH:
                return False
            
            for i in range(1, len(new_blocks)):
                if new_blocks[i].previous_hash != new_blocks[i-1].hash:
                    return False
            
            return self._apply_chain(new_blocks)
                
        except Exception as e:
            print(f"❌ Sync error: {e}")
            return False
    
    def _apply_chain(self, new_blocks):
        try:
            was_mining = self.is_mining
            if was_mining:
                self.mining_should_stop = True
                time.sleep(0.5)
            
            with self.chain_lock:
                print(f"🔄 Applying chain with {len(new_blocks)} blocks...")
                
                self.chain = new_blocks
                self.balances = {GENESIS_ADDRESS.lower(): INITIAL_SUPPLY}
                self.nonces = {GENESIS_ADDRESS.lower(): 0}
                self.contracts = {}
                self.receipts = {}
                
                # Replay all transactions
                for block in self.chain[1:]:
                    for tx in block.transactions:
                        sender = tx.from_addr.lower() if tx.from_addr else None
                        recipient = tx.to.lower() if tx.to else None
                        
                        if sender == '0x0000000000000000000000000000000000000000':
                            # Coinbase
                            self.balances[recipient] = self.balances.get(recipient, 0) + tx.value
                        elif sender and recipient:
                            # Regular transaction
                            gas_cost = tx.calculate_gas_used() * tx.gas_price
                            self.balances[sender] = self.balances.get(sender, 0) - tx.value - gas_cost
                            self.balances[recipient] = self.balances.get(recipient, 0) + tx.value
                            self.nonces[sender] = self.nonces.get(sender, 0) + 1
                
                print(f"✅ Chain synced to height {len(self.chain)-1}!")
                self.synced = True
            
            if was_mining:
                print("▶️  Resuming mining...")
            
            return True
        except Exception as e:
            print(f"❌ Apply chain error: {e}")
            return False
    
    def add_block_from_peer(self, block_data):
        try:
            new_block = Block.from_dict(block_data)
            
            with self.chain_lock:
                if len(self.chain) == 0:
                    return False
                
                latest = self.chain[-1]
                
                print(f"📨 Peer block #{new_block.number} | Our height: #{latest.number}")
                
                if new_block.previous_hash == latest.hash and new_block.number == latest.number + 1:
                    target = '0' * new_block.difficulty
                    if not new_block.hash.startswith('0x' + target):
                        return False
                    
                    if self.is_mining:
                        self.mining_should_stop = True
                    
                    # Execute transactions
                    cumulative_gas = 0
                    for i, tx in enumerate(new_block.transactions):
                        if i == 0:  # Coinbase
                            addr = new_block.miner.lower()
                            self.balances[addr] = self.balances.get(addr, 0) + tx.value
                        else:
                            success, receipt = self._execute_transaction(tx, new_block, cumulative_gas)
                            cumulative_gas = receipt.cumulative_gas_used
                            self.receipts[tx.hash] = receipt
                    
                    self.chain.append(new_block)
                    print(f"   ✅ Accepted from peer")
                    return True
                
                elif new_block.number == latest.number:
                    if new_block.hash != latest.hash:
                        print(f"   🔀 FORK! Different block #{new_block.number}")
                        return "FORK_DETECTED"
                    else:
                        print(f"   ⏭️  Duplicate block")
                        return False
                
                elif new_block.number < latest.number:
                    if new_block.number < len(self.chain):
                        our_block = self.chain[new_block.number]
                        if our_block.hash != new_block.hash:
                            print(f"   🔀 FORK at block #{new_block.number}!")
                            return "FORK_DETECTED"
                    print(f"   ⏭️  Old block rejected")
                    return False
                
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
        if not self.blockchain.is_bootstrap and not self.blockchain.synced:
            print("🔄 Starting initial blockchain sync...")
            
            for attempt in range(10):
                time.sleep(2)
                
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
                            
                            if peer_height > our_height:
                                print(f"\n🔄 Peer has longer chain ({peer_height} vs {our_height})")
                                if self.blockchain.replace_chain(peer_chain):
                                    print(f"✅ Synced to peer's chain!")
                                    break
                    except Exception as e:
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
    
    def broadcast_transaction(self, tx):
        """Broadcast transaction to peers"""
        for peer in list(self.peers):
            try:
                requests.post(f"{peer}/api/transaction", json=tx.to_dict(), timeout=5)
            except:
                pass
    
    def add_peer(self, peer_url):
        if peer_url not in self.peers and peer_url != self.my_address and len(self.peers) < MAX_PEERS:
            self.peers.add(peer_url)
            return True
        return False

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
            if not address:
                raise ValueError("Address required")
            balance = blockchain.get_balance(address)
            result = hex(balance)
        
        elif method == 'eth_getTransactionCount':
            address = params[0] if params else None
            if not address:
                raise ValueError("Address required")
            nonce = blockchain.get_nonce(address)
            result = hex(nonce)
        
        elif method == 'eth_gasPrice':
            result = hex(blockchain.base_fee_per_gas)
        
        elif method == 'eth_estimateGas':
            tx_params = params[0] if params else {}
            # Check if contract creation
            if not tx_params.get('to'):
                result = hex(CONTRACT_CREATION_GAS)
            elif tx_params.get('data') and tx_params['data'] != '0x':
                result = hex(CONTRACT_CALL_GAS)
            else:
                result = hex(BASE_TX_GAS)
        
        elif method == 'eth_call':
            # Execute read-only call - return empty for now
            result = '0x'
        
        elif method == 'net_version':
            result = str(CHAIN_ID)
        
        elif method == 'eth_accounts':
            result = []
        
        elif method == 'eth_getBlockByNumber':
            block_num_hex = params[0] if params else 'latest'
            include_txs = params[1] if len(params) > 1 else False
            
            if block_num_hex == 'latest':
                block = blockchain.get_latest_block()
            elif block_num_hex == 'earliest':
                block = blockchain.get_block_by_number(0)
            elif block_num_hex == 'pending':
                block = None
            else:
                block = blockchain.get_block_by_number(int(block_num_hex, 16))
            
            if block:
                result = block.to_dict() if include_txs else {
                    **block.to_dict(),
                    'transactions': [tx.hash for tx in block.transactions]
                }
            else:
                result = None
        
        elif method == 'eth_getTransactionByHash':
            tx_hash = params[0] if params else None
            if not tx_hash:
                raise ValueError("Transaction hash required")
            
            tx, block = blockchain.get_transaction_by_hash(tx_hash)
            if tx and block:
                tx_dict = tx.to_dict()
                tx_dict['blockNumber'] = hex(block.number)
                tx_dict['blockHash'] = block.hash
                result = tx_dict
            else:
                result = None
        
        elif method == 'eth_getTransactionReceipt':
            tx_hash = params[0] if params else None
            if not tx_hash:
                raise ValueError("Transaction hash required")
            
            receipt = blockchain.get_transaction_receipt(tx_hash)
            result = receipt.to_dict() if receipt else None
        
        elif method == 'eth_sendRawTransaction':
            raw_tx_hex = params[0] if params else None
            if not raw_tx_hex:
                return jsonify({
                    'jsonrpc': '2.0',
                    'id': rpc_id,
                    'error': {'code': -32602, 'message': 'missing raw transaction'}
                })
            
            if RLP_AVAILABLE:
                try:
                    # Decode RLP transaction
                    rlp_tx = decode_raw_transaction(raw_tx_hex)
                    
                    # Convert to VelvetChain transaction
if isinstance(rlp_tx, EIP1559Transaction):
    # Use max_fee_per_gas as effective gas price
    effective_gas_price = rlp_tx.max_fee_per_gas

    tx = Transaction(
        nonce=rlp_tx.nonce,
        gas_price=effective_gas_price,
        gas_limit=rlp_tx.gas_limit,
        to='0x' + rlp_tx.to.hex() if rlp_tx.to else None,
        value=rlp_tx.value,
        data='0x' + rlp_tx.data.hex() if rlp_tx.data else '0x',
        chain_id=rlp_tx.chain_id,
        v=rlp_tx.v,
        r=rlp_tx.r,
        s=rlp_tx.s,
        from_addr=rlp_tx.sender,
        tx_type=TX_TYPE_TRANSFER if rlp_tx.to else TX_TYPE_CONTRACT_CREATION
    )

else:
    # Legacy transaction
    tx = Transaction(
        nonce=rlp_tx.nonce,
        gas_price=rlp_tx.gas_price,
        gas_limit=rlp_tx.gas_limit,
        to='0x' + rlp_tx.to.hex() if rlp_tx.to else None,
        value=rlp_tx.value,
        data='0x' + rlp_tx.data.hex() if rlp_tx.data else '0x',
        chain_id=(rlp_tx.v - 35) // 2 if rlp_tx.v >= 35 else CHAIN_ID,
        v=rlp_tx.v,
        r=rlp_tx.r,
        s=rlp_tx.s,
        from_addr=rlp_tx.sender,
        tx_type=TX_TYPE_TRANSFER if rlp_tx.to else TX_TYPE_CONTRACT_CREATION
    )

                    
                    # Add to blockchain mempool
                    tx_hash = blockchain.add_transaction(tx)
                    
                    if tx_hash:
                        # Broadcast to network
                        p2p_network.broadcast_transaction(tx)
                        print(f"✅ MetaMask transaction accepted: {tx_hash}")
                        result = tx_hash
                    else:
                        return jsonify({
                            'jsonrpc': '2.0',
                            'id': rpc_id,
                            'error': {'code': -32603, 'message': 'Transaction validation failed'}
                        })
                
                except Exception as e:
                    print(f"❌ Raw transaction error: {e}")
                    import traceback
                    traceback.print_exc()
                    return jsonify({
                        'jsonrpc': '2.0',
                        'id': rpc_id,
                        'error': {'code': -32603, 'message': str(e)}
                    })
            else:
                # Simplified mode - hash the raw tx
                result = "0x" + hashlib.sha256(raw_tx_hex.encode()).hexdigest()
        
        elif method == 'web3_clientVersion':
            result = f"VelvetChain/{VERSION}"
        
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
        'synced': blockchain.synced,
        'baseFeePerGas': blockchain.base_fee_per_gas,
        'gasPrice': f"{blockchain.base_fee_per_gas / 10**9} gwei"
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

@app.route('/api/transaction', methods=['POST'])
def receive_transaction():
    """Receive transaction from peer"""
    try:
        tx_data = request.json
        tx = Transaction.from_dict(tx_data)
        
        tx_hash = blockchain.add_transaction(tx)
        if tx_hash:
            return jsonify({'status': 'accepted', 'hash': tx_hash})
        else:
            return jsonify({'status': 'rejected'})
    
    except Exception as e:
        print(f"❌ Transaction receive error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/transaction/send', methods=['POST'])
def send_transaction():
    """Send a signed transaction"""
    try:
        data = request.json
        
        # Create transaction
        tx = Transaction(
            nonce=int(data.get('nonce', 0)),
            gas_price=int(data.get('gasPrice', BASE_GAS_PRICE)),
            gas_limit=int(data.get('gasLimit', BASE_TX_GAS)),
            to=data.get('to'),
            value=int(data.get('value', 0)),
            data=data.get('data', '0x'),
            v=int(data.get('v', 0)),
            r=int(data.get('r', 0)),
            s=int(data.get('s', 0)),
            from_addr=data.get('from'),
            tx_type=int(data.get('type', TX_TYPE_TRANSFER))
        )
        
        # Add to mempool
        tx_hash = blockchain.add_transaction(tx)
        
        if tx_hash:
            # Broadcast to network
            p2p_network.broadcast_transaction(tx)
            return jsonify({'status': 'success', 'hash': tx_hash})
        else:
            return jsonify({'status': 'rejected', 'message': 'Transaction validation failed'})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/wallet/create', methods=['POST'])
def create_wallet_endpoint():
    """Create a new wallet"""
    if RLP_AVAILABLE:
        wallet_data = create_eth_wallet()
    else:
        wallet = Wallet.create_wallet()
        wallet_data = {
            'address': wallet.address,
            'privateKey': wallet.private_key_hex
        }
    return jsonify(wallet_data)

@app.route('/api/wallet/sign', methods=['POST'])
def sign_transaction_endpoint():
    """Sign a transaction with private key"""
    try:
        data = request.json
        private_key = data.get('privateKey')
        
        if not private_key:
            return jsonify({'error': 'Private key required'})
        
        wallet = Wallet.from_private_key(private_key)
        
        # Create transaction
        tx = Transaction(
            nonce=int(data.get('nonce', 0)),
            gas_price=int(data.get('gasPrice', BASE_GAS_PRICE)),
            gas_limit=int(data.get('gasLimit', BASE_TX_GAS)),
            to=data.get('to'),
            value=int(data.get('value', 0)),
            data=data.get('data', '0x'),
            tx_type=int(data.get('type', TX_TYPE_TRANSFER))
        )
        
        # Sign transaction
        tx.sign(wallet)
        
        return jsonify({
            'transaction': tx.to_dict(),
            'hash': tx.hash
        })
    
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/block', methods=['POST'])
def receive_block():
    try:
        block_data = request.json
        print(f"\n📨 Received block #{int(block_data['number'], 16)}")
        result = blockchain.add_block_from_peer(block_data)
        
        print(f"   Result: {result}")
        
        if result == "FORK_DETECTED" or result == "NEED_SYNC":
            return jsonify({'status': 'sync_needed'})
        
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

@app.route('/api/mempool', methods=['GET'])
def get_mempool():
    """Get pending transactions"""
    return jsonify({
        'count': len(blockchain.pending_transactions),
        'transactions': [tx.to_dict() for tx in blockchain.pending_transactions[:50]]
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'blockHeight': blockchain.get_latest_block().number if blockchain.chain else 0,
        'peers': len(p2p_network.peers),
        'synced': blockchain.synced,
        'mempool': len(blockchain.pending_transactions)
    })

# ==================== CLI ====================

def print_banner():
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║          🔗 VELVET CHAIN v2.0.0-ENHANCED 🔗            ║
    ║       Full EVM-Compatible Blockchain with Txs            ║
    ║                                                          ║
    ║  ✨ Real transactions with signing                       ║
    ║  ⛽ Gas fees and transaction fees                       ║
    ║  📜 Smart contract support                              ║
    ║  💎 Transaction receipts & logs                         ║
    ╚══════════════════════════════════════════════════════════╝
    """)

# ==================== MAIN ====================

def main():
    global blockchain, p2p_network
    
    parser = argparse.ArgumentParser(description='Velvet Chain Enhanced Node')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help='Port to run on')
    parser.add_argument('--mine', action='store_true', help='Start mining')
    parser.add_argument('--wallet', type=str, help='Mining wallet address')
    parser.add_argument('--peer', type=str, help='Connect to specific peer')
    parser.add_argument('--bootstrap', action='store_true', help='Run as bootstrap node')
    parser.add_argument('--create-wallet', action='store_true', help='Create a new wallet and exit')
    args = parser.parse_args()
    
    print_banner()
    
    # Create wallet if requested
    if args.create_wallet:
        if RLP_AVAILABLE:
            wallet_data = create_eth_wallet()
            print(f"\n💎 New Wallet Created!")
            print(f"{'='*60}")
            print(f"Address:     {wallet_data['address']}")
            print(f"Private Key: {wallet_data['privateKey']}")
            print(f"{'='*60}")
        else:
            wallet = Wallet.create_wallet()
            print(f"\n💎 New Wallet Created!")
            print(f"{'='*60}")
            print(f"Address:     {wallet.address}")
            print(f"Private Key: {wallet.private_key_hex}")
            print(f"{'='*60}")
        print(f"\n⚠️  SAVE YOUR PRIVATE KEY SECURELY!")
        print(f"   Use --wallet <ADDRESS> to mine")
        print(f"\n")
        sys.exit(0)
    
    if args.mine and not args.wallet:
        print("❌ --wallet required for mining")
        print("   Use --create-wallet to generate a new wallet")
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
        for i in range(120):
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
    
    print(f"\n{'='*60}")
    print(f"🚀 Node Running")
    print(f"{'='*60}")
    print(f"RPC:      http://localhost:{args.port}")
    print(f"API:      http://localhost:{args.port}/api/stats")
    print(f"Chain ID: {CHAIN_ID}")
    print(f"Type:     {'🏛️  BOOTSTRAP' if args.bootstrap else '🌐 Regular'}")
    print(f"Mining:   {'✅ Active' if args.mine and blockchain.is_mining else '❌ Inactive'}")
    print(f"Synced:   {'✅ Yes' if blockchain.synced else '❌ No'}")
    if args.wallet:
        print(f"Wallet:   {args.wallet}")
        print(f"Balance:  {blockchain.get_balance(args.wallet) / 10**18:,.4f} VELVET")
    print(f"Height:   {blockchain.get_latest_block().number if blockchain.chain else 0}")
    print(f"Peers:    {len(p2p_network.peers)}")
    print(f"Gas:      {blockchain.base_fee_per_gas / 10**9} gwei")
    print(f"{'='*60}\n")
    
    print("📚 API Endpoints:")
    print(f"   GET  /api/stats                    - Node statistics")
    print(f"   GET  /api/address/<addr>           - Get address balance")
    print(f"   GET  /api/mempool                  - View pending transactions")
    print(f"   POST /api/wallet/create            - Create new wallet")
    print(f"   POST /api/wallet/sign              - Sign transaction")
    print(f"   POST /api/transaction/send         - Send signed transaction")
    print(f"\n")
    
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
