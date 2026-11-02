"""Makes the preview pictures MinosFront shows next to the game list.

  python build_previews.py F:            (needs ffmpeg on the PATH; safe to run again, finished files are skipped)

For every game in <card>/pandory/library.tsv it takes the stock preview video <card>/movies/<name>.avi and writes three
320x240 JPEG pictures to <card>/pandory/snap/<name>_1.jpg .. _3.jpg (at 25 %, 50 % and 75 % of the clip). Read-only on the videos.
"""
import os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

FRAMES = (1.6, 3.2, 4.8)      # seconds; the stock clips are about 6.4 s long


def one(args):
    src, dst = args
    ok = 0
    for i, t in enumerate(FRAMES, 1):
        out = "%s_%d.jpg" % (dst, i)
        if os.path.exists(out) and os.path.getsize(out) > 0:
            ok += 1
            continue
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", src, "-frames:v", "1", "-vf", "scale=320:240", "-q:v", "5", out],
                           stdin=subprocess.DEVNULL, capture_output=True)
        if r.returncode == 0 and os.path.exists(out):
            ok += 1
    return src, ok


def main(card):
    pd = os.path.join(card, "pandory")
    snap = os.path.join(pd, "snap")
    os.makedirs(snap, exist_ok=True)
    jobs, missing = [], 0
    for line in open(os.path.join(pd, "library.tsv"), encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) < 4:
            continue
        base = os.path.splitext(p[1])[0]
        src = os.path.join(card, "movies", base + ".avi")
        if os.path.exists(src):
            jobs.append((src, os.path.join(snap, base)))
        else:
            missing += 1
    print("%d videos, %d games without video" % (len(jobs), missing))
    done = bad = 0
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as ex:
        for n, (src, ok) in enumerate(ex.map(one, jobs), 1):
            bad += ok < len(FRAMES)
            if n % 250 == 0:
                print("  %d/%d" % (n, len(jobs)), flush=True)
    print("done, %d games with missing pictures" % bad)


if __name__ == "__main__":
    main((sys.argv[1] if len(sys.argv) > 1 else "F:").rstrip("\/") + os.sep)
