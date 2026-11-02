"""English names for the non-arcade games of the library (Mega Drive / SNES / NES), by ROM checksum.

  python build_en_names.py F: D:\\Backup\\tools\\dats

Reads <card>/pandory/library.tsv and the ROM inside each zip (the CRC32 is stored in the zip index; SNES/MD copier headers are tried
too) and looks it up in the No-Intro .dat files of the libretro-database project (downloaded into the dats folder):
  Sega - Mega Drive - Genesis.dat, Nintendo - Super Nintendo Entertainment System.dat, Nintendo - Nintendo Entertainment System.dat
Writes <card>/pandory/names_en.tsv   (file <TAB> english title).  Games that are not found keep their Korean name.
"""
import os, re, sys, zipfile, zlib, collections

DATS = {"md": "Sega - Mega Drive - Genesis.dat", "snes": "Nintendo - Super Nintendo Entertainment System.dat", "nes": "Nintendo - Nintendo Entertainment System.dat"}
ROW = re.compile(r'rom \( name "(.*)" size (\d+) crc ([0-9A-Fa-f]{8})')


def load_dat(path):
    names = {}
    for line in open(path, encoding="utf-8", errors="replace"):
        m = ROW.search(line)
        if m:
            n = re.sub(r"\.[A-Za-z0-9]{2,4}$", "", m.group(1))
            names.setdefault(int(m.group(3), 16), n)
    return names


def clean(n):                                  # "Super Mario World (USA)" -> "Super Mario World"; keep one region tag
    base = re.sub(r"\s*\((?:Rev|Beta|Proto|Unl|Aftermarket|Pirate|Sample|Demo|v\d)[^)]*\)", "", n)
    m = re.search(r"\((USA|Europe|Japan|World|Korea|Brazil|Asia|China|Taiwan|[A-Za-z, ]+)\)", base)
    title = re.sub(r"\s*\([^)]*\)", "", base).strip()
    title = re.sub(r"^(.*), (The|A|An)$", r"\2 \1", title)
    return title or n


def crcs_of(path):
    out = []
    try:
        with zipfile.ZipFile(path) as z:
            infos = sorted([i for i in z.infolist() if not i.is_dir()], key=lambda i: -i.file_size)[:1]
            for i in infos:
                out.append(i.CRC)
                data = None
                if i.file_size % 1024 == 512:                    # SNES copier header
                    data = z.read(i)[512:]
                    out.append(zlib.crc32(data) & 0xFFFFFFFF)
                if i.file_size > 16 and i.filename.lower().endswith(".nes"):   # NES: with / without the 16 byte header
                    data = z.read(i)
                    out.append(zlib.crc32(data[16:]) & 0xFFFFFFFF)
    except Exception:
        pass
    return out


def main(card, dats):
    dbs = {k: load_dat(os.path.join(dats, v)) for k, v in DATS.items() if os.path.exists(os.path.join(dats, v))}
    out, stat = [], collections.Counter()
    for line in open(os.path.join(card, "pandory", "library.tsv"), encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) < 4 or p[0] not in dbs:
            continue
        f = p[1]
        hit = None
        for c in crcs_of(os.path.join(card, "roms", f)):
            if c in dbs[p[0]]:
                hit = clean(dbs[p[0]][c]); break
        stat[p[0] + (" found" if hit else " not found")] += 1
        if hit:
            out.append((f, hit))
    with open(os.path.join(card, "pandory", "names_en.tsv"), "w", encoding="utf-8", newline="\n") as w:
        for f, t in out:
            w.write("%s\t%s\n" % (f, t))
    for k, v in sorted(stat.items()):
        print("  %-18s %5d" % (k, v))


if __name__ == "__main__":
    main((sys.argv[1] if len(sys.argv) > 1 else "F:").rstrip("\\/") + os.sep, sys.argv[2] if len(sys.argv) > 2 else r"D:\Backup\tools\dats")
