#!/bin/bash
# TEST: RetroArch menu in Korean? Opens the menu three times (25 s each), with three different menu styles and the Korean font.
# Run 1 = materialui, run 2 = xmb, run 3 = ozone.  LOOK at the screen: is the text Korean and readable?  Result: menu_ko.log on the card.
CARD=$(cd "$(dirname "$0")/../.." && pwd)
RA="$CARD/pandory/ra"
export HOME="$RA" XDG_CONFIG_HOME="$RA" XDG_RUNTIME_DIR=/data
mkdir -p "$RA/saves" "$RA/states" "$RA/system" "$RA/assets"
FONT="$CARD/pandory/front/NanumGothic.ttf"
L="$CARD/menu_ko.log"; : > "$L"
run() {
  D="$1"
  printf '%s\n' 'video_driver = "gl"' 'video_context_driver = "kms"' "menu_driver = \"$D\"" 'user_language = "10"' \
    'video_font_enable = "true"' "video_font_path = \"$FONT\"" 'video_font_size = "24"' \
    "assets_directory = \"$RA/assets\"" 'menu_show_start_screen = "false"' 'menu_show_online_updater = "false"' 'menu_show_core_updater = "false"' \
    "libretro_directory = \"$CARD/pandory/cores\"" "rgui_browser_directory = \"$CARD/roms_pandory\"" > /tmp/ra_menu_ko.cfg
  echo "=== run: menu_driver=$D  $(date)" >> "$L"
  /lib/ld-linux-armhf.so.3 --library-path /usr/lib:/lib "$RA/retroarch" --menu --config "$RA/ra.cfg" --appendconfig /tmp/ra_menu_ko.cfg --verbose > "$CARD/menu_ko_ra.log" 2>&1 &
  P=$!
  sleep 25
  kill $P 2>/dev/null
  sleep 3
  grep -E "\[Menu\]|menu driver|Menu driver|font|Font|FONT|assets|Assets|ERROR|Failed|language|Language|stb|rgui|xmb|ozone|materialui" "$CARD/menu_ko_ra.log" | head -14 >> "$L"
}
run materialui
run xmb
run ozone
echo "done" >> "$L"
sync
