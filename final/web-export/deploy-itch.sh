#!/bin/bash
# deploy-itch.sh  —  Upload your InScript game to itch.io
# Prerequisites:
#   1. Install butler: https://itch.io/docs/butler/installing.html
#   2. Run: butler login
#   3. Set ITCH_USER and ITCH_GAME below
set -e
ITCH_USER="${ITCH_USER:-your-username}"
ITCH_GAME="${ITCH_GAME:-your-game-name}"
DIST_DIR="${1:-dist}"

echo "📦 Building web export..."
python -m inscript.targets.web.web_export game.ins --out "$DIST_DIR"

echo "🚀 Uploading to itch.io..."
butler push "$DIST_DIR" "$ITCH_USER/$ITCH_GAME:html5"

echo "✅ Deployed to https://$ITCH_USER.itch.io/$ITCH_GAME"
