#!/bin/bash
# Backs up the settings of MinosFront / RetroArch (small files only, no games, no cores) into pandory_backups/minos_N on the card. Keeps the last 5.
# Restore: copy the files of a backup folder back into pandory/ (same relative paths).
CARD=$(cd "$(dirname "$0")/../.." && pwd)
B="$CARD/pandory_backups"; mkdir -p "$B"
N=$(cat "$B/.counter" 2>/dev/null); N=$(( ${N:-0} + 1 )); echo $N > "$B/.counter"
D="$B/minos_$N"; mkdir -p "$D/front" "$D/ra"
cp "$CARD"/pandory/front/*.txt "$CARD"/pandory/front/*.tsv "$CARD"/pandory/front/*.cfg "$D/front/" 2>/dev/null
cp -r "$CARD/pandory/front/backup" "$D/front/" 2>/dev/null
cp "$CARD"/pandory/ra/ra.cfg* "$D/ra/" 2>/dev/null
cp -r "$CARD/pandory/ra/layouts" "$D/ra/" 2>/dev/null
cp "$CARD"/pandory/*.tsv "$CARD"/pandory/names_map.txt "$CARD"/pandory/pandory.xml "$CARD"/pandory/auto.sh "$D/" 2>/dev/null
cp "$CARD/m" "$D/" 2>/dev/null
echo "backup $N done: $(du -sk "$D" | cut -f1) KB" > "$CARD/backup.log"
# keep the last 5
total=$(ls -d "$B"/minos_* 2>/dev/null | wc -l); drop=$((total - 5)); i=0
for old in $(ls -d "$B"/minos_* 2>/dev/null | sort -t_ -k2 -n); do [ $i -lt $drop ] && rm -rf "$old"; i=$((i+1)); done
sync
