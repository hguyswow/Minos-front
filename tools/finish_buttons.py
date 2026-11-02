"""Turns the raw result of desc_batch.sh into <card>/pandory/buttons.tsv (button names of every library game).
  python finish_buttons.py F: D:\Backup\tools\buttons_raw.tsv
Games whose core reports no names get the standard names of that core (mame2003 buttons 1-6 = RetroPad B A Y X L R).
"""
import os, sys, collections

FALLBACK = {"mame2003": "B:Button 1|A:Button 2|Y:Button 3|X:Button 4|L:Button 5|R:Button 6|"}


def main(card, raw):
    out, stat = [], collections.Counter()
    for line in open(raw, encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) < 3:
            continue
        f, core, desc = p[0], p[1], p[2]
        desc = "".join(x + "|" for x in desc.split("|") if x and not x.split(":", 1)[-1].startswith("(") and "Turbo" not in x)   # drop FDS / VS-system / turbo extras
        if not desc and core in FALLBACK:
            desc = FALLBACK[core]; stat["fallback " + core] += 1
        elif not desc:
            stat["no names: " + core] += 1
        else:
            stat["names: " + core] += 1
        out.append((f, core, desc))
    with open(os.path.join(card, "pandory", "buttons.tsv"), "w", encoding="utf-8", newline="\n") as w:
        for r in out:
            w.write("\t".join(r) + "\n")
    print("buttons.tsv: %d games" % len(out))
    for k, v in sorted(stat.items()):
        print("  %-30s %5d" % (k, v))


if __name__ == "__main__":
    main((sys.argv[1] if len(sys.argv) > 1 else "F:").rstrip("\/") + os.sep, sys.argv[2] if len(sys.argv) > 2 else r"D:\Backup\tools\buttons_raw.tsv")
