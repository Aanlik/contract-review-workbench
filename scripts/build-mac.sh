#!/bin/bash
set -e

echo "============================================"
echo "  Contract Review Workbench - macOS Build"
echo "============================================"
echo ""

cd "$(dirname "$0")/.."

# Install Python deps
echo "[1/5] Installing Python dependencies..."
.venv/bin/pip install pyinstaller --quiet

# Build frontend
echo "[2/5] Building frontend..."
cd frontend && npm run build && cd ..

# Run PyInstaller
echo "[3/5] Building macOS executable..."
.venv/bin/pyinstaller backend/contract_review.spec --clean --noconfirm

# Setup data
echo "[4/5] Setting up data directory..."
mkdir -p dist/contract-review/data/storage

# Create startup script
echo "[5/5] Creating startup script..."
cat > dist/contract-review/start.sh << 'STARTEOF'
#!/bin/bash
cd "$(dirname "$0")"
echo "=========================================="
echo "  Contract Review Workbench"
echo "  http://127.0.0.1:8000"
echo "=========================================="
echo ""
./contract-review
STARTEOF
chmod +x dist/contract-review/start.sh

echo ""
echo "============================================"
echo "  Build complete!"
echo "  Output: dist/contract-review/"
echo "  Run: ./dist/contract-review/start.sh"
echo "============================================"
