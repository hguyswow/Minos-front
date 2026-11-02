#!/bin/sh
# Headless MinosFront test under QEMU:  front_test.sh KEYS [snapshot-name]   (needs the card mounted at /mnt/f; run in WSL as root)
sh /mnt/c/dev/pandora_editor/tools/build_front.sh >/dev/null
ls /mnt/f/pandory >/dev/null 2>&1 || mount -t drvfs F: /mnt/f
mkdir -p /tmp/so; rm -f /tmp/so/*
cd /tmp/mf_build
G="$3"; [ "$G" = "-" ] && G=""; S="$4"; [ "$S" = "-" ] && S=""; N="$5"; [ "$N" = "-" ] && N=""
MINOS_SYS="${SYSN:-}" MINOS_LANG="$N" MINOS_SPLASH="$S" MINOS_GAME="$G" MINOS_KEYS="$1" MINOS_SNAP=/tmp/so SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy timeout 300 /opt/qemu/usr/bin/qemu-arm-static -L /opt/devroot ./minosfront /mnt/f >/tmp/so/out.txt 2>&1
echo "exit $?"; tail -3 /tmp/so/out.txt; tail -4 /mnt/f/front.log
cp /tmp/so/final.bmp /mnt/c/Users/hguys/AppData/Local/Temp/${2:-final}.bmp 2>/dev/null; cp /tmp/so/splash.bmp /mnt/c/Users/hguys/AppData/Local/Temp/${2:-final}.bmp 2>/dev/null
