r"""Screen ratio of every arcade game (for the MinosFront bezels).

  python build_aspects.py F: D:\Backup\tools\meta

Reads the <video aspectx= aspecty=> element of every game in mame2003-plus.xml (the ratio of the picture AFTER rotation, e.g. 3:4 for vertical
shooters) and writes <card>/pandory/aspects.tsv   (file <TAB> x:y)   for the games in library.tsv."""
import os, re, sys


def main(card, meta):
    t = open(os.path.join(meta, "mame2003plus.xml"), encoding="utf-8", errors="replace").read()
    asp = {}
    for m in re.finditer(r'<game name="([^"]+)"[^>]*>(.*?)</game>', t, re.S):
        v = re.search(r'<video [^>]*aspectx="(\d+)" aspecty="(\d+)"', m.group(2))
        if v:
            asp[m.group(1)] = "%s:%s" % (v.group(1), v.group(2))
    n = 0
    with open(os.path.join(card, "pandory", "aspects.tsv"), "w", encoding="utf-8", newline="\n") as w:
        for line in open(os.path.join(card, "pandory", "library.tsv"), encoding="utf-8"):
            p = line.rstrip("\n").split("\t")
            if len(p) >= 4 and p[0] == "arcade":
                r = asp.get(re.sub(r"\.zip$", "", p[1], flags=re.I))
                if r:
                    w.write("%s\t%s\n" % (p[1], r)); n += 1
    print("aspects.tsv: %d games" % n)


if __name__ == "__main__":
    main((sys.argv[1] if len(sys.argv) > 1 else "F:").rstrip("\\/") + os.sep, sys.argv[2] if len(sys.argv) > 2 else r"D:\Backup\tools\meta")
