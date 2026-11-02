#!/bin/sh
# Prints the input descriptors (button names) that a core reports for a game. usage: desc_probe.sh CORE ROM-IN-F:/roms
ls /mnt/f/pandory >/dev/null 2>&1 || mount -t drvfs F: /mnt/f
W=/tmp/dp$$; mkdir -p $W/s $W/st $W/sy $W/c
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
timeout 40 /opt/qemu/usr/bin/qemu-arm-static -L /opt/devroot -E HOME=$W /mnt/f/pandory/ra/retroarch --config $W/cfg -L /opt/devroot/usr/lib/libretro/$1_libretro.so "/mnt/f/roms/$2" --max-frames=5 --verbose > $W/o.log 2>&1
grep -a -i -A40 "SET_INPUT_DESCRIPTORS" $W/o.log | grep -a -i "player 1\|descriptor" | head -${3:-30}
rm -rf $W
