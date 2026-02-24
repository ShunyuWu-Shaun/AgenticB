#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
DIST_DIR="${DIST_DIR:-$ROOT_DIR/dist}"

mkdir -p "$DIST_DIR"

"$PYTHON_BIN" -m nuitka \
  --onefile \
  --output-dir="$DIST_DIR" \
  --output-filename="easyshift-maas" \
  scripts/nuitka_cli_entry.py

"$PYTHON_BIN" -m nuitka \
  --onefile \
  --output-dir="$DIST_DIR" \
  --output-filename="easyshift-maas-api" \
  scripts/nuitka_api_entry.py

printf "Nuitka artifacts generated in %s\n" "$DIST_DIR"
