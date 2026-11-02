#!/bin/bash
# usage: batch.sh N [JOBS]  -> tests the next N untested games of /mnt/f/pandory/library.tsv (resumable)
N=${1:-100}; P=${2:-6}
[ -d /mnt/f/roms ] || { mkdir -p /mnt/f; mount -t drvfs F: /mnt/f; }
touch /opt/rt/results.tsv
cut -f1 /opt/rt/results.tsv | sort -u > /tmp/rt_done.txt
awk -F'\t' 'FILENAME==ARGV[1]{d[$1]=1;next} !($2 in d){print $1"\t"$2"\t"$4}' /tmp/rt_done.txt /mnt/f/pandory/library.tsv | head -n $N > /tmp/rt_todo.txt
echo "todo this round: $(wc -l < /tmp/rt_todo.txt)  already done: $(wc -l < /opt/rt/results.tsv)"
cat /tmp/rt_todo.txt | tr '\t' '\n' | xargs -d '\n' -n 3 -P $P /opt/rt/job.sh
echo "done now: $(wc -l < /opt/rt/results.tsv)"
