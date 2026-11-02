#!/bin/bash
# READ-ONLY: copies the whole internal flash (/dev/rkflash0) to the card as flash_full.img (about 218 MB).
CARD=$(cd "$(dirname "$0")/../.." && pwd)
D="$CARD/flashdump"; mkdir -p "$D"
exec >"$D/log.txt" 2>&1
echo start
dd if=/dev/rkflash0 of="$D/flash_full.img" bs=1M && echo "whole device ok" || echo "whole device FAIL"
ls -la "$D"
touch "$D/DONE"; sync