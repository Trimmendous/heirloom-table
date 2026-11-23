#!/usr/bin/env bash
# Every check that must pass before a commit. Exit code 0 = all good.
set -euo pipefail
cd "$(dirname "$0")/.."
step() { printf '\n== %s\n' "$1"; }

step "art: generate anything missing (tools/make_art.py)"
if command -v swiftc >/dev/null 2>&1; then
  python3 tools/make_art.py
else
  echo "swiftc not available: skipping art generation (existing art is still checked below)"
fi

step "recipes: validate schema + glyphs, regenerate roku/data, web/recipes.js, RECIPES.md, web/assets"
python3 tools/build_data.py

step "assets + manifest"
python3 tools/check_assets.py

step "BrightScript lint"
python3 tools/brs_lint.py

step "web clone: syntax"
for f in web/recipes.js web/js/*.js tools/web_test.js; do node --check "$f"; done
echo "node --check OK"

step "web clone: headless behaviour test"
node tools/web_test.js

step "package"
scripts/package.sh

printf '\nALL CHECKS PASSED\n'
