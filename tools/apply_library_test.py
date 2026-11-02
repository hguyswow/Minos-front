"""Applies the result of the headless QEMU test (tools/rt_batch.sh + rt_job.sh) to the MinosFront library.

  python apply_library_test.py F: D:\\Backup\\tools\\library_test.tsv

Reads   <card>/pandory/library_all.tsv   (every game of the original list, made by build_library.py; created from library.tsv on first run)
        the test result: file \\t system \\t working core or NONE \\t reason
Writes  <card>/pandory/library.tsv        only the games that really load, each with the core that loaded it
        <card>/pandory/library_broken.tsv games that no stock core could load, with the reason (not shown in the menu)
"""
import os, shutil, sys, collections


def main(card, results):
    pd = os.path.join(card, "pandory")
    full, cur = os.path.join(pd, "library_all.tsv"), os.path.join(pd, "library.tsv")
    if not os.path.exists(full):
        shutil.copyfile(cur, full)
    res = {}
    for line in open(results, encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) >= 4:
            res[p[0]] = (p[2], p[3])
    good, bad, untested = [], [], 0
    stat = collections.Counter()
    for line in open(full, encoding="utf-8"):
        r = line.rstrip("\n").split("\t")
        if len(r) < 4:
            continue
        got = res.get(r[1])
        if got is None:
            untested += 1
            good.append(r)                       # never tested: keep it, with its guessed core
            continue
        core, why = got
        if core == "NONE":
            bad.append(r + [why])
            stat["broken: " + r[0]] += 1
        else:
            if core != r[3]:
                stat["core changed %s -> %s" % (r[3], core)] += 1
            good.append([r[0], r[1], r[2], core])
            stat["ok: " + r[0]] += 1
    with open(cur, "w", encoding="utf-8", newline="\n") as f:
        for r in good:
            f.write("\t".join(r) + "\n")
    with open(os.path.join(pd, "library_broken.tsv"), "w", encoding="utf-8", newline="\n") as f:
        for r in bad:
            f.write("\t".join(r) + "\n")
    print("library.tsv: %d games (untested kept: %d)   library_broken.tsv: %d games" % (len(good), untested, len(bad)))
    for k, v in sorted(stat.items()):
        print("  %-48s %5d" % (k, v))


if __name__ == "__main__":
    main((sys.argv[1] if len(sys.argv) > 1 else "F:").rstrip("\\/") + os.sep, sys.argv[2] if len(sys.argv) > 2 else r"D:\Backup\tools\library_test.tsv")
