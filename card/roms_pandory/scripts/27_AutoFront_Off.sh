#!/bin/bash
# Turns OFF "MinosFront at start-up" (back to the normal menu at start).
CARD=$(cd "$(dirname "$0")/../.." && pwd)
rm -f "$CARD/pandory/front/autostart" "$CARD/pandory/front/autostart_fails"
sync
echo
