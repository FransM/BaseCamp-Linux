#!/usr/bin/env bash
# Build a source-overlay tarball (no PyInstaller, takes seconds).
#
# Output: source-<APP_VERSION>.tar.gz at the repo root, containing the
# user-side Python tree (gui.py + shared/ + devices/ + plugins/ + lang/
# + default_*.json) plus a VERSION file. Upload that tarball to the
# matching GitHub release; the in-app updater will pick it up and extract
# it to ~/.local/share/basecamp-linux/source-overlay/ on the user's box.
#
# Native code (libusb, hidapi, customtkinter) is NOT in here — those
# still need a full AppImage rebuild when they change.

set -euo pipefail

cd "$(dirname "$0")"

VER=$(grep -oP 'APP_VERSION = "\K[^"]+' gui.py | head -1)
if [[ -z "$VER" ]]; then
    echo "Could not read APP_VERSION from gui.py" >&2
    exit 1
fi

STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT

ROOT="$STAGE/source-overlay"
mkdir -p "$ROOT"

# Files & directories that belong in the overlay. Anything native, build
# artefact, or repo-meta is excluded by construction (we cherry-pick).
cp gui.py                       "$ROOT/"
cp tray_helper.py               "$ROOT/" 2>/dev/null || true
cp mountain-time-sync.py        "$ROOT/" 2>/dev/null || true
cp default_presets.json         "$ROOT/" 2>/dev/null || true
cp default_presets_60.json      "$ROOT/" 2>/dev/null || true
cp default_makalu_presets.json  "$ROOT/" 2>/dev/null || true
cp -r lang                      "$ROOT/"
cp -r shared                    "$ROOT/"
cp -r devices                   "$ROOT/"
cp -r plugins                   "$ROOT/"
# resources/ (icons, splash images) is intentionally NOT in the overlay —
# it's static and would just bloat the tarball. New icons require an
# AppImage rebuild.

# Drop __pycache__ and .pyc from copied trees — they'd just bloat the tarball
find "$ROOT" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find "$ROOT" -type f -name '*.pyc' -delete 2>/dev/null || true

echo "$VER" > "$ROOT/VERSION"

OUT="source-${VER}.tar.gz"
SHA="${OUT}.sha256"
rm -f "$OUT" "$SHA"
tar -C "$STAGE" -czf "$OUT" source-overlay
# Sidecar checksum — the updater REQUIRES this file on the GitHub release
# and will refuse the source update if it's missing or doesn't match.
sha256sum "$OUT" | cut -d' ' -f1 > "$SHA"

SIZE=$(du -h "$OUT" | cut -f1)
echo "Built $OUT ($SIZE)"
echo "Checksum: $(cat "$SHA")"
echo "Upload BOTH '$OUT' and '$SHA' as release assets."
