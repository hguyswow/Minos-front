#!/bin/bash
# Strips the built Wi-Fi modules and copies them (and a note about the layout check) to D:\Backup\wifi\modules.
export PATH=/opt/armv7-toolchain/bin:$PATH
mkdir -p /mnt/d/Backup/wifi/modules
for f in /opt/wifi/out/*.ko; do arm-linux-strip --strip-debug "$f" -o /mnt/d/Backup/wifi/modules/$(basename $f); done
cp /opt/wifi/device_config /mnt/d/Backup/wifi/modules/device_config.txt; cp /opt/wifi/o_wifi/.config /mnt/d/Backup/wifi/modules/wifi_config.txt; cp /opt/wifi/layout.log /mnt/d/Backup/wifi/modules/layout_check.txt
ls -la /mnt/d/Backup/wifi/modules
