#!/usr/bin/env bash
set -euo pipefail

# Publish the pre-built RAG bundle as a GitHub Release. By default uses
# the existing bundle at data/rag-bundle/. Pass --rebuild to rebuild
# from scratch (takes ~15 min on Apple Silicon, longer on CPU).
#
# Prerequisites: gh CLI installed and authenticated
#   brew install gh && gh auth login
#
# Usage:
#   ./scripts/publish-bundle.sh <owner/repo>
#   ./scripts/publish-bundle.sh --rebuild <owner/repo>

REBUILD=false
if [ "${1:-}" = "--rebuild" ]; then
  REBUILD=true
  shift
fi

if [ $# -lt 1 ]; then
  echo "Usage: $0 [--rebuild] <owner/repo>"
  echo "  e.g. $0 myusername/servicenow-atlas"
  echo "  e.g. $0 --rebuild myusername/servicenow-atlas"
  exit 1
fi

REPO="$1"
TAG="australia-$(date -u +%Y%m%d)"
BUNDLE_DIR="./data/rag-bundle"

if [ "$REBUILD" = true ]; then
  echo "==> Rebuilding bundle..."
  uv run atlas-build --output "$BUNDLE_DIR"
elif [ ! -f "$BUNDLE_DIR/manifest.json" ]; then
  echo "==> No existing bundle at $BUNDLE_DIR — building..."
  uv run atlas-build --output "$BUNDLE_DIR"
else
  echo "==> Using existing bundle at $BUNDLE_DIR"
  echo "    (pass --rebuild to build from scratch)"
fi

echo "==> Compressing bundle..."
TARBALL="$(mktemp).tar.gz"
tar -czf "$TARBALL" -C "$BUNDLE_DIR" .
SIZE=$(ls -lh "$TARBALL" | awk '{print $5}')
echo "  Bundle size: $SIZE"

echo "==> Creating GitHub release $TAG ..."
gh release create "$TAG" \
  --repo "$REPO" \
  --title "ServiceNow Atlas bundle - $TAG" \
  --notes "Pre-built RAG bundle for the ServiceNow Australia docs release.

Source SHA: see \`manifest.json\` inside the bundle.

Install with:
\`\`\`
uv run atlas-download --repo $REPO --tag $TAG --output ~/data/rag-bundle
\`\`\`" \
  "$TARBALL"

rm -f "$TARBALL"
echo "==> Done: https://github.com/$REPO/releases/tag/$TAG"
