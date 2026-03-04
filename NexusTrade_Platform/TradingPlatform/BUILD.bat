@echo off
title NexusTrade - Build System
color 0B
cls

echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║           NEXUSTRADE - PROFESSIONAL TRADING PLATFORM         ║
echo  ║                    BUILD SYSTEM v2.0                         ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.
echo  This will install all dependencies and build the .exe file.
echo  Estimated time: 3-8 minutes depending on your machine.
echo.
pause

:: Check Python
echo  [1/6] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERROR: Python is not installed or not in PATH.
    echo  Please install Python 3.10+ from https://www.python.org/downloads/
    echo  Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)
echo        Python found OK

:: Upgrade pip
echo  [2/6] Upgrading pip...
python -m pip install --upgrade pip -q

:: Install dependencies
echo  [3/6] Installing dependencies (this may take 2-4 minutes)...
python -m pip install PyQt6 pyqtgraph yfinance pandas numpy scikit-learn pyqtdarktheme pyinstaller -q
if errorlevel 1 (
    echo.
    echo  ERROR: Failed to install dependencies.
    echo  Try running this script as Administrator.
    echo.
    pause
    exit /b 1
)
echo        Dependencies installed OK

:: Create assets directory
echo  [4/6] Preparing assets...
if not exist "src\assets" mkdir src\assets

:: Build the executable
echo  [5/6] Building executable (this takes 2-5 minutes)...
cd src
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "NexusTrade" ^
    --add-data ".;." ^
    --hidden-import PyQt6 ^
    --hidden-import PyQt6.QtCore ^
    --hidden-import PyQt6.QtGui ^
    --hidden-import PyQt6.QtWidgets ^
    --hidden-import pyqtgraph ^
    --hidden-import yfinance ^
    --hidden-import pandas ^
    --hidden-import numpy ^
    --hidden-import sklearn ^
    --hidden-import sklearn.ensemble ^
    --hidden-import sklearn.preprocessing ^
    --hidden-import sklearn.model_selection ^
    --hidden-import qdarktheme ^
    --hidden-import requests ^
    --collect-all pyqtgraph ^
    --collect-all qdarktheme ^
    --noconfirm ^
    main.py

if errorlevel 1 (
    echo.
    echo  ERROR: Build failed. Check the output above for details.
    echo.
    cd ..
    pause
    exit /b 1
)

:: Move exe to parent directory
echo  [6/6] Finalizing...
if exist "dist\NexusTrade.exe" (
    move "dist\NexusTrade.exe" "..\NexusTrade.exe" >nul
    cd ..
    echo.
    echo  ╔══════════════════════════════════════════════════════════════╗
    echo  ║                  BUILD SUCCESSFUL!                           ║
    echo  ║                                                              ║
    echo  ║   NexusTrade.exe has been created in this folder.           ║
    echo  ║   Double-click NexusTrade.exe to launch the platform!       ║
    echo  ╚══════════════════════════════════════════════════════════════╝
    echo.
    echo  Launching NexusTrade now...
    start "" "NexusTrade.exe"
) else (
    cd ..
    echo  Build file not found. Check src\dist\ folder manually.
)

echo.
pause
