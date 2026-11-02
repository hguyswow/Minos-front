#!/bin/bash
# modules_prepare with full error output.  usage: wifi_mp.sh base|wifi
export PATH=/opt/armv7-toolchain/bin:$PATH
K=/opt/wifi/linux-4.4.159
cd $K
make ARCH=arm CROSS_COMPILE=arm-linux- HOSTCC="arm-linux-gcc -static -O1" HOSTLD=arm-linux-ld O=/opt/wifi/o_${1:-base} modules_prepare 2>&1 | grep -v "^  \(HOSTCC\|CHK\|UPD\|SYSTBL\)" | tail -${2:-25}
