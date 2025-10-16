#!/bin/bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
REQ="$DIR/app/requirements.txt"
[ -f "$DIR/requirements.txt" ] && REQ="$DIR/requirements.txt"

if ! command -v python3 >/dev/null 2>&1; then
  osascript -e 'display dialog "Python 3 is not installed. Click OK to open python.org downloads." buttons {"OK"} default button 1'
  open "https://www.python.org/downloads/"
  read -p "Install Python 3, then re-run this installer. Press Return to close... "
  exit 1
fi

python3 -m pip install --upgrade pip wheel setuptools
python3 -m pip install -r "$REQ"

osascript -e 'display notification "All dependencies installed" with title "Hudson’s App"'
read -p "✅ Done. Press Return to close... "
