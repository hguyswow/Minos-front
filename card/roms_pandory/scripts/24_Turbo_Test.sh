#!/bin/bash
# TEST: autofire (RetroArch "Classic Toggle"). Plays 1941 (arcade shooter). Hold Select/Coin and press a button (A, B, ...): that button fires by itself; do it again to switch it off.
# In this test the other hotkeys need START instead of Coin:  Start+A save, Start+E load, Start+F pause, Start+B reset, Start+Coin quit. Closes itself after 3 minutes.
# Result: ra_turbo.log on the card.
CARD=$(cd "$(dirname "$0")/../.." && pwd)
RA="$CARD/pandory/ra"
export HOME="$RA" XDG_CONFIG_HOME="$RA" XDG_RUNTIME_DIR=/data
mkdir -p "$RA/saves" "$RA/states" "$RA/system" "$RA/screenshots"
cat > /tmp/ra_turbo.cfg <<'EOC'
video_driver = "gl"
video_context_driver = "kms"
config_save_on_exit = "false"
input_turbo_enable = "true"
input_turbo_mode = "1"
input_turbo_period = "6"
input_player1_turbo = "i"
input_enable_hotkey = "num1"
input_exit_emulator = "i"
fps_show = "true"
EOC
echo "start $(date)" > "$CARD/ra_turbo.log"
/lib/ld-linux-armhf.so.3 --library-path /usr/lib:/lib "$RA/retroarch" --config "$RA/ra.cfg" --appendconfig /tmp/ra_turbo.cfg -L /usr/lib/libretro/mame2003_libretro.so "$CARD/roms/1941.zip" --verbose >> "$CARD/ra_turbo.log" 2>&1 &
P=$!
sleep 180
kill $P 2>/dev/null
echo "end $(date)" >> "$CARD/ra_turbo.log"
sync
echo
