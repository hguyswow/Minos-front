#!/bin/bash
# TEST: sound output. Plays mw3rev_ko.md 7 times (about 25 s each, 3 minutes total) through different sound outputs / rates.
# LISTEN to every run and remember which numbers sound clean. Result: sound.log on the card (also records what the sound hardware really does).
CARD=$(cd "$(dirname "$0")/../.." && pwd)
RA="$CARD/pandory/ra"
export HOME="$RA" XDG_CONFIG_HOME="$RA" XDG_RUNTIME_DIR=/data
mkdir -p "$RA/saves" "$RA/states" "$RA/system"
ROM="$CARD/roms_pandory/genesis/mw3rev_ko.md"
[ -f "$ROM" ] || ROM=$(ls "$CARD"/roms_pandory/genesis/*.[mM][dD] 2>/dev/null | head -1)
L="$CARD/sound.log"; RL="$CARD/sound_ra.log"
{
  echo "=== /proc/asound/cards"; cat /proc/asound/cards 2>&1
  echo "=== /proc/asound/pcm"; cat /proc/asound/pcm 2>&1
  echo "=== /tmp/alsa_device.cfg: $(cat /tmp/alsa_device.cfg 2>&1)"
  echo "=== aplay -l"; aplay -l 2>&1 | head -20
  echo "=== amixer"; amixer 2>&1 | head -70
  echo "=== processes holding sound devices"; ls -l /proc/[0-9]*/fd 2>/dev/null | grep -E "snd/pcm" | head
} > "$L" 2>&1
snap() { for s in /proc/asound/card*/pcm*p/sub0/status; do [ -f "$s" ] && grep -q RUNNING "$s" && echo "$(echo $s | sed 's#/proc/asound/##; s#/sub0/status##'):$(grep hw_ptr "$s" | awk '{print $2}')"; done; }
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
  AL=$(grep -E "\[ALSA\]" "$RL" | grep -E "Using|Period|Buffer|rate|Rate|ERROR|error|fail" | head -4 | tr '\n' ' ')
  echo "--- run $N: device='$DEV' rate=$RATE | frames=$FR approx_fps=$(awk -v f="${FR:-0}" 'BEGIN{printf "%.1f", f/20}')" >> "$L"
  echo "    hw_ptr at t=10s: [$S1]  at t=12s: [$S2]   (sound chip frames per 2 s; full speed = about 2x the rate)" >> "$L"
  echo "    hw_params: $HP" >> "$L"
  echo "    ra: $AL" >> "$L"
}
run 1 ""          44100
run 2 internal    44100
run 3 hdmi        44100
run 4 ""          48000
run 5 hdmi        48000
run 6 plughw:0,0  44100
run 7 plughw:0,1  44100
echo "done" >> "$L"
sync
