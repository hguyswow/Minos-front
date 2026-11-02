#!/bin/bash
# TEST (safe, read-only): records what the kernel sees on the USB ports and whether it can load modules / firmware. Plug the Wi-Fi dongle in BEFORE running.
# Result: usb_probe.log on the card.
CARD=$(cd "$(dirname "$0")/../.." && pwd)
L="$CARD/usb_probe.log"
{
echo "== date"; date
echo "== uname"; uname -a
echo "== /sys/bus/usb/devices"
for d in /sys/bus/usb/devices/*; do echo "-- $d: vid=$(cat $d/idVendor 2>/dev/null) pid=$(cat $d/idProduct 2>/dev/null) manuf=$(cat $d/manufacturer 2>/dev/null) product=$(cat $d/product 2>/dev/null) speed=$(cat $d/speed 2>/dev/null) maxpower=$(cat $d/bMaxPower 2>/dev/null)"; done
echo "== lsusb"; lsusb 2>&1 | head -20
echo "== dmesg (usb, wlan, rtl, firmware, vbus)"; dmesg 2>&1 | grep -i -E "usb|wlan|rtl|firmware|vbus|dwc|ehci|ohci|regulator" | tail -60
echo "== /sys/class/net"; ls -la /sys/class/net 2>&1
echo "== /proc/net/dev"; cat /proc/net/dev 2>&1
echo "== /proc/modules"; cat /proc/modules 2>&1 | head
echo "== modules_disabled"; cat /proc/sys/kernel/modules_disabled 2>&1
echo "== firmware loader path param"; ls -la /sys/module/firmware_class/parameters 2>&1; cat /sys/module/firmware_class/parameters/path 2>&1
echo "== busybox applets (net / modules)"; busybox --list 2>/dev/null | grep -E "^(insmod|rmmod|lsmod|modprobe|ifconfig|ip|iw|iwconfig|udhcpc|wpa|ntpd|httpd|nc|wget|telnetd|route|ping)" | tr '\n' ' '; echo
echo "== which"; for t in wpa_supplicant wpa_cli iw dropbear sshd ntpd; do echo "$t: $(which $t 2>&1)"; done
echo "== usb regulator / gpio hints"; ls /sys/class/regulator 2>&1 | head; grep -i -E "usb|vbus|otg" /proc/interrupts 2>&1 | head
echo "== kernel config bits"; zcat /proc/config.gz 2>/dev/null | grep -E "CONFIG_(WLAN|CFG80211|MAC80211|RTLWIFI|USB_NET|MODULES|MODVERSIONS|FW_LOADER|WIRELESS)" | head -20
} > "$L" 2>&1
sync
echo
