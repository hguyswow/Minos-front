"""Regenerate the Pandora Saga DX2 Plus name patch from the files in roms_pandory.

Usage:  python pandora_names.py E:            (E: = the memory card drive)

What it does
  1. Lists the games Pandory will add to the menu (same order the menu uses).
  2. Reads E:\\pandory\\names_map.txt  ("file name | display name") for titles.
     Missing files are appended there with an automatic title so you can edit them.
  3. Writes E:\\pandory\\patch.txt (applied automatically at every menu start by auto.sh).
  4. Writes game_list.md / game_list.csv next to this script (menu number, system, title, file).

Menu number of the first added game is 9801; the k-th added game is 9801+k.
"""
import csv, os, re, sys

BS = chr(92)
STOCK = 9882                 # menu's visible stock entries (live value)
NAME_BASE = 0xBB9A3C         # live name table
REC = 0x580                  # name record size
MAX_GAMES = 240              # name table / list headroom
SYS_TAG = {                  # folder -> tag shown before the title ('' = none)
    '32x': '[32X]', 'amiga': '[AMIGA]', 'amiga1200': '[AMIGA]', 'atari2600': '[2600]', 'atarist': '[ST]',
    'gb': '[GB]', 'gba': '[GBA]', 'gbc': '[GBC]', 'gblink': '[GB]', 'genesis': '[MD]', 'pce': '[PCE]',
    'ports': '[PORT]', 'scripts': '[SCRIPT]', 'megadrive': '[MD]', 'snes': '[SFC]', 'nes': '[FC]',
}
USE_TAGS = '--no-tags' not in sys.argv
CODE_PATCHES = [(0x2f618, '000'), (0x2f728, '000'), (0x2fa68, '000'), (0x31330, '000' + BS + '000' + BS + '240' + BS + '341')]


def octal(bs):
    return ''.join(BS + format(b, '03o') for b in bs)


def pretty(stem):
    s = re.sub(r'[_]+', ' ', stem).strip()
    return s


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    drive = (args[0] if args else 'E:').rstrip('\\/') + os.sep
    rp = os.path.join(drive, 'roms_pandory')
    xml = open(os.path.join(drive, 'pandory', 'pandory.xml'), encoding='utf-8', errors='replace').read()
    folders = sorted(set(re.findall(r'<emulator [^>]*folder="([^"]+)"', xml)))
    games = []
    for f in folders:
        d = os.path.join(rp, f)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d), key=lambda n: n.encode('utf-8')):
            p = os.path.join(d, name)
            if not os.path.isfile(p) or name.startswith('.') or name.lower().endswith('.txt'):
                continue
            games.append((f, name))
    if len(games) > MAX_GAMES:
        print('WARNING: %d games; only the first %d get names' % (len(games), MAX_GAMES))
        games = games[:MAX_GAMES]

    mp = os.path.join(drive, 'pandory', 'names_map.txt')
    names = {}
    if os.path.exists(mp):
        for line in open(mp, encoding='utf-8'):
            if '|' in line and not line.startswith('#'):
                k, v = line.rstrip('\n').split('|', 1)
                names[k.strip()] = v.strip()
    added = []
    for f, name in games:
        if name not in names:
            names[name] = pretty(os.path.splitext(name)[0])
            added.append(name)
    with open(mp, 'w', encoding='utf-8', newline='\n') as o:
        o.write('# file name | title shown in the menu (edit the title; keep it under about 24 characters)\n')
        for f, name in games:
            o.write('%s | %s\n' % (name, names[name]))

    lines = []
    rows = []
    for k, (f, name) in enumerate(games):
        title = names[name]
        tag = SYS_TAG.get(f, '') if USE_TAGS else ''
        shown = (tag + ' ' + title).strip() if tag else title
        ko = shown.encode('utf-32le') + b'\0\0\0\0'
        en = shown.encode('ascii', 'replace') + b'\0'
        # D k slot-offset escapes: the record index is read live from the menu's list (changes when games are hidden)
        lines.append('D %d %d %s' % (k, 0x340, octal(en)))
        lines.append('D %d %d %s' % (k, 0x380, octal(ko)))
        lines.append('D %d %d %s' % (k, 0x000, octal(ko)))
        lines.append('D %d %d %s' % (k, 0x0c0, octal(ko)))
        rows.append((9801 + k, f, shown, name))
    for a, e in CODE_PATCHES:
        lines.append('%d %s' % (a, BS + e))
    out = os.path.join(drive, 'pandory', 'patch.txt')
    open(out, 'w', newline='\n').write('\n'.join(lines) + '\n')

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, 'game_list_added.csv'), 'w', encoding='utf-8-sig', newline='') as c:
        w = csv.writer(c)
        w.writerow(['menu number', 'folder', 'title shown', 'file'])
        w.writerows(rows)
    with open(os.path.join(here, 'game_list_added.md'), 'w', encoding='utf-8-sig') as m:
        m.write('# Added games (menu numbers)\n\n| No. | Folder | Title | File |\n|---|---|---|---|\n')
        for r in rows:
            m.write('| %d | %s | %s | %s |\n' % r)
    print('%d games -> %s' % (len(games), out))
    if added:
        print('New titles added to names_map.txt (edit them if you like):')
        for n in added:
            print('   ', n, '->', names[n])
    for r in rows:
        print(r[0], r[1], '|', r[2])


if __name__ == '__main__':
    main()
