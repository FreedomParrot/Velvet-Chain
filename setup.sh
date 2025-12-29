#!/bin/bash

# Velvet Chain - Automated Setup Script
# This script will set up everything you need to start mining!

set -e

echo "╔══════════════════════════════════════════════════════════╗"
echo "║                                                          ║"
echo "║              🔗 VELVET CHAIN SETUP                       ║"
echo "║         Let's get you mining in under 5 minutes!         ║"
echo "║                                                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo "🔍 Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    
    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; then
        echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION detected"
    else
        echo -e "${RED}✗${NC} Python 3.8+ required (found $PYTHON_VERSION)"
        exit 1
    fi
else
    echo -e "${RED}✗${NC} Python 3 not found. Please install Python 3.8+"
    exit 1
fi

# Check pip
echo "🔍 Checking pip..."
if command -v pip3 &> /dev/null; then
    echo -e "${GREEN}✓${NC} pip3 found"
else
    echo -e "${RED}✗${NC} pip3 not found. Installing..."
    python3 -m ensurepip
fi

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} All dependencies installed!"
else
    echo -e "${RED}✗${NC} Failed to install dependencies"
    exit 1
fi

# Create explorer directory if it doesn't exist
echo ""
echo "📁 Setting up explorer..."
mkdir -p explorer

# Download or create explorer HTML
if [ ! -f "explorer/index.html" ]; then
    echo -e "${YELLOW}!${NC} Explorer HTML not found. Please add explorer/index.html"
fi

# Ask for wallet address
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "💰 WALLET SETUP"
echo ""
echo "To mine VELVET tokens, you need a wallet address."
echo "If you have MetaMask, copy your address from there."
echo "Format: 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb1"
echo ""
read -p "Enter your wallet address: " WALLET_ADDRESS

# Validate wallet address format
if [[ ! $WALLET_ADDRESS =~ ^0x[a-fA-F0-9]{40}$ ]]; then
    echo -e "${RED}✗${NC} Invalid wallet address format"
    echo "   Address must start with 0x and be 42 characters long"
    exit 1
fi

echo -e "${GREEN}✓${NC} Wallet address validated!"

# Ask for mining preference
echo ""
echo "⛏️  Do you want to mine VELVET tokens? (y/n)"
read -p "Mine: " MINE_CHOICE

if [[ $MINE_CHOICE == "y" || $MINE_CHOICE == "Y" ]]; then
    MINE_FLAG="--mine"
    echo -e "${GREEN}✓${NC} Mining enabled!"
else
    MINE_FLAG=""
    echo -e "${YELLOW}!${NC} Running as full node (no mining)"
fi

# Ask for port
echo ""
read -p "RPC Port (default 8545): " PORT
PORT=${PORT:-8545}

# Create startup script
echo ""
echo "📝 Creating startup script..."

cat > start-node.sh << EOF
#!/bin/bash
# Velvet Chain Node Startup Script
# Generated: $(date)

python3 node.py --port $PORT $MINE_FLAG --wallet $WALLET_ADDRESS
EOF

chmod +x start-node.sh

echo -e "${GREEN}✓${NC} Startup script created!"

# Create systemd service file (optional)
echo ""
echo "🔧 Do you want to create a systemd service (Linux only)? (y/n)"
read -p "Create service: " SERVICE_CHOICE

if [[ $SERVICE_CHOICE == "y" || $SERVICE_CHOICE == "Y" ]]; then
    CURRENT_DIR=$(pwd)
    CURRENT_USER=$(whoami)
    
    cat > velvet-node.service << EOF
[Unit]
Description=Velvet Chain Mining Node
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$CURRENT_DIR
ExecStart=$CURRENT_DIR/start-node.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    echo ""
    echo "Service file created: velvet-node.service"
    echo ""
    echo "To install (requires sudo):"
    echo "  sudo cp velvet-node.service /etc/systemd/system/"
    echo "  sudo systemctl enable velvet-node"
    echo "  sudo systemctl start velvet-node"
    echo ""
fi

# Final instructions
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                                                          ║"
echo "║              ✅ SETUP COMPLETE!                          ║"
echo "║                                                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "🚀 Quick Start:"
echo "   ./start-node.sh"
echo ""
echo "🌐 Access Points:"
echo "   RPC:      http://localhost:$PORT"
echo "   Explorer: http://localhost:$PORT/explorer"
echo ""
echo "💰 Your Wallet:"
echo "   Address: $WALLET_ADDRESS"
echo ""
echo "⛏️  Mining Status:"
if [[ $MINE_FLAG == "--mine" ]]; then
    echo "   ${GREEN}ENABLED${NC} - You'll earn 50 VELVET per block!"
    echo ""
    echo "   Expected earnings (if mining alone):"
    echo "   • Per hour:   ~18,000 VELVET"
    echo "   • Per day:    ~432,000 VELVET"
    echo "   • Per month:  ~12,960,000 VELVET"
else
    echo "   DISABLED - Running as full node"
fi
echo ""
echo "🦊 Add to MetaMask:"
echo "   Network:  Velvet Chain"
echo "   RPC URL:  http://localhost:$PORT"
echo "   Chain ID: 16523431"
echo "   Symbol:   VELVET"
echo ""
echo "📚 Documentation:"
echo "   README: ./README.md"
echo "   GitHub: https://github.com/yourusername/velvet-chain"
echo ""
echo "💬 Community:"
echo "   Discord:  https://discord.gg/velvetchain"
echo "   Twitter:  https://twitter.com/velvetchain"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Ready to start mining? Run: ./start-node.sh"
echo ""