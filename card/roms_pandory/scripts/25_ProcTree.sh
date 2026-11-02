#!/bin/bash
# TEST: records which user processes run, their command lines, the parent chain of this script and /tmp, to learn how the menu is started
# (needed to start MinosFront at boot). Result: proc_tree.log on the card.
CARD=$(cd "$(dirname "$0")/../.." && pwd)
L="$CARD/proc_tree.log"
{
echo "== date"; date
echo "== processes (no kernel threads)"
for p in /proc/[0-9]*; do n=${p#/proc/}; c=$(tr '\0' ' ' < $p/cmdline 2>/dev/null); [ -n "$c" ] && echo "$n ppid=$(awk '/^PPid/{print $2}' $p/status 2>/dev/null) exe=$(readlink $p/exe 2>/dev/null) :: $c"; done
echo "== this script: pid $$"
q=$$; i=0; while [ $i -lt 8 ] && [ "$q" != "0" ] && [ -n "$q" ]; do echo "chain $q: $(tr '\0' ' ' < /proc/$q/cmdline 2>/dev/null)"; q=$(awk '/^PPid/{print $2}' /proc/$q/status 2>/dev/null); i=$((i+1)); done
echo "== /tmp"; ls -la /tmp 2>&1 | head -60
echo "== /userdata"; ls -la /userdata 2>&1 | head -30
echo "== env"; env | sort | head -40
} > "$L" 2>&1
sync
echo
