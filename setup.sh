#!/usr/bin/env bash
# Cài đặt một lần — Git Bash / MSYS trên Windows:
#   bash setup.sh

set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -d .venv ]]; then
  python -m venv .venv
fi

# Git Bash: kích hoạt venv (KHÔNG dùng Activate.ps1)
# shellcheck disable=SC1091
source .venv/Scripts/activate

python -m pip install -U pip
pip install -r requirements.txt
python -m playwright install chromium

if [[ ! -f .env ]]; then
  cp config.example.env .env
fi

echo ""
echo "Xong. Trong Git Bash, kích hoạt venv:"
echo "  source .venv/Scripts/activate"
echo ""
echo "Chạy tool:"
echo '  python main.py -k "từ khóa" --headed'
