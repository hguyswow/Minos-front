#!/bin/bash
# Tests the key layout generator and checks that RetroArch finds the remap file.  Run in WSL as root.
export PATH=/opt/armv7-toolchain/bin:$PATH
ls /mnt/f/pandory >/dev/null 2>&1 || mount -t drvfs F: /mnt/f
arm-linux-gcc -O1 -D_GNU_SOURCE -I/mnt/c/dev/pandora_editor/tools /mnt/c/dev/pandora_editor/tools/test_keys.c -o /tmp/test_keys -ldl 2>&1 | grep -E "error|warning: impl"
rm -rf /tmp/minos_remap
Q=/opt/qemu/usr/bin/qemu-arm-static
CORE=/opt/devroot/usr/lib/libretro/fbalpha2012_libretro.so
SPEC="${1:-b=B;c=Y;d=B+Y;a=X;e=A;f=X+A}"
$Q -L /opt/devroot /tmp/test_keys $CORE kof97.zip "$SPEC" /tmp/ovr.cfg
echo "--- cfg"; cat /tmp/ovr.cfg; echo "--- remap files"; find /tmp/minos_remap -type f -exec sh -c 'echo {}; cat {}' \;
# does RetroArch pick the remap file up?
W=/tmp/tk; rm -rf $W; mkdir -p $W/s $W/st $W/sy $W/c
cat > $W/cfg <<EOC
video_driver = "null"
audio_driver = "null"
input_driver = "null"
input_joypad_driver = "null"
menu_driver = "null"
audio_enable = "false"
config_save_on_exit = "false"
log_verbosity = "true"
savefile_directory = "$W/s"
savestate_directory = "$W/st"
system_directory = "$W/sy"
cache_directory = "$W/c"
EOC
timeout 60 $Q -L /opt/devroot -E HOME=$W /mnt/f/pandory/ra/retroarch --config $W/cfg --appendconfig /tmp/ovr.cfg -L $CORE /mnt/f/roms/kof97.zip --max-frames=10 --verbose 2>&1 | grep -a -i "remap" | head
