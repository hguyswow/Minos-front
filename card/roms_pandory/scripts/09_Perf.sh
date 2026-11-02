#!/bin/bash
# TEST: speed measurement. Plays mw3rev_ko.md with RetroArch (GPU driver) for 40 seconds and logs CPU speed, load, temperature every 4 s.
# Result: perf.log on the card (last lines show frames per second).
CARD=$(cd "$(dirname "$0")/../.." && pwd)
RA="$CARD/pandory/ra"
export HOME="$RA" XDG_CONFIG_HOME="$RA" XDG_RUNTIME_DIR=/data
mkdir -p "$RA/saves" "$RA/states" "$RA/system"
ROM="$CARD/roms_pandory/genesis/mw3rev_ko.md"
[ -f "$ROM" ] || ROM=$(ls "$CARD"/roms_pandory/genesis/*.[mM][dD] 2>/dev/null | head -1)
printf '%s\n' 'video_driver = "gl"' 'video_context_driver = "kms"' 'fps_show = "true"' 'aspect_ratio_index = "24"' > /tmp/ra_perf.cfg
L="$CARD/perf.log"; RL="$CARD/perf_ra.log"
echo "rom=$ROM" > "$L"
S=$(date +%s)
/lib/ld-linux-armhf.so.3 --library-path /usr/lib:/lib "$RA/retroarch" --config "$RA/ra.cfg" --appendconfig /tmp/ra_perf.cfg -L "$CARD/pandory/cores/picodrive_libretro.so" "$ROM" --verbose > "$RL" 2>&1 &
P=$!
sleep 6
C=/sys/devices/system/cpu/cpu0/cpufreq
for i in 1 2 3 4 5 6 7 8 9; do
  echo "--- t=$((6 + (i-1)*4))s" >> "$L"
  echo "cpu0 freq=$(cat $C/scaling_cur_freq 2>&1) governor=$(cat $C/scaling_governor 2>&1) min=$(cat $C/scaling_min_freq 2>&1) max=$(cat $C/scaling_max_freq 2>&1) avail=$(cat $C/scaling_available_frequencies 2>&1)" >> "$L"
  echo "online cpus: $(cat /sys/devices/system/cpu/online 2>&1)   loadavg: $(cat /proc/loadavg 2>&1)" >> "$L"
  echo "temp: $(cat /sys/class/thermal/thermal_zone0/temp 2>&1)" >> "$L"
  for z in /sys/class/devfreq/*; do [ -d "$z" ] && echo "devfreq $(basename $z): cur=$(cat $z/cur_freq 2>&1) gov=$(cat $z/governor 2>&1)" >> "$L"; done
  echo "ra ticks (user sys): $(awk '{print $14, $15}' /proc/$P/stat 2>&1)" >> "$L"
  sleep 4
done
top -b -n 1 2>&1 | head -14 >> "$L"
kill $P 2>/dev/null
sleep 3
E=$(date +%s)
FR=$(grep -o 'Frames pushed: [0-9]*' "$RL" | grep -o '[0-9]*' | head -1)
echo "=== seconds=$((E-S))  frames_pushed=$FR  approx_fps=$(awk -v f="$FR" -v s=$((E-S-3)) 'BEGIN{ if (s>0) printf "%.1f", f/s }')  (60 is full speed)" >> "$L"
grep -E "Threaded video stats" "$RL" >> "$L"
echo done >> "$L"
sync
