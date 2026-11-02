#!/bin/bash
# TEST: RetroArch's own menu with the GPU video driver. Closes by itself after 3 minutes. Result: ra_menu_gl.log on the card.
CARD=$(cd "$(dirname "$0")/../.." && pwd)
RA="$CARD/pandory/ra"
export HOME="$RA" XDG_CONFIG_HOME="$RA" XDG_RUNTIME_DIR=/data
mkdir -p "$RA/saves" "$RA/states" "$RA/system" "$RA/screenshots"
cat > /tmp/ra_menu_gl.cfg <<'EOC'
video_driver = "gl"
video_context_driver = "kms"
menu_driver = "rgui"
fps_show = "true"
libretro_directory = "/mnt/sdcard/pandory/cores"
rgui_browser_directory = "/mnt/sdcard/roms_pandory"
menu_show_start_screen = "false"
EOC
echo "start $(date)" > "$CARD/ra_menu_gl.log"
/lib/ld-linux-armhf.so.3 --library-path /usr/lib:/lib "$RA/retroarch" --menu --config "$RA/ra.cfg" --appendconfig /tmp/ra_menu_gl.cfg --verbose >> "$CARD/ra_menu_gl.log" 2>&1 &
P=$!
sleep 180
kill $P 2>/dev/null
echo "end $(date)" >> "$CARD/ra_menu_gl.log"
sync
