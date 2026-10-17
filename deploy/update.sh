#!/usr/bin/env bash
# GitHub se naya code laata hai aur app restart karta hai.
# Chalane ka tareeka (listing-ai folder ke andar se):  bash deploy/update.sh
set -e
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$APP_DIR"

git pull
venv/bin/pip install -q -r requirements.txt
systemctl restart listing-ai
sleep 2

if systemctl is-active --quiet listing-ai; then
  echo "✅ Update ho gaya, app chal raha hai."
else
  echo "❌ App start nahi hua. Neeche ka error screenshot karke bhejo:"
  journalctl -u listing-ai -n 30 --no-pager
  exit 1
fi
