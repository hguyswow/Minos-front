#!/bin/bash
# W3: builds the Wi-Fi modules (cfg80211, mac80211, rtlwifi, rtl_usb, rtl8192c-common, rtl8192cu) in /opt/wifi/o_wifi and collects them in /opt/wifi/out.
export PATH=/opt/armv7-toolchain/bin:$PATH
bash /mnt/c/dev/pandora_editor/tools/wifi_binfmt.sh >/dev/null 2>&1
K=/opt/wifi/linux-4.4.159
cd $K
grep -E "=m$" /opt/wifi/o_wifi/.config | head -20
time make -j16 ARCH=arm CROSS_COMPILE=arm-linux- HOSTCC="arm-linux-gcc -static -O1" HOSTLD=arm-linux-ld O=/opt/wifi/o_wifi modules 2>&1 | grep -E "error|Error|\.ko|undefined|warning: .*(implicit|incompatible)" | head -40
mkdir -p /opt/wifi/out; find /opt/wifi/o_wifi -name "*.ko" -exec cp {} /opt/wifi/out/ \;
ls -la /opt/wifi/out
for f in /opt/wifi/out/*.ko; do echo "$(basename $f): $(arm-linux-readelf -p .modinfo $f 2>/dev/null | grep -E 'vermagic|depends|firmware' | tr -s ' ' | tr '\n' ' ')"; done
