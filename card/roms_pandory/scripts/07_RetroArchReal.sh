#!/bin/bash
# TEST: real RetroArch 1.22.2 (our own build) running the first Mega Drive game. Exit with Q or the RetroArch quit key.
CARD=$(cd "$(dirname "$0")/../.." && pwd)
RA="$CARD/pandory/ra"
export HOME="$RA" XDG_CONFIG_HOME="$RA" XDG_RUNTIME_DIR=/data
mkdir -p "$RA/saves" "$RA/states" "$RA/system"
ROM=$(ls "$CARD"/roms_pandory/genesis/*.[zZ][iI][pP] "$CARD"/roms_pandory/genesis/*.[mM][dD] "$CARD"/roms_pandory/genesis/*.[bB][iI][nN] 2>/dev/null | head -1)
echo "rom=$ROM" > "$CARD/ra_run.log"
/lib/ld-linux-armhf.so.3 --library-path /usr/lib:/lib "$RA/retroarch" --config "$RA/ra.cfg" -L "$CARD/pandory/cores/picodrive_libretro.so" "$ROM" --verbose >> "$CARD/ra_run.log" 2>&1
echo "exit code $?" >> "$CARD/ra_run.log"
sync
