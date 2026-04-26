#!/bin/bash
# Deploy EvoPlay to Oracle Cloud server
# Usage: ./deploy.sh

SERVER="ubuntu@129.80.245.31"
KEY="/Users/shaoshao/Desktop/ssh-key-2026-03-29.key"
REMOTE_DIR="/home/ubuntu/EvoPlay"

echo "=== Step 1: Sync code to server ==="
rsync -avz --exclude 'node_modules' --exclude '__pycache__' --exclude '.git' \
    --exclude 'backend/logs' --exclude 'backend/llm_logs' --exclude 'agent_logs' \
    --exclude 'evolution_logs' --exclude 'human_data' \
    -e "ssh -i $KEY" \
    /Users/shaoshao/Desktop/EvoPlay/ $SERVER:$REMOTE_DIR/

echo "=== Step 2: Build and run on server ==="
ssh -i $KEY $SERVER << 'REMOTE'
cd /home/ubuntu/EvoPlay

# Ensure data directories and files exist
mkdir -p /home/ubuntu/evoplay-data/logs
mkdir -p /home/ubuntu/evoplay-data/llm_logs
[ -f /home/ubuntu/evoplay-data/players.json ] || echo '{"players":[]}' > /home/ubuntu/evoplay-data/players.json

# Build Docker image
docker build -t evoplay .

# Stop old container if running
docker stop evoplay 2>/dev/null
docker rm evoplay 2>/dev/null

# Run new container
docker run -d --name evoplay \
    -p 80:5001 \
    -v /home/ubuntu/evoplay-data/logs:/app/backend/logs \
    -v /home/ubuntu/evoplay-data/llm_logs:/app/backend/llm_logs \
    -v /home/ubuntu/evoplay-data/players.json:/app/backend/players.json \
    -e FLASK_DEBUG=0 \
    --restart unless-stopped \
    evoplay

echo ""
echo "=== Deploy complete ==="
docker ps | grep evoplay
REMOTE

echo ""
echo "=== Access at: http://129.80.245.31 ==="
