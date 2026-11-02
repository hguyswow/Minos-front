#!/bin/bash
# Wi-Fi module experiment, step W1/W2 (PC only, WSL root): prepares two kernel build trees from the device's own config
#   /opt/wifi/o_base  = the device config unchanged (what the running kernel was built with)
#   /opt/wifi/o_wifi  = device config + wireless options as modules
# then compares the layout (size / field offsets) of the structures modules share with the kernel. Equal = modules are safe to load.
export PATH=/opt/armv7-toolchain/bin:$PATH
bash /mnt/c/dev/pandora_editor/tools/wifi_binfmt.sh >/dev/null 2>&1
ls /mnt/f/kerninfo >/dev/null 2>&1 || mount -t drvfs F: /mnt/f
K=/opt/wifi/linux-4.4.159
M="make -C $K ARCH=arm CROSS_COMPILE=arm-linux- HOSTCC=\"arm-linux-gcc -static -O1\" HOSTLD=arm-linux-ld"
mkdir -p /opt/wifi/o_base /opt/wifi/o_wifi
zcat /mnt/f/kerninfo/config.gz > /opt/wifi/device_config
cp /opt/wifi/device_config /opt/wifi/o_base/.config
cp /opt/wifi/device_config /opt/wifi/o_wifi/.config
$K/scripts/config --file /opt/wifi/o_base/.config -d SYSTEM_TRUSTED_KEYRING -d MODULE_SIG   # host tool extract-cert would need openssl headers; no effect on shared structures
$K/scripts/config --file /opt/wifi/o_wifi/.config -d SYSTEM_TRUSTED_KEYRING -d MODULE_SIG
echo "== olddefconfig (base)"; eval $M O=/opt/wifi/o_base olddefconfig 2>&1 | tail -4
S=$K/scripts/config
$S --file /opt/wifi/o_wifi/.config -e WIRELESS -e CFG80211 -m CFG80211 -d CFG80211_WEXT -d WIRELESS_EXT -m MAC80211 -d MAC80211_DEBUGFS -d CFG80211_DEBUGFS \
   -e WLAN -e WLAN_VENDOR_REALTEK -m RTLWIFI -e RTLWIFI_USB -m RTL8192CU -d RTLWIFI_DEBUG -d MAC80211_LEDS -d MAC80211_MESH -d RFKILL -d CFG80211_CERTIFICATION_ONUS -e CFG80211_DEFAULT_PS -d CFG80211_INTERNAL_REGDB 2>&1 | tail -2
echo "== olddefconfig (wifi)"; eval $M O=/opt/wifi/o_wifi olddefconfig 2>&1 | tail -4
grep -E "^CONFIG_(WIRELESS|CFG80211|MAC80211|RTLWIFI|RTL8192CU|RTLWIFI_USB|WLAN|RFKILL|WIRELESS_EXT|LIB80211|MII)[A-Z_0-9]*=" /opt/wifi/o_wifi/.config
echo "== modules_prepare (base)"; eval $M O=/opt/wifi/o_base modules_prepare 2>&1 | tail -4
echo "== modules_prepare (wifi)"; eval $M O=/opt/wifi/o_wifi modules_prepare 2>&1 | tail -4
echo "== done prepare"
