#!/bin/bash
# TEST: in-game RetroArch menu with the NORMAL settings. Hold Coin, press C (upper middle) -> menu. Coin+B is now reset. Closes itself after 2 minutes.
CARD=$(cd "$(dirname "$0")/../.." && pwd)
RA="$CARD/pandory/ra"
export HOME="$RA" XDG_CONFIG_HOME="$RA" XDG_RUNTIME_DIR=/data
mkdir -p "$RA/saves" "$RA/states" "$RA/system" "$RA/screenshots"
ROM="$CARD/roms_pandory/genesis/mw3rev_ko.md"
[ -f "$ROM" ] || ROM=$(ls "$CARD"/roms_pandory/genesis/*.[mM][dD] 2>/dev/null | head -1)
cat > /tmp/ra_mig.cfg <<'EOC'
video_driver = "gl"
video_context_driver = "kms"
menu_driver = "rgui"


fps_show = "true"
EOC
echo "start $(date) rom=$ROM" > "$CARD/ra_menu_ingame.log"
/lib/ld-linux-armhf.so.3 --library-path /usr/lib:/lib "$RA/retroarch" --config "$RA/ra.cfg" --appendconfig /tmp/ra_mig.cfg -L "$CARD/pandory/cores/picodrive_libretro.so" "$ROM" --verbose >> "$CARD/ra_menu_ingame.log" 2>&1 &
P=$!
sleep 120
kill $P 2>/dev/null
echo "end $(date)" >> "$CARD/ra_menu_ingame.log"
sync
echo
