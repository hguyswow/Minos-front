#!/bin/bash
# TEST: sound with 16-bit output (the stock firmware format). Plays mw3rev_ko.md three times (about 25 s each).
# LISTEN to each run. Result: sound16.log on the card (shows the real sound-chip format, and frames per second; 60 = full speed).
CARD=$(cd "$(dirname "$0")/../.." && pwd)
RA="$CARD/pandory/ra"
export HOME="$RA" XDG_CONFIG_HOME="$RA" XDG_RUNTIME_DIR=/data
mkdir -p "$RA/saves" "$RA/states" "$RA/system"
ROM="$CARD/roms_pandory/genesis/mw3rev_ko.md"
[ -f "$ROM" ] || ROM=$(ls "$CARD"/roms_pandory/genesis/*.[mM][dD] 2>/dev/null | head -1)
L="$CARD/sound16.log"; RL="$CARD/sound16_ra.log"
{ echo "alsa user config: $(ls -la $HOME/.asoundrc 2>&1)"; echo "alsa_device.cfg: $(cat /tmp/alsa_device.cfg 2>&1)"; } > "$L"
snap() { for s in /proc/asound/card*/pcm*p/sub0/status; do [ -f "$s" ] && grep -q RUNNING "$s" && echo "$(echo $s | sed 's#/proc/asound/##; s#/sub0/status##'):$(grep hw_ptr "$s" | awk '{print $3}')"; done; }
run() {
  N="$1"; DEV="$2"; RATE="$3"
  printf '%s\n' 'video_driver = "gl"' 'video_context_driver = "kms"' 'aspect_ratio_index = "24"' 'fps_show = "true"' "audio_device = \"$DEV\"" "audio_out_rate = \"$RATE\"" > /tmp/ra_snd.cfg
  /lib/ld-linux-armhf.so.3 --library-path /usr/lib:/lib "$RA/retroarch" --config "$RA/ra.cfg" --appendconfig /tmp/ra_snd.cfg -L "$CARD/pandory/cores/picodrive_libretro.so" "$ROM" --verbose > "$RL" 2>&1 &
  P=$!
  sleep 10
  S1=$(snap); sleep 2; S2=$(snap)
  HP=$(cat /proc/asound/card*/pcm*p/sub0/hw_params 2>/dev/null | tr '\n' ' ')
  sleep 8
  kill $P 2>/dev/null
  sleep 4
  FR=$(grep -o 'Frames pushed: [0-9]*' "$RL" | grep -o '[0-9]*' | head -1)
  ER=$(grep -E "ERROR|rror" "$RL" | head -3 | tr '\n' ' ')
  echo "--- run $N: device='$DEV' rate=$RATE | frames=$FR approx_fps=$(awk -v f="${FR:-0}" 'BEGIN{printf "%.1f", f/20}')" >> "$L"
  echo "    hw_ptr t=10s: [$S1]  t=12s: [$S2]" >> "$L"
  echo "    hw_params: $HP" >> "$L"
  echo "    errors: $ER" >> "$L"
}
run 1 ra16    44100
run 2 ra16hw  44100
run 3 ra16    48000
echo "done" >> "$L"
sync
