#!/bin/bash
# Runs the Pandory executable under QEMU with a system-call trace to see what it does.
# It works on a COPY in /tmp (Pandory rewrites pandory.xml in its folder - never run it inside the card folder!).
# usage: pandory_trace.sh [seconds] [args...]
ls /mnt/f/pandory >/dev/null 2>&1 || mount -t drvfs F: /mnt/f
S=${1:-20}; shift
W=/tmp/ptrace; rm -rf $W; mkdir -p $W/pandory; cp /mnt/f/pandory/pandory $W/pandory/; cp /mnt/f/pandory/pandory.xml $W/pandory/ 2>/dev/null
cd $W/pandory
timeout $S unshare -m -- /opt/qemu/usr/bin/qemu-arm-static -L /opt/devroot -strace ./pandory "$@" 2>&1 | grep -a -v -E "mmap|munmap|mprotect|brk|futex|rt_sig|clock|getpid|gettid|set_tid|set_robust|prlimit|ugetrlimit|uname|getuid|geteuid|getgid|getegid|_llseek|fstat64|read\(|write\(3|close\(3|open\(\"pandory.xml" | head -${LINES_MAX:-140}
