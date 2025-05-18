#!/usr/bin/env bash
# setup_env.sh
# 간단 자동 설정 스크립트 (macOS/Linux)
set -e

echo "[1/3] Creating virtual environment..."
python3 -m venv venv

echo "[2/3] Activating venv and installing requirements..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "[3/3] Done!  Now run: \nsource venv/bin/activate && streamlit run posture_guardian/main.py" 