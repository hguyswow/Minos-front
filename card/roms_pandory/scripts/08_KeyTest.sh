#!/bin/bash
# TEST: button map. Runs the SDL probe for 90 seconds; every key press is written to keytest.log on the card (use it to learn what each physical button sends).
CARD=$(cd "$(dirname "$0")/../.." && pwd)
export XDG_RUNTIME_DIR=/data
export XDG_CONFIG_HOME=/data
echo "start $(date)" > "$CARD/keytest_run.log"
/lib/ld-linux-armhf.so.3 --library-path /usr/lib:/lib "$CARD/pandory/bin/sdltest" "$CARD/keytest.log" 90 >> "$CARD/keytest_run.log" 2>&1
echo "exit code $?" >> "$CARD/keytest_run.log"
sync
