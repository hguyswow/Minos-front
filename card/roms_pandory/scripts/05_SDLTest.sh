#!/bin/bash
# TEST: runs our own SDL2 program (ARM) for 40 seconds: colour bars, moving square, logs inputs. Result: sdltest.log on the card.
CARD=$(cd "$(dirname "$0")/../.." && pwd)
export XDG_RUNTIME_DIR=/data
export XDG_CONFIG_HOME=/data
echo "start $(date)" > "$CARD/sdltest_run.log"
/lib/ld-linux-armhf.so.3 --library-path /usr/lib:/lib "$CARD/pandory/bin/sdltest" "$CARD/sdltest.log" 40 >> "$CARD/sdltest_run.log" 2>&1
echo "exit code $?" >> "$CARD/sdltest_run.log"
sync