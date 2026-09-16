#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "Python 3 not found. Install Python 3.10+ and try again." >&2
  exit 1
fi

healthy=0
if command -v curl >/dev/null 2>&1; then
  if curl -fsS --max-time 1 "http://127.0.0.1:8768/health" >/dev/null 2>&1; then
    healthy=1
  fi
fi

if [[ "$healthy" -eq 0 ]]; then
  "$PY" python/expense_server.py &
  sleep 2
fi

URL="http://127.0.0.1:8768/"
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL" >/dev/null 2>&1 || true
elif command -v open >/dev/null 2>&1; then
  open "$URL" || true
else
  echo "Open $URL in your browser."
fi
