#!/bin/bash
# TEST: real RetroArch with the GPU video driver (GLES2 via KMS) instead of the slow software "drm" one. Plays mw3rev_ko.md. Result: ra_gl.log on the card. FPS is shown on screen.
CARD=$(cd "$(dirname "$0")/../.." && pwd)
RA="$CARD/pandory/ra"
export HOME="$RA" XDG_CONFIG_HOME="$RA" XDG_RUNTIME_DIR=/data
mkdir -p "$RA/saves" "$RA/states" "$RA/system" "$RA/screenshots"
ROM="$CARD/roms_pandory/genesis/mw3rev_ko.md"
[ -f "$ROM" ] || ROM=$(ls "$CARD"/roms_pandory/genesis/*.[mM][dD] 2>/dev/null | head -1)
cat > /tmp/ra_gl.cfg <<'EOC'
video_driver = "gl"
video_context_driver = "kms"
video_shader_enable = "false"
fps_show = "true"
aspect_ratio_index = "24"
EOC
cat "$RA/layouts/genesis.cfg" >> /tmp/ra_gl.cfg
echo "rom=$ROM" > "$CARD/ra_gl.log"
/lib/ld-linux-armhf.so.3 --library-path /usr/lib:/lib "$RA/retroarch" --config "$RA/ra.cfg" --appendconfig /tmp/ra_gl.cfg -L "$CARD/pandory/cores/picodrive_libretro.so" "$ROM" --verbose >> "$CARD/ra_gl.log" 2>&1
echo "exit code $?" >> "$CARD/ra_gl.log"
sync
