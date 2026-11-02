#!/bin/bash
# READ-ONLY: collects kernel/boot information into the card folder kerninfo.
CARD=$(cd "$(dirname "$0")/../.." && pwd)
D="$CARD/kerninfo"; mkdir -p "$D"
g() { [ -r "$1" ] && cat "$1" > "$D/$2" 2>&1; }
g /proc/cmdline cmdline.txt
g /proc/version version.txt
g /proc/cpuinfo cpuinfo.txt
g /proc/meminfo meminfo.txt
g /proc/filesystems filesystems.txt
g /proc/modules modules.txt
g /proc/partitions partitions.txt
g /proc/mounts mounts.txt
g /proc/iomem iomem.txt
g /proc/interrupts interrupts.txt
g /proc/devices devices.txt
g /proc/cgroups cgroups.txt
[ -r /proc/config.gz ] && cat /proc/config.gz > "$D/config.gz" || echo "no /proc/config.gz" > "$D/config_missing.txt"
ls -la /proc/sys/kernel > "$D/ls_sys_kernel.txt" 2>&1
ls -la /sys/kernel /sys/block /sys/class/block /sys/firmware > "$D/ls_sys.txt" 2>&1
ls -la /dev /dev/block/by-name /dev/disk/by-partlabel > "$D/ls_dev.txt" 2>&1
dmesg > "$D/dmesg.txt" 2>&1
for f in /sys/class/block/rkflash0*/size /sys/class/block/rkflash0*/start /sys/class/block/rkflash0*/uevent; do echo "== $f"; cat $f; done > "$D/rkflash_sys.txt" 2>&1
ls -la /lib/modules /lib/firmware > "$D/ls_modules.txt" 2>&1
which kexec chroot pivot_root switch_root unshare losetup mkfs.ext4 e2fsck fdisk parted > "$D/tools_present.txt" 2>&1
busybox --list > "$D/busybox_applets.txt" 2>&1
ls -la /usr/lib > "$D/ls_usr_lib.txt" 2>&1
ls -la /sys/class/drm /sys/class/graphics /sys/class/input > "$D/ls_video_input.txt" 2>&1
cat /sys/class/graphics/fb0/modes /sys/class/graphics/fb0/virtual_size > "$D/fb0.txt" 2>&1
touch "$D/DONE"; sync