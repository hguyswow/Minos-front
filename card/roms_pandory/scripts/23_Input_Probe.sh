#!/bin/bash
# TEST: which input devices exist and what raw signals every button sends. For 25 seconds press ALL buttons (also the extra four) one after another.
# Result: input_probe.log on the card.
CARD=$(cd "$(dirname "$0")/../.." && pwd)
L="$CARD/input_probe.log"
{ echo "== devices"; cat /proc/bus/input/devices; echo "== /dev/input"; ls -l /dev/input; echo "== uinput"; ls -l /dev/uinput /dev/misc/uinput 2>&1; } > "$L" 2>&1
PIDS=""
for d in /dev/input/event*; do cat "$d" > /tmp/probe_$(basename "$d").bin 2>/dev/null & PIDS="$PIDS $!"; done
sleep 25
kill $PIDS 2>/dev/null
for f in /tmp/probe_*.bin; do
  echo "== raw $f  (type code value;  type 1 = key, 3 = analog axis)" >> "$L"
  od -An -tu2 -w16 "$f" | awk '$5==1 || $5==3 {print "type="$5" code="$6" value="$7+65536*$8}' | sort | uniq -c >> "$L"
done
sync
echo
