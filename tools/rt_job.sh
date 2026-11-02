#!/bin/bash
# usage: job.sh SYSTEM FILE CORE   -> appends "file<TAB>system<TAB>working core or NONE<TAB>reason" to /opt/rt/results.tsv
sys="$1"; f="$2"; core="$3"
Q=/opt/qemu/usr/bin/qemu-arm-static; RA=/mnt/d/Backup/tools/ra_build/out/retroarch
W=$(mktemp -d /tmp/rtw.XXXXXX); mkdir -p $W/s $W/st $W/sy $W/c
cat > $W/cfg <<EOC
video_driver = "null"
audio_driver = "null"
input_driver = "null"
input_joypad_driver = "null"
menu_driver = "null"
audio_enable = "false"
audio_sync = "false"
video_vsync = "false"
video_threaded = "false"
config_save_on_exit = "false"
savefile_directory = "$W/s"
savestate_directory = "$W/st"
system_directory = "$W/sy"
cache_directory = "$W/c"
log_verbosity = "true"
EOC
case "$sys" in
  arcade) cores="$core fbalpha2012 mame2003" ;;
  snes)   cores="$core snes9x2002" ;;
  *)      cores="$core" ;;
esac
tried=""; reason="?"
for c in $cores; do
  case " $tried " in *" $c "*) continue;; esac
  tried="$tried $c"
  timeout 60 $Q -L /opt/devroot -E HOME=$W $RA --config $W/cfg -L /opt/devroot/usr/lib/libretro/${c}_libretro.so "/mnt/f/roms/$f" --max-frames=20 --verbose > $W/o.log 2>&1 &
  PID=$!
  # stop as soon as the game has loaded (some cores never exit on their own), or when the process ends, or after 60 s
  for t in $(seq 1 120); do
    kill -0 $PID 2>/dev/null || break
    grep -aq 'Core\] Geometry' $W/o.log && { sleep 1; break; }
    sleep 0.5
  done
  kill $PID 2>/dev/null; pkill -P $PID 2>/dev/null; wait $PID 2>/dev/null
  rc=$?
  if grep -aq 'Core\] Geometry' $W/o.log && ! grep -aq -E 'Failed to load content|is required|required files are missing' $W/o.log; then
    printf '%s\t%s\t%s\tok\n' "$f" "$sys" "$c" >> /opt/rt/results.tsv; rm -rf $W; exit 0
  fi
  reason=$(grep -a -m1 -E 'required files are missing|is required|Failed to load content|Failed to initialize|error' $W/o.log | cut -c1-90 | tr '\t' ' ')
  [ -z "$reason" ] && reason="exit=$rc"
done
printf '%s\t%s\tNONE\t%s (tried:%s)\n' "$f" "$sys" "$reason" "$tried" >> /opt/rt/results.tsv
rm -rf $W
