"""Makes a patched COPY of the Pandory executable whose menu command runs the card's wrapper script (reference/m) instead of /usr/bin/gamemenu.

  python patch_pandory.py F:            -> F:\pandory\pandory.wrapper   (the original F:\pandory\pandory is NOT touched)
To use it (card in the PC): rename pandory -> pandory.hook_only, pandory.wrapper -> pandory, and copy reference/m to the card root as "m".
To go back: rename again. The wrapper only runs MinosFront when pandory/front/autostart exists, otherwise it just starts the stock menu.
"""
import os, sys

OFF = 0xE9F2C
OLD = b"/usr/bin/gamemenu \0"
NEW = b"sh /mnt/sdcard/m \0"


def main(card):
    src = os.path.join(card, "pandory", "pandory")
    d = bytearray(open(src, "rb").read())
    if bytes(d[OFF:OFF + len(OLD)]) != OLD:
        raise SystemExit("unexpected bytes at 0x%x: %r (a different Pandory version?)" % (OFF, bytes(d[OFF:OFF + 24])))
    room = d[OFF:OFF + 24].index(b" 2>&1"[:2]) if False else 20           # the next string (" 2>&1") starts 20 bytes after
    new = NEW + b"\0" * (room - len(NEW))
    d[OFF:OFF + room] = new
    dst = os.path.join(card, "pandory", "pandory.wrapper")
    open(dst, "wb").write(d)
    diff = sum(1 for a, b in zip(open(src, "rb").read(), d) if a != b)
    print("written", dst, "; bytes changed vs. the current pandory:", diff)


if __name__ == "__main__":
    main((sys.argv[1] if len(sys.argv) > 1 else "F:").rstrip("\/") + os.sep)
