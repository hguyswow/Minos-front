#!/bin/bash
# Research helper (WSL, root): fetches kernel sources for the Wi-Fi module experiment. Nothing here touches the card or the device.
#   /opt/wifi/linux-4.4.159        mainline 4.4.159 (same version number as the device kernel)
#   /opt/wifi/rk-kernel            Rockchip's own kernel tree (develop-4.4), shallow
mkdir -p /opt/wifi && cd /opt/wifi
log=/opt/wifi/fetch.log; : > $log
{
  echo "== apt"; apt-get install -y flex bison libssl-dev libelf-dev bc xz-utils >/dev/null 2>&1 && echo "apt ok" || echo "apt failed"
  echo "== mainline 4.4.159"
  [ -d linux-4.4.159 ] || { curl -sL -m 600 -o l.tar.xz https://cdn.kernel.org/pub/linux/kernel/v4.x/linux-4.4.159.tar.xz && tar xf l.tar.xz && rm l.tar.xz; }
  head -4 linux-4.4.159/Makefile 2>&1
  echo "== rockchip kernel"
  [ -d rk-kernel ] || git clone --depth 1 -b develop-4.4 https://github.com/rockchip-linux/kernel.git rk-kernel 2>&1 | tail -2
  head -4 rk-kernel/Makefile 2>&1
  du -sh linux-4.4.159 rk-kernel 2>&1
  echo "== done"
} >> $log 2>&1
