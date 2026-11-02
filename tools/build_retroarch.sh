#!/bin/bash
# Cross-builds RetroArch 1.22.2 for the Pandora Saga DX2 Plus (RK3128, Mali-400 r7p0, glibc 2.26): DRM/KMS + GLES2 + ALSA, no X11/Wayland/SDL.
set -euo pipefail
TC=/opt/armv7-toolchain
SR=$TC/arm-buildroot-linux-gnueabihf/sysroot
SRC=/opt/src/RetroArch
OUT=/mnt/d/Backup/tools/ra_build/out
PATCH=/mnt/d/Backup/toolchain_dl/RA2Pandora/src/RA2Pandora-master/patches/retroarch/0001-drm-driver-fixes.patch

# second pass of symlinks (some targets did not exist yet during the first pass)
python3 - <<'EOF'
import os, re
sr = '/opt/armv7-toolchain/arm-buildroot-linux-gnueabihf/sysroot/usr/lib'
lst = '/mnt/d/Backup/flash_dump_2026-11-01/kerninfo/ls_usr_lib.txt'
for _ in range(3):
    n = 0
    for line in open(lst, encoding='utf-8', errors='replace'):
        m = re.search(r'\s(\S+) -> (\S+)\s*$', line)
        if not m: continue
        name, tgt = m.group(1), os.path.basename(m.group(2))
        link = os.path.join(sr, name)
        if os.path.lexists(os.path.join(sr, tgt)) and not os.path.lexists(link):
            os.symlink(tgt, link); n += 1
    print('symlinks pass:', n)
EOF
ls $SR/usr/lib | grep -E "^(libEGL|libGLESv2|libgbm)" | tr '\n' ' '; echo

export PATH=$TC/bin:$PATH
export PKG_CONFIG_SYSROOT_DIR=$SR
export PKG_CONFIG_LIBDIR=$SR/usr/lib/pkgconfig
export PKG_CONFIG_PATH=""
export PKG_CONF_PATH=pkg-config
CPU="-march=armv7-a -mtune=cortex-a7 -mfpu=neon-vfpv4 -mfloat-abi=hard"
EGL="-DMESA_EGL_NO_X11_HEADERS -DEGL_NO_X11"
export CFLAGS="$CPU -O2 -pipe $EGL"
export CXXFLAGS="$CPU -O2 -pipe $EGL"
export LDFLAGS="-Wl,-rpath-link,$SR/usr/lib -Wl,-rpath-link,$SR/lib"

cd $SRC
if ! git apply --check -R "$PATCH" 2>/dev/null; then
  git apply "$PATCH" && echo "patch applied"
else
  echo "patch already applied"
fi

./configure --host=arm-linux \
  --disable-x11 --disable-wayland --disable-sdl --disable-sdl2 --disable-qt \
  --disable-ffmpeg --disable-freetype --disable-pulse --disable-oss --disable-jack \
  --disable-vulkan --disable-opengl1 --disable-opengl_core --disable-cg \
  --disable-v4l2 --disable-libusb --disable-systemd --disable-discord \
  --disable-translate --disable-accessibility --disable-slang --disable-glslang \
  --disable-spirv_cross --disable-crtswitchres --disable-cdrom --disable-parport \
  --disable-networking --disable-cheevos --disable-ssl --disable-builtinmbedtls \
  --enable-opengl --enable-opengles --enable-egl --enable-kms \
  --enable-udev --enable-alsa --enable-zlib --enable-threads \
  --enable-command --enable-neon --enable-floathard \
  --enable-plain_drm > /tmp/ra_configure.log 2>&1 || { tail -30 /tmp/ra_configure.log; exit 1; }
grep -E "^(Checking|Check).*(GLES|EGL|KMS|DRM|ALSA|udev|zlib)" /tmp/ra_configure.log | head -12

make -j16 > /tmp/ra_make.log 2>&1 || { tail -40 /tmp/ra_make.log; exit 2; }
mkdir -p $OUT
cp retroarch $OUT/retroarch
arm-linux-strip $OUT/retroarch
ls -la $OUT/retroarch
arm-linux-readelf -d $OUT/retroarch | grep NEEDED
