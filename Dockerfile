# Velvet Chain - Docker Image
# Build: docker build -t velvet-chain .
# Run:   docker run -p 8545:8545 velvet-chain --mine --wallet 0xYourAddress

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY node.py .
COPY explorer/ ./explorer/

# Create data directory
RUN mkdir -p /data

# Expose RPC port
EXPOSE 8545

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8545/api/stats')"

# Set entrypoint
ENTRYPOINT ["python", "node.py"]

# Default command (can be overridden)
CMD ["--port", "8545"]

# Labels
LABEL maintainer="hello@velvetchain.network"
LABEL version="1.0.0"
LABEL description="Velvet Chain - Decentralized EVM-Compatible Blockchain"