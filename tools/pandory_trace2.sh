#!/bin/bash
# Runs the Pandory executable under another name (argv[0]) on a COPY, with a system-call trace.  usage: pandory_trace2.sh NAME [seconds]
ls /mnt/f/pandory >/dev/null 2>&1 || mount -t drvfs F: /mnt/f
N=${1:-gamemenu}; S=${2:-20}
W=/tmp/ptrace; rm -rf $W; mkdir -p $W/pandory $W/tmp; cp /mnt/f/pandory/pandory $W/pandory/$N; cp /mnt/f/pandory/pandory.xml $W/pandory/ 2>/dev/null
cd $W/pandory
timeout $S unshare -m -- /opt/qemu/usr/bin/qemu-arm-static -L /opt/devroot -strace ./$N 2>&1 | grep -a -E "EXECUTING|STARTING|GAMEMENU|CMD|execve|ARGUMENTS|RESOLUTION|Running|Starting|PARSING|BINARY|UDISK|BIND|open\(\"/(tmp|usr|sdcard|mnt|media)" | grep -v "O_RDONLY.*\.so" | head -${LINES_MAX:-80}
