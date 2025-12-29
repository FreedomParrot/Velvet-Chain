# 🚀 Velvet Chain - Quick Start Guide

Get mining in under 5 minutes!

---

## Prerequisites

- Python 3.8+ installed
- MetaMask wallet (optional)
- 10 GB free disk space
- Internet connection

---

## Installation

### Option 1: Automated Setup (Recommended)

```bash
# Clone repository
git clone https://github.com/yourusername/velvet-chain.git
cd velvet-chain

# Run setup script
chmod +x setup.sh
./setup.sh
```

The setup script will:
- ✅ Check Python version
- ✅ Install dependencies
- ✅ Configure your wallet
- ✅ Create startup script
- ✅ Set up systemd service (optional)

### Option 2: Manual Setup

```bash
# Clone repository
git clone https://github.com/yourusername/velvet-chain.git
cd velvet-chain

# Install dependencies
pip install -r requirements.txt

# Start mining node
python node.py --mine --wallet YOUR_WALLET_ADDRESS
```

---

## Running Your Node

### Mining Node (Earns Rewards)

```bash
python node.py --mine --wallet 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb1
```

**Output:**
```
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║              🔗 VELVET CHAIN v1.0.0                      ║
║         Decentralized EVM-Compatible Blockchain          ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝

✅ Genesis block created
💰 Initial supply: 1,000,000 VELVET → 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb1
🌐 P2P network started on port 8545
⛏️  Mining started! Rewards → 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb1
🎯 Target block time: 10s | Reward: 50 VELVET

============================================================
🚀 Node Running
============================================================
RPC Endpoint:     http://localhost:8545
Explorer:         http://localhost:8545/explorer
Chain ID:         16523431
Mining:           ✅ Active
Wallet:           0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb1
Balance:          1,000,000.00 VELVET
Peers:            0
============================================================

⛏️  Mining block #1 (difficulty: 4)...
   Mining... 523,489 attempts
⛏️  Block #1 mined! Hash: 0x00009a2b... (523489 H/s)
✅ Block #1 added to chain
💰 Mining reward: 50 VELVET → 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb1
```

### Full Node (No Mining)

```bash
python node.py
```

This runs a full node that validates and relays blocks without mining.

### Custom Port

```bash
python node.py --port 8546 --mine --wallet 0xYourAddress
```

---

## Connecting to MetaMask

### Method 1: One-Click (Using Explorer)

1. Open browser to `http://localhost:8545/explorer`
2. Click "🦊 Add to MetaMask" button
3. Approve in MetaMask
4. Done! ✅

### Method 2: Manual Setup

1. Open MetaMask
2. Click network dropdown
3. Select "Add Network"
4. Enter these details:

```
Network Name:     Velvet Chain
RPC URL:          http://localhost:8545
Chain ID:         16523431
Currency Symbol:  VELVET
```

5. Click "Save"
6. Switch to Velvet Chain network

### Viewing Your Balance

Your VELVET balance will appear in MetaMask automatically!

---

## Checking Your Earnings

### Method 1: Block Explorer

Visit: `http://localhost:8545/explorer`

You'll see:
- Your current balance
- Blocks you've mined
- Pending transactions
- Network statistics

### Method 2: Command Line

```bash
# Check balance via API
curl -X POST http://localhost:8545 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "eth_getBalance",
    "params": ["YOUR_WALLET_ADDRESS", "latest"],
    "id": 1
  }'
```

### Method 3: MetaMask

Just open MetaMask - your balance shows automatically!

---

## Running on VPS

### Setup on Ubuntu/Debian

```bash
# Connect to your VPS
ssh user@your-vps-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3
sudo apt install python3 python3-pip git -y

# Clone and setup
git clone https://github.com/yourusername/velvet-chain.git
cd velvet-chain
pip3 install -r requirements.txt

# Start mining
python3 node.py --mine --wallet YOUR_WALLET_ADDRESS
```

### Run as Background Service

```bash
# Create service file
sudo nano /etc/systemd/system/velvet-node.service
```

Add this content:

```ini
[Unit]
Description=Velvet Chain Mining Node
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/velvet-chain
ExecStart=/usr/bin/python3 node.py --mine --wallet YOUR_WALLET_ADDRESS
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable velvet-node
sudo systemctl start velvet-node
sudo systemctl status velvet-node
```

### View Logs

```bash
# Real-time logs
sudo journalctl -u velvet-node -f

# Recent logs
sudo journalctl -u velvet-node -n 100
```

---

## Docker Setup

### Single Mining Node

```bash
# Build image
docker build -t velvet-chain .

# Run container
docker run -d \
  --name velvet-miner \
  -p 8545:8545 \
  velvet-chain \
  --mine --wallet YOUR_WALLET_ADDRESS

# View logs
docker logs -f velvet-miner
```

### Multiple Nodes with Docker Compose

```bash
# Set wallet addresses
export WALLET_ADDRESS_1=0xYourAddress1
export WALLET_ADDRESS_2=0xYourAddress2

# Start all nodes
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all nodes
docker-compose down
```

---

## Mining Tips

### Maximize Your Earnings

1. **Use Multiple Machines**
   - Run nodes on multiple computers
   - Each increases your mining chance
   - Use different wallet addresses

2. **Optimize Performance**
   - Close unnecessary programs
   - Use faster CPU (more cores = better)
   - Keep system cool for sustained performance

3. **Stay Connected**
   - Ensure stable internet connection
   - Use wired connection over WiFi
   - Monitor for disconnections

4. **Run 24/7**
   - Use VPS for constant uptime
   - Set up auto-restart on crashes
   - Monitor remotely

### Expected Earnings

With 10-second block time:
- **Per Hour:** ~360 blocks × 50 VELVET = 18,000 VELVET
- **Per Day:** ~8,640 blocks × 50 VELVET = 432,000 VELVET
- **Per Month:** ~259,200 blocks × 50 VELVET = 12,960,000 VELVET

*Note: Earnings depend on network hashrate and your share*

---

## Troubleshooting

### Node Won't Start

```bash
# Check Python version
python3 --version  # Should be 3.8+

# Reinstall dependencies
pip3 install --upgrade -r requirements.txt

# Check port availability
sudo lsof -i :8545
```

### Can't Connect to MetaMask

1. Verify node is running: `http://localhost:8545/api/stats`
2. Check Chain ID is correct: 16523431
3. Try manual network addition
4. Restart MetaMask

### Mining is Slow

- Normal! Mining takes time (Proof of Work)
- Higher difficulty = slower mining
- More CPU cores = faster mining
- Check system resources (CPU, RAM)

### No Peers Connecting

- Check firewall settings
- Ensure port 8545 is open
- Wait for peer discovery (takes ~30 seconds)
- Bootstrap nodes may be down (normal)

### Balance Not Showing

- Wait for block confirmation (10 seconds)
- Refresh MetaMask
- Check correct wallet address
- Verify you're on Velvet Chain network

---

## Next Steps

### 1. Join the Community

- **Discord:** https://discord.gg/velvetchain
- **Twitter:** https://twitter.com/velvetchain
- **Telegram:** https://t.me/velvetchain

### 2. Contribute

- Report bugs: GitHub Issues
- Suggest features: GitHub Discussions
- Submit code: Pull Requests
- Help others: Discord/Telegram

### 3. Build on Velvet

- Deploy smart contracts (coming soon)
- Create DeFi protocols
- Build NFT marketplaces
- Develop dApps

### 4. Spread the Word

- Share on social media
- Write blog posts
- Create tutorials
- Run community nodes

---

## Useful Commands

```bash
# Start mining node
python node.py --mine --wallet 0xYourAddress

# Start full node (no mining)
python node.py

# Custom port
python node.py --port 8546

# Check node status
curl http://localhost:8545/api/stats

# Get blockchain data
curl http://localhost:8545/api/chain

# Check address balance
curl http://localhost:8545/api/address/0xYourAddress

# View connected peers
curl http://localhost:8545/api/peers

# Stop node (Ctrl+C)
# Or if running as service:
sudo systemctl stop velvet-node
```

---

## Getting Help

**Need support?**

1. Check documentation: [README.md](README.md)
2. Search issues: [GitHub Issues](https://github.com/yourusername/velvet-chain/issues)
3. Ask community: [Discord](https://discord.gg/velvetchain)
4. Email: support@velvetchain.network

---

## Security Tips

🔒 **Keep Your Keys Safe**
- Never share your private key
- Use hardware wallet for large amounts
- Backup your wallet
- Use strong passwords

🔒 **Secure Your Node**
- Keep software updated
- Use firewall
- Monitor for suspicious activity
- Regular security audits

---

**Happy Mining! ⛏️💰**

Start earning VELVET tokens today!