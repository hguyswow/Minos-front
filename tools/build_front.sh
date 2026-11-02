#!/bin/sh
# Cross-builds MinosFront (run inside WSL, as root). Output: /tmp/mf_build/minosfront
export PATH=/opt/armv7-toolchain/bin:$PATH
FX=${FX:-/opt/devroot}
rm -rf /tmp/mf_build; mkdir -p /tmp/mf_build
cp /mnt/c/dev/pandora_editor/tools/front/*.c /mnt/c/dev/pandora_editor/tools/front/*.inc /mnt/c/dev/pandora_editor/tools/front/*.h /tmp/mf_build/ 2>/dev/null
cd /tmp/mf_build && rm -f test_ra_settings.c
arm-linux-gcc -O2 -D_GNU_SOURCE -I/opt/src/SDL-release-2.0.7/include minosfront.c -o minosfront $FX/usr/lib/libSDL2-2.0.so.0.7.0 -lm -ldl -lpthread 2>&1 | grep -E "error|warning: impl" ; ls -la minosfront
