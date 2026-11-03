#!/bin/bash
mkdir -p /mnt/d/Backup/wifi/modules_rk
for f in /opt/wifi/out_rk/*.ko; do /opt/armv7-toolchain/bin/arm-linux-strip --strip-debug $f -o /mnt/d/Backup/wifi/modules_rk/$(basename $f); done
/opt/armv7-toolchain/bin/arm-linux-readelf -p .modinfo /opt/wifi/out_rk/rtl8192cu.ko | grep -E "vermagic|depends"
ls -la /mnt/d/Backup/wifi/modules_rk
