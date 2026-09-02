#!/usr/bin/env bash
# Sets up and runs the Flask backend from scratch: venv, deps, migrations, seed data, server.
# Usage: ./setup.sh
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

if [ ! -f .env ]; then
  echo "Missing backend/.env — copy .env.example and fill in real values first." >&2
  exit 1
fi

if [ ! -d .venv ]; then
  echo "==> Creating virtualenv (.venv)"
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> Installing dependencies"
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo "==> Running database migrations"
flask db upgrade

echo "==> Seeding baseline categories"
python seed.py

echo "==> Starting Flask backend on http://localhost:5000"
exec python run.py
