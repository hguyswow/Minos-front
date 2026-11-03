#!/bin/sh
# Runs at every menu (re)start via a patched Pandory command.
#  1. MinosFront at start-up (optional, switch file pandory/front/autostart): holds the new stock menu (SIGSTOP), runs MinosFront on the screen,
#     and when MinosFront ends the stock menu is killed so Pandory starts a fresh one (that start runs this script again -> step 2).
#     Safety: if MinosFront ends within 6 s (crashed / no screen) twice in a row, the feature switches itself off (autostart_failed).
#  2. Waits for the new gamemenu and applies patch.txt to its memory (Korean names of the added games).
# Test settings: CARD, AUTO_WAIT, FRONT_CMD can be set from outside (tools/test_autostart.sh).
CARD=${CARD:-/mnt/sdcard}
LOG="$CARD/auto_patch.log"
FD="$CARD/pandory/front"
mkdir /tmp/auto.lock 2>/dev/null || exit 0
exec >"$LOG" 2>&1
findgm() { for q in $(ls /proc | grep -E "^[0-9]+$"); do case "$(readlink /proc/$q/exe 2>/dev/null)" in */gamemenu) echo $q; return;; esac; done; }
rd32() { # address -> decimal value of the 32-bit little-endian word
  set -- $(dd if=/proc/$P/mem bs=1 skip=$1 count=4 2>/dev/null | od -b | head -1)
  shift
  echo $(( (0$4 << 24) + (0$3 << 16) + (0$2 << 8) + 0$1 ))
}
OLD=$(findgm)
# safe mode: holding the B button while the system starts skips MinosFront (the stock menu comes up)
SAFE=0; ${KEYCHECK_CMD:-/lib/ld-linux-armhf.so.3 --library-path /usr/lib:/lib $CARD/pandory/bin/minosfront --keycheck} && SAFE=1
[ "$SAFE" = 1 ] && echo "B held -> safe mode: MinosFront skipped"
echo "start old=$OLD $(date)"
if [ -f /tmp/front_skip ]; then
  rm -f /tmp/front_skip; echo "skip flag found: normal menu this time"
elif [ -f "$FD/autostart" ] && [ ! -f "$FD/autostart_failed" ] && [ "$SAFE" != 1 ]; then
  i=0; P=""
  while [ $i -lt 60 ]; do
    P=$(findgm)
    if [ -n "$P" ] && [ "$P" != "$OLD" ]; then break; fi
    P=""; i=$((i+1)); sleep 1
  done
  echo "autostart: menu pid=$P after ${i}s"
  if [ -n "$P" ]; then
    kill -STOP $P
    T0=$(date +%s)
    export XDG_RUNTIME_DIR=/data XDG_CONFIG_HOME=/data
    ${FRONT_CMD:-/lib/ld-linux-armhf.so.3 --library-path /usr/lib:/lib $CARD/pandory/bin/minosfront $CARD} > "$CARD/front_run.log" 2>&1
    T1=$(date +%s)
    touch /tmp/front_skip
    if [ $((T1 - T0)) -lt 6 ]; then
      n=$(cat "$FD/autostart_fails" 2>/dev/null); n=$(( ${n:-0} + 1 )); echo $n > "$FD/autostart_fails"
      echo "MinosFront ended after $((T1 - T0)) s (fail $n)"
      [ $n -ge 2 ] && { echo off > "$FD/autostart_failed"; echo "autostart switched off"; }
    else
      rm -f "$FD/autostart_fails"
    fi
    kill -CONT $P 2>/dev/null; kill -9 $P 2>/dev/null
    echo "menu killed, Pandory should start a new one"
    j=0; N=""                                   # if Pandory does not start a new menu within 12 s, start it ourselves
    while [ $j -lt 12 ]; do N=$(findgm); [ -n "$N" ] && [ "$N" != "$P" ] && break; N=""; j=$((j+1)); sleep 1; done
    if [ -z "$N" ]; then echo "no new menu after 12 s -> starting gamemenu"; ${GM_CMD:-gamemenu} >/dev/null 2>&1 & fi
  fi
  rmdir /tmp/auto.lock
  exit 0
fi
i=0; P=""
while [ $i -lt ${AUTO_TRIES:-90} ]; do
  P=$(findgm)
  if [ -n "$P" ] && [ "$P" != "$OLD" ]; then break; fi
  P=""; i=$((i+1)); sleep 1
done
echo "pid=$P after ${i}s"
if [ -n "$P" ]; then
  sleep ${AUTO_WAIT:-8}
  P=$(findgm)
  STOCK=$(rd32 $((0x8e33bc)))        # number of visible stock games (changes when games are hidden)
  echo "stock=$STOCK"
  n=0
  while read -r a b c d; do
    [ -z "$a" ] && continue
    if [ "$a" = "D" ]; then          # D k slotoffset escapes  (record index read live from the list)
      idx=$(rd32 $((0x8cf6d8 + 4 * (STOCK + b))))
      addr=$((0xBB9A3C + 1408 * idx + c))
      printf "$d" | dd of=/proc/$P/mem bs=1 seek=$addr conv=notrunc 2>/dev/null && n=$((n+1))
    else                              # static: address escapes
      printf "$b" | dd of=/proc/$P/mem bs=1 seek=$a conv=notrunc 2>/dev/null && n=$((n+1))
    fi
  done < "$CARD/pandory/patch.txt"
  echo "patched pid=$P lines=$n"
fi
rmdir /tmp/auto.lock
