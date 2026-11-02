#!/bin/bash
# Turns ON "MinosFront at start-up": every time the menu starts, MinosFront is shown first. (Switch file pandory/front/autostart.)
CARD=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$CARD/pandory/front"
rm -f "$CARD/pandory/front/autostart_failed" "$CARD/pandory/front/autostart_fails"
echo on > "$CARD/pandory/front/autostart"
sync
echo
