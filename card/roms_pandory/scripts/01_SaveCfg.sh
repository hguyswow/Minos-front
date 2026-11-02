#!/bin/bash
# READ-ONLY: copies the menu's saved settings (/userdata/*.cfg) to the card folder cfgdump.
CARD=$(cd "$(dirname "$0")/../.." && pwd)
D="$CARD/cfgdump"; mkdir -p "$D"
for f in /userdata/*.cfg /userdata/cabinet_type /userdata/nostm8_*; do
  [ -f "$f" ] && cat "$f" > "$D/$(basename $f).$(date +%s)"
done
ls -la /userdata > "$D/ls_userdata.txt" 2>&1
sync
