#!/bin/bash
# W3b: Wi-Fi modules built from the Rockchip kernel tree (develop-4.4, 4.4.194) with the device's own config.
# The mainline-4.4.159 build crashed in wiphy_register on the device (struct layout differs in the vendor kernel).
export PATH=/opt/armv7-toolchain/bin:$PATH
bash /mnt/c/dev/pandora_editor/tools/wifi_binfmt.sh >/dev/null 2>&1
K=/opt/wifi/rk; O=/opt/wifi/o_rk
M="make -C $K ARCH=arm CROSS_COMPILE=arm-linux- HOSTCC=\"arm-linux-gcc -static -O1\" HOSTLD=arm-linux-ld O=$O"
mkdir -p $O; cp /opt/wifi/device_config $O/.config
S=$K/scripts/config
$S --file $O/.config -d SYSTEM_TRUSTED_KEYRING -d MODULE_SIG -d LOCALVERSION_AUTO
$S --file $O/.config -e WIRELESS -m CFG80211 -d CFG80211_WEXT -d WIRELESS_EXT -m MAC80211 -d MAC80211_DEBUGFS -d CFG80211_DEBUGFS \
   -e WLAN -e WLAN_VENDOR_REALTEK -m RTLWIFI -e RTLWIFI_USB -m RTL8192CU -d RTLWIFI_DEBUG -d MAC80211_LEDS -d MAC80211_MESH -d RFKILL -d CFG80211_CERTIFICATION_ONUS -e CFG80211_DEFAULT_PS -d CFG80211_INTERNAL_REGDB 2>&1 | tail -2
eval $M olddefconfig 2>&1 | tail -3
grep -E "^CONFIG_(CFG80211|MAC80211|RTLWIFI|RTL8192CU|RTLWIFI_USB|RTL8192C_COMMON)=" $O/.config
eval $M modules_prepare 2>&1 | grep -v "^  \(HOSTCC\|CHK\|UPD\|SYSTBL\|CC\|LD\|HOSTLD\)" | tail -8
ls $K/drivers/net/wireless | head -30
