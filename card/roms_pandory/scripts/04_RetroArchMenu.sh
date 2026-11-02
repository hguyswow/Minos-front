#!/bin/bash
# TEST: starts the stock RetroArch with its own menu for 2 minutes (then it is closed automatically).
CARD=$(cd "$(dirname "$0")/../.." && pwd)
export XDG_CONFIG_HOME=/data
export XDG_RUNTIME_DIR=/data
CFG=/tmp/ra_menu.cfg
sed -e '/^menu_driver/d' -e '/^input_joypad_driver/d' -e '/^menu_show_start_screen/d' -e '/^video_fullscreen/d' -e '/^rgui_browser_directory/d' -e '/^libretro_directory/d' /usr/retroarch/retroarch.cfg > $CFG
cat >> $CFG <<'EOC'
menu_driver = "rgui"
input_joypad_driver = "udev"
menu_show_start_screen = "false"
video_fullscreen = "true"
libretro_directory = "/usr/lib/libretro"
rgui_browser_directory = "/mnt/sdcard/roms_pandory"
EOC
echo "start $(date)" > "$CARD/ra_menu.log"
/usr/bin/retroarch --menu --fullscreen -c $CFG >> "$CARD/ra_menu.log" 2>&1 &
P=$!
sleep 120
kill $P 2>/dev/null
echo "end $(date)" >> "$CARD/ra_menu.log"
sync