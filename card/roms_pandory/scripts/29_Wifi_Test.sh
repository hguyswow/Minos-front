#!/bin/bash
# TEST (needs the dongle plugged in): loads the Wi-Fi modules from the card, checks that wlan0 appears, scans for networks. Does not connect or change anything permanent (a reboot undoes it).
# Result: wifi_test.log on the card.
CARD=$(cd "$(dirname "$0")/../.." && pwd)
W="$CARD/pandory/wifi"
L="$CARD/wifi_test.log"
mv -f "$L" "$L.prev" 2>/dev/null
# live log: dmesg is copied to the card every 0.3 s, so the last kernel messages before a crash survive
( while true; do { dmesg | tail -100; echo "--- marker: $(cat /tmp/wifi_step 2>/dev/null)"; } > "$CARD/wifi_live.log"; sync; sleep 0.3; done ) &
LIVE=$!
echo start > /tmp/wifi_step
{
echo "== date"; date
echo "== firmware path"; echo "$W/fw" > /sys/module/firmware_class/parameters/path 2>&1; cat /sys/module/firmware_class/parameters/path
echo "== firmware file check"; ls -la "$W/fw/rtlwifi/"; wc -c "$W/fw/rtlwifi/rtl8192cufw_TMSC.bin"; grep -E "sdcard|mmcblk" /proc/mounts
echo "== usb power: autosuspend off"; echo -1 > /sys/module/usbcore/parameters/autosuspend 2>&1; for d in /sys/bus/usb/devices/1-1; do echo on > $d/power/control 2>&1; cat $d/power/control; done
for m in cfg80211 mac80211 rtlwifi rtl8192c-common rtl_usb rtl8192cu; do
  n=${m//-/_}
  if grep -q "^$n " /proc/modules; then echo "== $m already loaded"; continue; fi
  echo "== insmod $m"; sync
  if [ "$m" = rtl8192cu ]; then
    # the driver that talks to the dongle: run it in the background so a hang cannot block the script, and save dmesg before and after
    dmesg | tail -30 > "$CARD/wifi_dmesg_before.log"; sync
    ( insmod "$W/mod_rk/$m.ko" > /tmp/insmod_cu.log 2>&1; echo "exit=$?" >> /tmp/insmod_cu.log ) &
    sleep 8; cat /tmp/insmod_cu.log; dmesg | tail -60 > "$CARD/wifi_dmesg_after.log"; sync
  else
    insmod "$W/mod_rk/$m.ko" 2>&1; echo "exit=$?"
  fi
done
sleep 4
echo "== lsmod"; lsmod; dmesg | tail -40 > "$CARD/wifi_dmesg_step2.log"; sync
echo "== /sys/class/net"; ls /sys/class/net
echo "== dmesg"; dmesg | grep -i -E "rtl|cfg80211|mac80211|wlan|firmware|usb 1-1|8192|taint|Unknown symbol|disagrees" | tail -50
if [ -d /sys/class/net/wlan0 ]; then
  echo "== wlan0 up"; echo "ifconfig-up" > /tmp/wifi_step; sync; ( ifconfig wlan0 up > /tmp/ifup.log 2>&1; echo "exit=$?" >> /tmp/ifup.log ) & sleep 6; cat /tmp/ifup.log; echo "idle-15s" > /tmp/wifi_step; sleep 15; echo "idle done" ; dmesg | tail -40 > "$CARD/wifi_dmesg_step3.log"; sync; ifconfig wlan0 2>&1
  echo "wpa-start" > /tmp/wifi_step
  printf 'ctrl_interface=/tmp/wpa_ctrl\nupdate_config=0\n' > /tmp/wpa_test.conf
  "$W/bin/wpa_supplicant" -B -i wlan0 -D nl80211 -c /tmp/wpa_test.conf -f /tmp/wpa_test.log 2>&1
  sleep 2; "$W/bin/wpa_cli" -p /tmp/wpa_ctrl scan 2>&1; sleep 6
  echo "== scan results"; "$W/bin/wpa_cli" -p /tmp/wpa_ctrl scan_results 2>&1 | head -30
  echo "== wpa log"; tail -20 /tmp/wpa_test.log
  killall wpa_supplicant 2>/dev/null
else
  echo "== NO wlan0 (modules did not bind)"
fi
echo "done" > /tmp/wifi_step; echo "== done"; sleep 1; kill $LIVE
} >> "$L" 2>&1
