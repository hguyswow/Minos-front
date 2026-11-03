#!/bin/bash
export PATH=/opt/armv7-toolchain/bin:$PATH
cd /opt/wifi/rk
ls drivers/net/wireless | grep -i rtl
make ARCH=arm CROSS_COMPILE=arm-linux- HOSTCC="arm-linux-gcc -static -O1" HOSTLD=arm-linux-ld O=/opt/wifi/o_rk -j16 modules 2>&1 | grep -E "error|Error|.ko|undefined" | head -20
mkdir -p /opt/wifi/out_rk; find /opt/wifi/o_rk -name "*.ko" -exec cp {} /opt/wifi/out_rk/ \;
ls -la /opt/wifi/out_rk
