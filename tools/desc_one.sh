#!/bin/bash
# desc_one.sh FILE CORE -> one line  file<TAB>core<TAB>B:name|Y:name|...   (player 1 face/shoulder buttons a core reports; empty = none)
f="$1"; c="$2"
r=$(timeout 40 /opt/qemu/usr/bin/qemu-arm-static -L /opt/devroot /tmp/desc_dump /opt/devroot/usr/lib/libretro/${c}_libretro.so "/mnt/f/roms/$f" /tmp/sysd 2>/dev/null | awk '/^  retropad / { id=$2; if (id=="B"||id=="Y"||id=="A"||id=="X"||id=="L"||id=="R"||id=="L2"||id=="R2"||id=="L3"||id=="R3") { n=substr($0, index($0,"= ")+2); printf "%s:%s|", id, n } }')
printf '%s\t%s\t%s\n' "$f" "$c" "$r"
