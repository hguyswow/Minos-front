r"""Game info (year / maker / genre) for the MinosFront info panel.

  python build_meta.py F: D:\Backup\tools\meta

Arcade: by set name from mame2003-plus.xml (year, manufacturer) and catver.ini (category).
MD / SNES / NES: by ROM checksum, using the libretro-database metadat files (genre / releaseyear / developer).
Writes <card>/pandory/meta.tsv   (file <TAB> year <TAB> maker <TAB> genre).
"""
import os, re, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_en_names import crcs_of, load_dat

SYS = {"md": "Sega - Mega Drive - Genesis.dat", "snes": "Nintendo - Super Nintendo Entertainment System.dat", "nes": "Nintendo - Nintendo Entertainment System.dat"}
GAME = re.compile(r'game \(\s*comment "(.*?)"\s*(?:\w+ "(.*?)"\s*)?rom \( crc ([0-9A-Fa-f]{8}) \)', re.S)


def load_meta(path):                                           # crc -> value, and game name -> value
    t = open(path, encoding="utf-8", errors="replace").read()
    out, byname = {}, {}
    for m in re.finditer(r'game \(\s*comment "(.*?)"\s*(?:\w+ "(.*?)"\s*)rom \( crc ([0-9A-Fa-f]{8}) \)', t, re.S):
        out[int(m.group(3), 16)] = m.group(2); byname[m.group(1)] = m.group(2)
    return out, byname


def arcade():
    d = {}
    t = open(os.path.join(META, "mame2003plus.xml"), encoding="utf-8", errors="replace").read()
    for m in re.finditer(r'<game name="([^"]+)"[^>]*>\s*<description>[^<]*</description>\s*(?:<year>([^<]*)</year>\s*)?(?:<manufacturer>([^<]*)</manufacturer>)?', t):
        d[m.group(1)] = [m.group(2) or "", (m.group(3) or "").strip(), ""]
    cat = None
    for line in open(os.path.join(META, "catver.ini"), encoding="utf-8", errors="replace"):
        if line.startswith("["):
            cat = line.strip() == "[Category]"; continue
        if cat and "=" in line:
            k, v = line.strip().split("=", 1)
            if k in d:
                d[k][2] = v.split(" / ")[0].split("*")[0].strip()
    return d


def main(card, meta):
    global META
    META = meta
    global DATSDIR
    DATSDIR = os.path.join(os.path.dirname(meta.rstrip("/\\")), "dats")
    ar = arcade()
    dbs = {}
    for k, v in SYS.items():
        dbs[k] = [load_meta(os.path.join(meta, "metadat_%s_%s" % (kind, v))) for kind in ("releaseyear", "developer", "genre")]
    nn = {k: load_dat(os.path.join(DATSDIR, v)) for k, v in SYS.items()}
    stat, rows = collections.Counter(), []
    for line in open(os.path.join(card, "pandory", "library.tsv"), encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) < 4:
            continue
        f, row = p[1], None
        if p[0] == "arcade":
            row = ar.get(re.sub(r"\.zip$", "", f, flags=re.I))
        elif p[0] in dbs:
            for c in crcs_of(os.path.join(card, "roms", f)):
                nm = nn[p[0]].get(c)
                vals = [db[0].get(c) or (db[1].get(nm, "") if nm else "") for db in dbs[p[0]]]
                if any(vals):
                    row = vals; break
        stat[p[0] + (" found" if row else " not found")] += 1
        if row and any(row):
            rows.append((f, row))
    with open(os.path.join(card, "pandory", "meta.tsv"), "w", encoding="utf-8", newline="\n") as w:
        for f, r in rows:
            w.write("%s\t%s\n" % (f, "\t".join(x.replace("\t", " ") for x in r)))
    for k, v in sorted(stat.items()):
        print("  %-18s %5d" % (k, v))


if __name__ == "__main__":
    main((sys.argv[1] if len(sys.argv) > 1 else "F:").rstrip("\/") + os.sep, sys.argv[2] if len(sys.argv) > 2 else r"D:\Backup\tools\meta")
