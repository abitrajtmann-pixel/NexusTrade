#!/bin/bash
echo ""
echo " ╔══════════════════════════════════════════════════════╗"
echo " ║     NEXUSTRADE - macOS Build System                   ║"
echo " ╚══════════════════════════════════════════════════════╝"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERROR: Python3 not found. Install from https://www.python.org/"
    exit 1
fi

echo "[1/4] Installing dependencies..."
python3 -m pip install --upgrade pip -q
python3 -m pip install PyQt6 pyqtgraph yfinance pandas numpy scikit-learn pyqtdarktheme pyinstaller -q

echo "[2/4] Building app bundle..."
cd src
python3 -m PyInstaller \
    --onefile \
    --windowed \
    --name "NexusTrade" \
    --add-data ".:." \
    --hidden-import PyQt6 \
    --hidden-import pyqtgraph \
    --hidden-import yfinance \
    --hidden-import sklearn.ensemble \
    --hidden-import sklearn.preprocessing \
    --collect-all pyqtgraph \
    --collect-all qdarktheme \
    --noconfirm \
    main.py

echo "[3/4] Moving app..."
if [ -f "dist/NexusTrade" ]; then
    mv dist/NexusTrade ../NexusTrade
    chmod +x ../NexusTrade
    cd ..
    echo ""
    echo " ✅  BUILD COMPLETE!"
    echo "    Run ./NexusTrade to launch the platform"
    echo ""
    ./NexusTrade &
elif [ -d "dist/NexusTrade.app" ]; then
    cp -r dist/NexusTrade.app ..
    cd ..
    echo ""
    echo " ✅  BUILD COMPLETE!"
    echo "    Double-click NexusTrade.app to launch!"
    open NexusTrade.app
fi
