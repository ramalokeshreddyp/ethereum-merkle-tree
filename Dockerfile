# ─────────────────────────────────────────────────────────────
# Ethereum Merkle Tree Verifier — Dockerfile
# Base: python:3.11-slim
# ─────────────────────────────────────────────────────────────

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system build deps needed by pysha3
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifest first (layer-cache friendly)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Default command: run the full end-to-end pipeline
# Override with docker-compose or docker run -- e.g.:
#   docker run ethereum-merkle-tree python main.py --part 1
CMD ["python", "main.py"]
