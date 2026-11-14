#!/usr/bin/env bash
# Git Bash / MSYS — cửa sổ app (không mở Streamlit)
set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -d .venv ]]; then
  python -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/Scripts/activate

python -m pip install -q -r requirements.txt
exec python desktop_app.py
