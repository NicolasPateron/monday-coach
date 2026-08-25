#!/bin/bash
# Regenerates the README screenshots from the demo page.
# Chrome headless, one PNG per section, then converted to JPEG.
set -e
cd "$(dirname "$0")/../.."
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DEMO="$PWD/docs/demo"
OUT="$PWD/docs/images"
mkdir -p "$OUT" "$DEMO/_tmp"

python3 docs/demo/build_demo.py > /dev/null

# One standalone file per section: Chrome's --screenshot captures the viewport,
# so the page must already be exactly the size of the section.
python3 docs/demo/split_sections.py

for f in "$DEMO"/_tmp/*.html; do
  name=$(basename "$f" .html)
  size=$(python3 -c "
import re,sys
s=open('$f',encoding='utf-8').read()
m=re.search(r'<!--size:(\d+)x(\d+)-->',s); print(m.group(1)+','+m.group(2))")
  "$CHROME" --headless --disable-gpu --force-color-profile=srgb \
    --hide-scrollbars --default-background-color=0a0a0bff \
    --window-size="$size" --screenshot="$OUT/$name.png" "file://$f" 2>/dev/null
  sips -s format jpeg -s formatOptions 88 "$OUT/$name.png" --out "$OUT/$name.jpg" > /dev/null
  rm -f "$OUT/$name.png"
  echo "  $name.jpg  $(du -h "$OUT/$name.jpg" | cut -f1)"
done
rm -rf "$DEMO/_tmp"
