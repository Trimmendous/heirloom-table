#!/usr/bin/env bash
# Build the sideloadable Roku package: dist/heirloom-table-roku.zip (manifest at the zip root).
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p dist
OUT="dist/heirloom-table-roku.zip"
rm -f "$OUT"
(cd roku && zip -q -r -X "../$OUT" manifest source components data fonts images \
    -x 'images/web/*' -x '*.DS_Store' -x '*/.*')
python3 tools/check_assets.py --package "$OUT"
