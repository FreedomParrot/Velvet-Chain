# 🔗 Velvet Chain

**A decentralized, EVM-compatible blockchain that anyone can mine!**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Network Status](https://img.shields.io/badge/network-live-success)](https://velvetchain.network)

---

## 🌟 Features

- ✅ **True Decentralization** - Anyone can run a node and mine
- ✅ **EVM Compatible** - Works with MetaMask and Web3 tools
- ✅ **Fair Mining** - Proof of Work with automatic difficulty adjustment
- ✅ **Easy Setup** - Get mining in under 5 minutes
- ✅ **Beautiful Explorer** - Track blocks and transactions in real-time
- ✅ **Auto Peer Discovery** - Connects to the network automatically
- ✅ **Mining Rewards** - Earn 50 VELVET per block

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- MetaMask wallet (optional, for sending transactions)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/freedomparrot/velvet-chain.git
cd velvet-chain
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Start mining!**
```bash
python node.py --mine --wallet YOUR_WALLET_ADDRESS
```

Replace `YOUR_WALLET_ADDRESS` with your MetaMask wallet address (e.g., `0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb1`)

That's it! You're now mining VELVET tokens! 🎉

---

## 💻 Usage

### Run a Mining Node

```bash
python node.py --mine --wallet 0xYourWalletAddress
```

**Earns:** 50 VELVET per block mined

### Run a Full Node (No Mining)

```bash
python node.py
```

Helps secure the network and relay transactions

### Custom Port

```bash
python node.py --port 8546 --mine --wallet 0xYourWalletAddress
```

### View the Explorer

Open your browser to:
```
http://localhost:8545/explorer
```

---

## 🦊 Connect to MetaMask

1. Open MetaMask
2. Click network dropdown → "Add Network"
3. Enter the following details:

| Field | Value |
|-------|-------|
| Network Name | Velvet Chain |
| RPC URL | http://173.255.229.107:8545 |
| Chain ID | 16523431 |
| Currency Symbol | VELVET |

4. Click "Save"
5. Your VELVET balance will appear in MetaMask!

---

## ⛏️ Mining Information

### How Mining Works

Velvet Chain uses **Proof of Work** consensus:

1. Your node collects pending transactions
2. Creates a new block with transactions + your mining reward
3. Finds a valid hash by trying different nonces
4. Broadcasts the block to the network
5. You receive 50 VELVET! 💰

### Mining Rewards

- **Block Reward:** 50 VELVET per block
- **Target Block Time:** 10 seconds
- **Difficulty Adjustment:** Every 100 blocks
- **Expected Daily Earnings:** ~432,000 VELVET (if mining alone)

### Hardware Requirements

**Minimum:**
- CPU: 2 cores
- RAM: 2 GB
- Disk: 10 GB
- Internet: 5 Mbps

**Recommended:**
- CPU: 4+ cores
- RAM: 4+ GB
- Disk: 50+ GB
- Internet: 10+ Mbps

*Note: Velvet uses CPU mining. More CPU cores = higher mining chance*

---

## 🌐 Network Information

### Mainnet Details

- **Network Name:** Velvet Chain
- **Chain ID:** 16523431
- **Currency:** VELVET
- **Total Supply:** 1,000,000 VELVET (initial) + mining rewards capped at 21,000,000 with halving every new era !
- **Block Explorer:** https://explorer.velvetchain.network
- **Genesis Block:** December 29, 2024

### Bootstrap Nodes

The network automatically connects to bootstrap nodes:
- `https://velvet-bootstrap-1.network:8545`
- `https://velvet-bootstrap-2.network:8545`

### Current Network Stats

Check live stats at: https://stats.velvetchain.network

---

## 📊 Block Explorer

The included block explorer shows:

- ✅ Real-time blockchain statistics
- ✅ Latest blocks and transactions
- ✅ Mining difficulty and hashrate
- ✅ Network peer count
- ✅ Your wallet balance
- ✅ Transaction history

Access at: `http://localhost:8545/explorer`

---

## 🔧 Advanced Configuration

### Environment Variables

Create a `.env` file:

```bash
VELVET_PORT=8545
VELVET_WALLET=0xYourAddress
VELVET_BOOTSTRAP_NODES=http://node1.com:8545,http://node2.com:8545
VELVET_MAX_PEERS=25
```

### Running as a Service (Linux)

Create `/etc/systemd/system/velvet-node.service`:

```ini
[Unit]
Description=Velvet Chain Node
After=network.target

[Service]
Type=simple
User=velvet
WorkingDirectory=/home/velvet/velvet-chain
ExecStart=/usr/bin/python3 node.py --mine --wallet 0xYourAddress
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable velvet-node
sudo systemctl start velvet-node
sudo systemctl status velvet-node
```

### Docker Support

```bash
docker build -t velvet-chain .
docker run -p 8545:8545 velvet-chain --mine --wallet 0xYourAddress
```

---

## 🤝 Contributing

We love contributions! Here's how to help:

### Setting Up Development

```bash
git clone https://github.com/yourusername/velvet-chain.git
cd velvet-chain
pip install -r requirements-dev.txt
python -m pytest tests/
```

### Contribution Guidelines

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### What We Need

- 🐛 Bug fixes
- ✨ New features
- 📝 Documentation improvements
- 🧪 Test coverage
- 🌐 Translations
- 🎨 UI improvements

---

## 📖 API Documentation

### JSON-RPC Endpoints

Velvet Chain implements Ethereum JSON-RPC for MetaMask compatibility:

```javascript
// Get chain ID
POST http://localhost:8545
{
  "jsonrpc": "2.0",
  "method": "eth_chainId",
  "params": [],
  "id": 1
}

// Get balance
POST http://localhost:8545
{
  "jsonrpc": "2.0",
  "method": "eth_getBalance",
  "params": ["0xYourAddress", "latest"],
  "id": 1
}
```

### REST API

```bash
# Get blockchain stats
GET http://localhost:8545/api/stats

# Get latest blocks
GET http://localhost:8545/api/chain

# Get specific block
GET http://localhost:8545/api/block/123

# Get address info
GET http://localhost:8545/api/address/0xYourAddress

# Get connected peers
GET http://localhost:8545/api/peers
```

---

## 🔐 Security

### Best Practices

- ✅ Never share your private keys
- ✅ Use a hardware wallet for large amounts
- ✅ Keep your node software updated
- ✅ Use a firewall to protect RPC port
- ✅ Regular backups of blockchain data

### Reporting Vulnerabilities

Found a security issue? Email: security@velvetchain.network

**Do not** create public issues for security vulnerabilities.

---

## 🗺️ Roadmap

### Phase 1: Launch (Q1 2025) ✅
- [x] Core blockchain implementation
- [x] P2P networking
- [x] Mining support
- [x] Block explorer
- [x] MetaMask integration

### Phase 2: Growth (Q2 2025)
- [ ] Smart contract support
- [ ] Mobile wallet app
- [ ] Mining pool software
- [ ] Hardware wallet support
- [ ] DEX listing

### Phase 3: Ecosystem (Q3 2025)
- [ ] DeFi protocols
- [ ] NFT marketplace
- [ ] Bridge to Ethereum
- [ ] Validator nodes
- [ ] DAO governance

### Phase 4: Enterprise (Q4 2025)
- [ ] Private chains
- [ ] Enterprise APIs
- [ ] Advanced analytics
- [ ] Institutional support

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🌍 Community

### Join Us!

- 💬 **Discord:** https://discord.gg/velvetchain
- 🐦 **Twitter:** https://twitter.com/velvetchain
- 📱 **Telegram:** https://t.me/velvetchain
- 📧 **Email:** hello@velvetchain.network
- 🌐 **Website:** https://velvetchain.network

### Community Nodes

Help us grow the network! List your public node:
- Open an issue with your node URL
- We'll add it to the bootstrap nodes
- Earn community recognition! 🏆

---

## ❓ FAQ

**Q: How much can I earn mining?**  
A: Depends on network hashrate. With 10-second blocks, ~8,640 blocks/day × 50 VELVET = 432,000 VELVET/day (if mining alone).

**Q: Can I mine on multiple computers?**  
A: Yes! Each computer increases your chances.

**Q: Is this a scam/rugpull?**  
A: No! Open source, no premine (except initial supply for development), fully decentralized.

**Q: What can I do with VELVET tokens?**  
A: Hold, trade on DEXes, use in DeFi, send to friends, or stake (coming soon).

**Q: Can I run this on a Raspberry Pi?**  
A: Yes! Works great on ARM devices.

**Q: How is this different from Bitcoin/Ethereum?**  
A: EVM-compatible (smart contracts), faster blocks, easier mining, modern codebase.

---

## 🙏 Acknowledgments

Built with:
- Python 3
- Flask
- Web3.py
- eth-account
- And lots of ☕

Special thanks to:
- The Ethereum community
- Bitcoin pioneers
- All our contributors
- You, for mining! 🎉

---

## 📈 Stats

![GitHub stars](https://img.shields.io/github/stars/yourusername/velvet-chain?style=social)
![GitHub forks](https://img.shields.io/github/forks/yourusername/velvet-chain?style=social)
![GitHub issues](https://img.shields.io/github/issues/yourusername/velvet-chain)
![GitHub pull requests](https://img.shields.io/github/issues-pr/yourusername/velvet-chain)

---

<div align="center">

**Made with ❤️ by the Velvet Chain Community**

[Website](https://velvetchain.network) • [Docs](https://docs.velvetchain.network) • [Explorer](https://explorer.velvetchain.network)

</div>
