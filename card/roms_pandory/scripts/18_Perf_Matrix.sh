#!/bin/bash
# TEST: what limits the speed?  Plays mw3rev_ko.md five times (about 24 s each, 2 minutes total) with different settings and counts frames.
# Result: perf2.log on the card. Full speed = about 60 frames per second.
CARD=$(cd "$(dirname "$0")/../.." && pwd)
RA="$CARD/pandory/ra"
export HOME="$RA" XDG_CONFIG_HOME="$RA" XDG_RUNTIME_DIR=/data
mkdir -p "$RA/saves" "$RA/states" "$RA/system"
ROM="$CARD/roms_pandory/genesis/mw3rev_ko.md"
[ -f "$ROM" ] || ROM=$(ls "$CARD"/roms_pandory/genesis/*.[mM][dD] 2>/dev/null | head -1)
L="$CARD/perf2.log"; RL="$CARD/perf2_ra.log"
echo "rom=$ROM" > "$L"
C=/sys/devices/system/cpu/cpu0/cpufreq
run() {
  NAME="$1"; shift
  printf '%s\n' 'aspect_ratio_index = "24"' 'fps_show = "true"' "$@" > /tmp/ra_p2.cfg
  /lib/ld-linux-armhf.so.3 --library-path /usr/lib:/lib "$RA/retroarch" --config "$RA/ra.cfg" --appendconfig /tmp/ra_p2.cfg -L "$CARD/pandory/cores/picodrive_libretro.so" "$ROM" --verbose > "$RL" 2>&1 &
  P=$!
  sleep 12
  FQ=$(cat $C/scaling_cur_freq 2>&1)
  TK1=$(awk '{print $14+$15}' /proc/$P/stat 2>/dev/null)
  sleep 8
  TK2=$(awk '{print $14+$15}' /proc/$P/stat 2>/dev/null)
  kill $P 2>/dev/null
  sleep 4
  FR=$(grep -o 'Frames pushed: [0-9]*' "$RL" | grep -o '[0-9]*' | head -1)
  DR=$(grep -o 'Frames dropped: [0-9]*' "$RL" | grep -o '[0-9]*' | head -1)
  echo "$NAME | frames_total=$FR dropped=$DR | approx_fps=$(awk -v f="${FR:-0}" 'BEGIN{printf "%.1f", f/21}') | cpu_freq_khz=$FQ | ra_cpu_pct_of_one_core=$(awk -v a="${TK1:-0}" -v b="${TK2:-0}" 'BEGIN{printf "%d", (b-a)/8}')" >> "$L"
}
run "A baseline GPU (sound on, vsync on)" 'video_driver = "gl"' 'video_context_driver = "kms"'
run "B GPU, sound OFF"                    'video_driver = "gl"' 'video_context_driver = "kms"' 'audio_enable = "false"'
run "C GPU, sound OFF, vsync OFF"         'video_driver = "gl"' 'video_context_driver = "kms"' 'audio_enable = "false"' 'video_vsync = "false"'
run "D software drm, sound OFF, vsync OFF" 'video_driver = "drm"' 'audio_enable = "false"' 'video_vsync = "false"'
run "E GPU, sound sync OFF"               'video_driver = "gl"' 'video_context_driver = "kms"' 'audio_sync = "false"'
echo "done  (60 fps = full speed; about 21 s of play per run)" >> "$L"
sync
