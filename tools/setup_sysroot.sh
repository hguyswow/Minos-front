#!/bin/bash
# Prepares the cross sysroot for building RetroArch for the Pandora Saga DX2 Plus (WSL, offline: all inputs come from /mnt/d).
set -e
TC=/opt/armv7-toolchain
SR=$TC/arm-buildroot-linux-gnueabihf/sysroot
DL=/mnt/d/Backup/toolchain_dl/ra_build
FX=/mnt/d/Backup/firmware_extract
mkdir -p /opt/src /opt/debs/x

echo "== RetroArch source"
if [ ! -d /opt/src/RetroArch ]; then
  mkdir -p /opt/src/RetroArch
  tar xzf $DL/RetroArch-v1.22.2.tar.gz -C /opt/src/RetroArch --strip-components=1
fi
ls /opt/src/RetroArch | head -3

echo "== Debian dev packages -> headers"
python3 - <<'EOF'
import glob, os, tarfile, io, lzma, gzip, shutil
out = '/opt/debs/x'
for deb in sorted(glob.glob('/mnt/d/Backup/toolchain_dl/ra_build/debs/*.deb')):
    data = open(deb, 'rb').read()
    assert data[:8] == b'!<arch>\n'
    pos = 8
    while pos < len(data):
        hdr = data[pos:pos+60]; name = hdr[:16].decode().strip(); size = int(hdr[48:58].decode().strip())
        body = data[pos+60:pos+60+size]; pos += 60 + size + (size & 1)
        if name.startswith('data.tar'):
            if name.endswith('.xz'): raw = lzma.decompress(body)
            elif name.endswith('.gz'): raw = gzip.decompress(body)
            else: raw = body
            tarfile.open(fileobj=io.BytesIO(raw)).extractall(out)
print('debs extracted')
EOF
cp -an /opt/debs/x/usr/include/. $SR/usr/include/ 2>/dev/null || true
ls $SR/usr/include | grep -E "^(EGL|GLES2|gbm.h|libdrm|xf86drm|alsa|libudev)" | tr '\n' ' '; echo

echo "== board libraries into sysroot (no overwrite)"
for f in $FX/usr/lib/*.so* $FX/lib/*.so*; do
  b=$(basename "$f")
  [ -e "$SR/usr/lib/$b" ] || [ -e "$SR/lib/$b" ] || cp -a "$f" "$SR/usr/lib/"
done

echo "== recreate symlinks lost during extraction (from the device's directory listing)"
python3 - <<'EOF'
import os, re
sr = '/opt/armv7-toolchain/arm-buildroot-linux-gnueabihf/sysroot/usr/lib'
n = 0
for line in open('/mnt/f/kerninfo/ls_usr_lib.txt', encoding='utf-8', errors='replace') if os.path.exists('/mnt/f/kerninfo/ls_usr_lib.txt') else open('/mnt/d/Backup/flash_dump_2026-11-01/kerninfo/ls_usr_lib.txt', encoding='utf-8', errors='replace'):
    m = re.search(r'\s(\S+) -> (\S+)\s*$', line)
    if not m: continue
    name, tgt = m.group(1), os.path.basename(m.group(2))
    link = os.path.join(sr, name)
    if os.path.exists(os.path.join(sr, tgt)) and not os.path.lexists(link):
        os.symlink(tgt, link); n += 1
print('symlinks created:', n)
EOF
ls -la $SR/usr/lib | grep -E "libEGL|libGLESv2|libgbm|libmali|libasound.so|libudev.so|libdrm.so" | awk '{print $9, $10, $11}'

echo "== pkg-config files"
PC=$SR/usr/lib/pkgconfig; mkdir -p $PC
for pc in /opt/debs/x/usr/lib/arm-linux-gnueabihf/pkgconfig/*.pc; do
  sed -e 's#/arm-linux-gnueabihf##g' "$pc" > "$PC/$(basename $pc)"
done
for n in egl:EGL:1.4 glesv2:GLESv2:2.0 gbm:gbm:13.0.6; do
  IFS=: read -r name lib ver <<< "$n"
  cat > $PC/$name.pc <<EOP
prefix=/usr
libdir=\${prefix}/lib
includedir=\${prefix}/include

Name: $name
Description: $lib via libmali (Mali-400 r7p0)
Version: $ver
Libs: -L\${libdir} -l$lib
Cflags: -I\${includedir} -DMESA_EGL_NO_X11_HEADERS -DEGL_NO_X11
EOP
done
rm -f $PC/wayland-egl.pc $PC/dri.pc
ls $PC | tr '\n' ' '; echo
touch $SR/.ra_sysroot
echo "sysroot ready"
