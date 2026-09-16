#!/usr/bin/env bash
set -e

echo "⚡ Starting InnerTube Pro Studio..."
cd "$(dirname "$0")"

# Ensure dependencies are installed
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️ WARNING: ffmpeg not detected! Video muxing may be limited."
fi

python3 -m pip install -q -r requirements.txt || true

echo "🚀 Launching Multi-Threaded Daemon on http://127.0.0.1:5050"
exec python3 server.py
