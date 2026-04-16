#!/bin/bash
# NCERT Book Browser - Launcher Script
# Usage: ./run.sh [options]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Setting up virtual environment..."
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install -q -r requirements.txt
fi

source "$VENV_DIR/bin/activate"
python "$SCRIPT_DIR/ncert_browser.py" "$@"
