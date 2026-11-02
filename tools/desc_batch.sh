#!/bin/bash
# Reads the button names of every library game (headless, QEMU, parallel). Output: /mnt/d/Backup/tools/buttons_raw.tsv.  Run in WSL as root.
export PATH=/opt/armv7-toolchain/bin:$PATH
ls /mnt/f/pandory >/dev/null 2>&1 || mount -t drvfs F: /mnt/f
arm-linux-gcc -O1 -D_GNU_SOURCE /mnt/c/dev/pandora_editor/tools/desc_dump.c -o /tmp/desc_dump -ldl || exit 1
mkdir -p /tmp/sysd
awk -F'\t' '{print $2"\n"$4}' /mnt/f/pandory/library.tsv > /tmp/dbl.txt
xargs -P 14 -n 2 bash /mnt/c/dev/pandora_editor/tools/desc_one.sh < /tmp/dbl.txt > /mnt/d/Backup/tools/buttons_raw.tsv
wc -l /mnt/d/Backup/tools/buttons_raw.tsv
