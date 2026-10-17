#!/usr/bin/env bash
# Listing AI ko 24x7 chalne wali service banata hai.
# Chalane ka tareeka (listing-ai folder ke andar se):  bash deploy/install-service.sh
set -e

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${PORT:-8010}"
SERVICE=/etc/systemd/system/listing-ai.service

if [ ! -x "$APP_DIR/venv/bin/uvicorn" ]; then
  echo "venv nahi mila. Pehle yeh chalao: python3 -m venv venv && venv/bin/pip install -r requirements.txt"
  exit 1
fi

if ss -ltn 2>/dev/null | grep -q ":$PORT " && ! systemctl is-active --quiet listing-ai; then
  echo "Port $PORT pe pehle se kuch chal raha hai. Jis terminal mein uvicorn chal raha hai, wahan Ctrl+C dabao, phir yeh dobara chalao."
  exit 1
fi

cat > "$SERVICE" <<UNIT
[Unit]
Description=Listing AI
After=network-online.target
Wants=network-online.target

[Service]
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port $PORT
Environment=PYTHONUNBUFFERED=1
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now listing-ai
sleep 2

if systemctl is-active --quiet listing-ai; then
  echo ""
  echo "✅ Listing AI ab 24x7 chal raha hai: http://$(hostname -I | awk '{print $1}'):$PORT"
  echo "   Logs dekhne ke liye:   journalctl -u listing-ai -f   (bahar aane ke liye Ctrl+C)"
  echo "   Naya code laane ke liye: bash deploy/update.sh"
else
  echo "❌ Service start nahi hui. Neeche ka error screenshot karke bhejo:"
  journalctl -u listing-ai -n 30 --no-pager
  exit 1
fi
