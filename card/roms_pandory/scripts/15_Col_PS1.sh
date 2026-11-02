#!/bin/bash
# Collection "ps1": installs the menu setting that shows only these games, then returns to the menu (the menu restarts and reads it).
CARD=$(cd "$(dirname "$0")/../.." && pwd)
if [ ! -f "$CARD/pandory/collections/original.cfg" ]; then cat /userdata/gamemenu.cfg > "$CARD/pandory/collections/original.cfg"; fi
cat "$CARD/pandory/collections/ps1.cfg" > /userdata/gamemenu.cfg
sync
