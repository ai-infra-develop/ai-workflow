#!/bin/bash
set -euo pipefail

if [ -z "$REPO_DIR" ]; then
  echo "Error: REPO_DIR not set" >&2
  exit 1
fi
echo "$REPO_DIR" > "$RUN_DIR/repo_dir.txt"
exit 0