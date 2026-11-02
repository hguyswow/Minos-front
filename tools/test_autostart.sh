#!/bin/bash
# Simulates Pandory's menu loop with a mock "gamemenu" to test reference/auto.sh (autostart, skip flag, self-switch-off).  Run in WSL.
# usage: test_autostart.sh SCENARIO     ok | crash | off
SC=${1:-ok}
M=/tmp/mock; rm -rf $M /tmp/auto.lock /tmp/front_skip; mkdir -p $M/card/pandory/front; cp /mnt/c/dev/pandora_editor/reference/auto.sh $M/auto.sh; cp /bin/sleep $M/gamemenu; : > $M/card/pandory/patch.txt
case $SC in
  ok)    touch $M/card/pandory/front/autostart; FRONT_SEC=8; MENU_SEC=4; CYCLES=3 ;;
  crash) touch $M/card/pandory/front/autostart; FRONT_SEC=1; MENU_SEC=3; CYCLES=7 ;;
  off)   FRONT_SEC=8; MENU_SEC=3; CYCLES=2 ;;
  norestart) touch $M/card/pandory/front/autostart; FRONT_SEC=3; MENU_SEC=3; CYCLES=1 ;;
esac
t0=$(date +%s); log() { echo "[$(( $(date +%s) - t0 ))s] $*"; }
for c in $(seq 1 $CYCLES); do
  ( CARD=$M/card AUTO_WAIT=1 AUTO_TRIES=6 GM_CMD="touch $M/restarted" FRONT_CMD="sleep $FRONT_SEC" sh $M/auto.sh & )     # the hook, started by Pandory just before the menu
  sleep 1; $M/gamemenu $MENU_SEC & GM=$!
  log "cycle $c: menu pid $GM started"
  wait $GM; rc=$?
  log "cycle $c: menu ended rc=$rc ($( [ $rc -eq 137 ] && echo killed-by-autostart || echo normal ))"
  sleep 3                                                                                    # let a running auto.sh finish
  log "   flags: skip=$([ -f /tmp/front_skip ] && echo yes || echo no) fails=$(cat $M/card/pandory/front/autostart_fails 2>/dev/null) failed=$([ -f $M/card/pandory/front/autostart_failed ] && echo yes || echo no)"
done
sleep 14; echo "restarted by auto.sh: $([ -f $M/restarted ] && echo yes || echo no)"
echo "--- last auto_patch.log"; cat $M/card/auto_patch.log
