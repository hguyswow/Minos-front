#!/bin/bash
# TEST: MinosFront, our own EmulationStation-like launcher (systems -> game list -> launch). Closes by itself after 10 minutes.
CARD=$(cd "$(dirname "$0")/../.." && pwd)
export XDG_RUNTIME_DIR=/data
export XDG_CONFIG_HOME=/data
/lib/ld-linux-armhf.so.3 --library-path /usr/lib:/lib "$CARD/pandory/bin/minosfront" "$CARD" 600 > "$CARD/front_run.log" 2>&1
echo "exit code $?" >> "$CARD/front_run.log"
sync