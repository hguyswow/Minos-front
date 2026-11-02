#!/bin/bash
# W4: static ARM builds of libnl-3 and wpa_supplicant (+ wpa_cli) for the device.   Output: /opt/wifi/out/{wpa_supplicant,wpa_cli}
export PATH=/opt/armv7-toolchain/bin:$PATH
bash /mnt/c/dev/pandora_editor/tools/wifi_binfmt.sh >/dev/null 2>&1
W=/opt/wifi; SR=$W/sysroot; mkdir -p $W/src $SR $W/out; cd $W/src
[ -d libnl-3.9.0 ] || tar xf /mnt/d/Backup/wifi/src/libnl-3.9.0.tar.gz
[ -d wpa_supplicant-2.10 ] || tar xf /mnt/d/Backup/wifi/src/wpa_supplicant-2.10.tar.gz
echo "== libnl"
cd libnl-3.9.0
[ -f Makefile ] || ./configure --host=arm-linux --prefix=$SR --enable-static --disable-shared --disable-cli --disable-debug CC="arm-linux-gcc -static" > /tmp/nl_conf.log 2>&1 || { tail -15 /tmp/nl_conf.log; exit 1; }
make -j16 > /tmp/nl_make.log 2>&1 && make install > /tmp/nl_inst.log 2>&1 || { tail -15 /tmp/nl_make.log; exit 1; }
ls $SR/lib | head
echo "== wpa_supplicant"
cd $W/src/wpa_supplicant-2.10/wpa_supplicant
cat > .config <<EOC
CONFIG_DRIVER_NL80211=y
CONFIG_LIBNL32=y
CONFIG_TLS=internal
CONFIG_INTERNAL_LIBTOMMATH=y
CONFIG_CTRL_IFACE=y
CONFIG_BACKEND=file
CONFIG_IEEE80211N=y
CONFIG_NO_RANDOM_POOL=n
CONFIG_NO_WPA_PASSPHRASE=y
CONFIG_L2_PACKET=linux
CONFIG_PEERKEY=n
CONFIG_SAE=y
CFLAGS += -I$SR/include/libnl3 -O2
LDFLAGS += -static -L$SR/lib
LIBS += -L$SR/lib -lnl-genl-3 -lnl-3 -lm -lpthread
EOC
make clean > /dev/null 2>&1
make -j16 CC="arm-linux-gcc" PKG_CONFIG=/bin/true wpa_supplicant wpa_cli > /tmp/wpa_make.log 2>&1 || { tail -25 /tmp/wpa_make.log; exit 1; }
arm-linux-strip wpa_supplicant wpa_cli
cp wpa_supplicant wpa_cli $W/out/
file $W/out/wpa_supplicant 2>/dev/null; ls -la $W/out/wpa_supplicant $W/out/wpa_cli
