#!/bin/bash
# Mock test of reference/m (the menu wrapper): MinosFront ok / crash, and switch off.   usage: test_wrapper.sh ok|crash|off
SC=${1:-ok}
M=/tmp/wrap; rm -rf $M; mkdir -p $M/card/pandory/front; cp /mnt/c/dev/pandora_editor/reference/m $M/m
printf '#!/bin/sh\necho "STOCK MENU started with args: $*"\n' > $M/gamemenu; chmod +x $M/gamemenu
case $SC in
  ok)    touch $M/card/pandory/front/autostart; FS=7 ;;
  crash) touch $M/card/pandory/front/autostart; FS=1 ;;
  off)   FS=7 ;;
esac
for c in 1 2 3; do
  echo "--- menu start $c"
  CARD=$M/card FRONT_CMD="sleep $FS" GM_CMD=$M/gamemenu sh $M/m -x extra
  echo "    flags: fails=$(cat $M/card/pandory/front/autostart_fails 2>/dev/null) failed=$([ -f $M/card/pandory/front/autostart_failed ] && echo yes || echo no)"
done
echo "--- wrapper.log"; cat $M/card/wrapper.log
