#!/bin/bash
# Collection "arcade": installs the menu setting that shows only these games, then returns to the menu (the menu restarts and reads it).
CARD=$(cd "$(dirname "$0")/../.." && pwd)
if [ ! -f "$CARD/pandory/collections/original.cfg" ]; then cat /userdata/gamemenu.cfg > "$CARD/pandory/collections/original.cfg"; fi
cat "$CARD/pandory/collections/arcade.cfg" > /userdata/gamemenu.cfg
sync
