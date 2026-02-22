#!/usr/bin/env bash
# Generate transparent logo and all sizes from logo-white-bg.png
# Requires: ImageMagick (magick)
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$DIR/logo-white-bg.png"
TRANSPARENT="$DIR/logo-transparent.png"

if [ ! -f "$SRC" ]; then
    echo "Error: $SRC not found" >&2
    exit 1
fi

# Get image dimensions
W=$(magick identify -format '%w' "$SRC")
H=$(magick identify -format '%h' "$SRC")
LAST_X=$((W - 1))
LAST_Y=$((H - 1))

echo "Source: ${W}x${H}"

# Remove white background:
#   1. Flood-fill from all 4 corners (removes connected outer white)
#   2. Flood-fill the "i" box in the crab body (interior white)
#   3. Erode alpha by 1px to remove anti-alias fringe
MID_X=$((W / 2))
BOX_Y=$(( (H * 4) / 7 ))   # ~57% down, inside the "i" stem
DOT_Y=$(( (H * 51) / 100 )) # ~51% down, inside the "i" dot

echo "Removing background (box at ${MID_X},${BOX_Y}, dot at ${MID_X},${DOT_Y})..."
magick "$SRC" \
    -fill none -fuzz 20% \
    -draw "color 0,0 floodfill" \
    -draw "color ${LAST_X},0 floodfill" \
    -draw "color 0,${LAST_Y} floodfill" \
    -draw "color ${LAST_X},${LAST_Y} floodfill" \
    -draw "color ${MID_X},${BOX_Y} floodfill" \
    -draw "color ${MID_X},${DOT_Y} floodfill" \
    -channel alpha -morphology Erode Disk:1 +channel \
    "$TRANSPARENT"

echo "Wrote $TRANSPARENT"

# Generate all sizes needed by claweb
CLAWEB_RES="$DIR/../../claweb/res"
CLAWEB_STATIC="$DIR/../../claweb/site/static"

SIZES=(32 112 128 180 256 512 1024)

echo "Generating sizes..."
for S in "${SIZES[@]}"; do
    OUT="$CLAWEB_RES/logo-${S}.png"
    magick "$TRANSPARENT" -resize "${S}x${S}" "$OUT"
    echo "  ${S}x${S} -> $OUT"
done

# logo-square.png: full-res transparent logo
cp "$TRANSPARENT" "$CLAWEB_RES/logo-square.png"
echo "  logo-square.png (full res)"

# logo-envelope.png: used in site header and static
cp "$TRANSPARENT" "$CLAWEB_RES/logo-envelope.png"
echo "  logo-envelope.png"

# logo-envelope-transparent.png: same as transparent
cp "$TRANSPARENT" "$CLAWEB_RES/logo-envelope-transparent.png"
echo "  logo-envelope-transparent.png"

# Static copies for the deployed site
cp "$CLAWEB_RES/logo-envelope.png" "$CLAWEB_STATIC/logo-envelope.png"
cp "$CLAWEB_RES/logo-32.png" "$CLAWEB_STATIC/favicon.png"
echo "  static/logo-envelope.png, static/favicon.png"

echo "Done."
