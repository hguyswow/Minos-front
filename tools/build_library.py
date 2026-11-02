"""Builds the MinosFront library of the ORIGINAL game list (about 5,300 games on the card, 9,800 menu entries).

  python build_library.py F:            writes F:\\pandory\\library.tsv   (read-only on everything else)

Sources (all read-only):
  <firmware_extract>/lib/gl.bin   rom file names (+4), 112 bytes per entry, entry k at k*112 (there is NO header: the first 224 bytes are
                                  two real entries; the last two entries are END markers)
  <firmware_extract>/lib/name.bin Korean names: record i, slots 14..17 (UTF-32LE, 64 bytes each)
  reference/gl_class.json         system of every gl entry (Arcade / NES / SNES / Mega Drive / PlayStation)
  <card>/fba2012.txt, mame2003.txt  which arcade set names each core supports
  <card>/roms/                    the files that really exist

Output columns (tab separated, UTF-8):  system  file  korean_title  core
The core is a stock firmware core (/usr/lib/libretro/<core>_libretro.so); MinosFront starts RetroArch with it.
"""
import collections, json, os, re, sys

FW = r"D:\Backup\firmware_extract\lib"
HERE = os.path.dirname(os.path.abspath(__file__))
CLASS = os.path.join(HERE, "..", "reference", "gl_class.json")

SYSTEM_KEY = {"Arcade": "arcade", "Arcade (기타)": "arcade", "NES": "nes", "SNES": "snes",
              "Mega Drive": "md", "PlayStation": "ps1"}
CORE = {"nes": "fceumm", "snes": "snes9x", "md": "genesisplusgx", "ps1": "pcsx_rearmed"}   # md_*.zip hold ONE plain Mega Drive ROM (.smd/.gen/.bin)
ORDER = ["arcade", "md", "snes", "nes", "ps1"]


def read_set_names(path):
    names = set()
    if not os.path.exists(path):
        return names
    for line in open(path, encoding="utf-8", errors="replace"):
        m = re.match(r"\s*([A-Za-z0-9_\-]+)\b", line)
        if m:
            names.add(m.group(1).lower())
    return names


def main(card):
    gl = open(os.path.join(FW, "gl.bin"), "rb").read()
    nm = open(os.path.join(FW, "name.bin"), "rb").read()
    cls = json.load(open(CLASS, encoding="utf-8"))
    rec = 0x580
    roms_dir = os.path.join(card, "roms")
    on_card = {f.lower(): f for f in os.listdir(roms_dir)}
    fba = read_set_names(os.path.join(card, "fba2012.txt"))
    mame = read_set_names(os.path.join(card, "mame2003.txt"))
    print("support lists: fba2012=%d sets, mame2003=%d sets, files on card=%d" % (len(fba), len(mame), len(on_card)))

    def korean(i):
        s = ""
        for slot in (14, 15, 16, 17):
            b = nm[i * rec + slot * 64: i * rec + (slot + 1) * 64]
            s += b.decode("utf-32le", "ignore").split("\0")[0]
        return s.strip()

    seen, out = set(), []
    stat = collections.Counter()
    for i in range(9800):
        # gl.bin has NO header: entry i is at i*112 (the first 224 bytes are two real entries) and its name is name.bin record i.
        rn = gl[i * 112 + 4: i * 112 + 40].split(b"\0")[0].decode("latin1")
        # gl_class.json was built with the old 224-byte offset, so it is shifted by two entries; entries 0 and 1 are Arcade.
        system = SYSTEM_KEY.get(cls[i - 2] if i >= 2 else "Arcade")
        if not rn or not system:
            stat["skipped (no rom name / unknown system)"] += 1
            continue
        fn = on_card.get((rn + ".zip").lower()) or on_card.get(rn.lower())
        if not fn:
            for ext in (".bin", ".cue", ".iso"):
                fn = on_card.get((rn + ext).lower())
                if fn:
                    break
        if not fn:
            stat["skipped (file not on card)"] += 1
            continue
        if fn in seen:
            stat["duplicate entry of a file already listed"] += 1
            continue
        seen.add(fn)
        base = os.path.splitext(fn)[0].lower()
        if system == "arcade":
            core = "fbalpha2012" if base in fba else "mame2003" if base in mame else "mame2003"
            if base not in fba and base not in mame:
                stat["arcade set in neither support list (tried with mame2003)"] += 1
        else:
            core = CORE[system]
        title = korean(i) or base
        title = re.sub(r"[\t\r\n]+", " ", title)
        out.append((system, fn, title, core))
        stat["listed: %s / %s" % (system, core)] += 1
    out.sort(key=lambda r: (ORDER.index(r[0]), r[2].lower(), r[1].lower()))
    dst = os.path.join(card, "pandory", "library.tsv")
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        for r in out:
            f.write("\t".join(r) + "\n")
    print("written %s : %d games" % (dst, len(out)))
    for k, v in sorted(stat.items()):
        print("  %-62s %5d" % (k, v))
    return out


if __name__ == "__main__":
    main((sys.argv[1] if len(sys.argv) > 1 else "F:").rstrip("\\/") + os.sep)
