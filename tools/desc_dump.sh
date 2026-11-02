#!/bin/sh
# usage: desc_dump.sh CORE ROMFILE   (core name without _libretro.so, rom file name in F:/roms)
export PATH=/opt/armv7-toolchain/bin:$PATH
ls /mnt/f/pandory >/dev/null 2>&1 || mount -t drvfs F: /mnt/f
[ -x /tmp/desc_dump ] || arm-linux-gcc -O1 -D_GNU_SOURCE /mnt/c/dev/pandora_editor/tools/desc_dump.c -o /tmp/desc_dump -ldl 2>&1 | grep -E "error" 
mkdir -p /tmp/sysd
timeout 60 /opt/qemu/usr/bin/qemu-arm-static -L /opt/devroot /tmp/desc_dump /opt/devroot/usr/lib/libretro/$1_libretro.so "/mnt/f/roms/$2" /tmp/sysd 2>&1 | head -30
