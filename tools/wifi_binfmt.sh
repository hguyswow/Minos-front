#!/bin/bash
# Registers qemu-arm as the handler for ARM ELF files (so ARM-built "host tools" of the kernel build can run in WSL without a native gcc).
mountpoint -q /proc/sys/fs/binfmt_misc || mount -t binfmt_misc none /proc/sys/fs/binfmt_misc
[ -e /proc/sys/fs/binfmt_misc/qemu-arm ] && echo "already registered" && exit 0
echo ':qemu-arm:M::\x7fELF\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x28\x00:\xff\xff\xff\xff\xff\xff\xff\x00\xff\xff\xff\xff\xff\xff\xff\xff\xfe\xff\xff\xff:/opt/qemu/usr/bin/qemu-arm-static:F' > /proc/sys/fs/binfmt_misc/register && echo registered
ls /proc/sys/fs/binfmt_misc
