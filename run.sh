#!/usr/bin/env bash
# Quick launcher for RegimeShift AI
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    echo "Installing required dependencies..."
    ./.venv/bin/pip install -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com -r requirements.txt
fi

echo "=========================================================="
echo " Starting QUANTREGIME AI Dashboard..."
echo " Open your browser to http://localhost:8501"
echo "=========================================================="
./.venv/bin/streamlit run app.py
