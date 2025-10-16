#!/bin/bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

if ! command -v python3 >/dev/null 2>&1; then
  osascript -e 'display dialog "Python 3 is not installed. Install it first." buttons {"OK"} default button 1'
  exit 1
fi

# Step 1: migrations (OTP etc.)
python3 -m app.migrations_add_otp

# Step 2: create first admin (prompts in this window)
python3 "$DIR/create_admin.py"

osascript -e 'display notification "Database initialized and admin created" with title "Hudson’s App"'
read -p "✅ Done. Press Return to close... "
