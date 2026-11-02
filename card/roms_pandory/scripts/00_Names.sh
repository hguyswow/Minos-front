#!/bin/bash
# Manual re-apply: runs the same patcher that starts automatically with the menu.
rm -rf /tmp/auto.lock
( setsid /bin/sh /mnt/sdcard/pandory/auto.sh >/dev/null 2>&1 < /dev/null & )
