#!/usr/bin/env bash

# One-shot local setup for backend (FastAPI) and frontend (Next.js).
# Usage:
#   ./setup-local.sh           # installs deps only
#   START_SERVERS=1 ./setup-local.sh  # installs deps, then starts backend+frontend
#
# Requirements: bash, python3, node, npm. Do not use sudo; runs in user space.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/question-app"
VENV_DIR="$ROOT_DIR/.venv"

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

need_cmd python3
need_cmd node
need_cmd npm

echo "==> Ensuring Python venv in $VENV_DIR"
if [[ ! -d "$VENV_DIR" ]]; then
  python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

echo "==> Installing backend dependencies"
pip install --upgrade pip
pip install -r "$BACKEND_DIR/requirements.txt"

echo "==> Installing frontend dependencies"
cd "$FRONTEND_DIR"
npm install

if [[ "${START_SERVERS:-0}" == "1" ]]; then
  echo "==> Starting backend (uvicorn) and frontend (next dev)"
  # Start backend
  cd "$BACKEND_DIR"
  "$VENV_DIR/bin/uvicorn" main:app --host 0.0.0.0 --port 8000 &
  BACK_PID=$!

  # Start frontend
  cd "$FRONTEND_DIR"
  npm run dev -- --hostname 0.0.0.0 --port 3000 &
  FRONT_PID=$!

  echo "Backend PID: $BACK_PID"
  echo "Frontend PID: $FRONT_PID"
  echo "Press Ctrl+C to stop both."
  wait $BACK_PID $FRONT_PID
fi

echo "==> Done."

