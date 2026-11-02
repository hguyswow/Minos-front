"""Build menu 'collections' (system filters) for the Pandora Saga DX2 Plus.

The stock menu stores a visibility bitmap (1 bit per stock game) in /userdata/gamemenu.cfg.
This script writes one ready-made cfg per collection to E:\pandory\collections and one menu script per collection
to E:\roms_pandory\scripts. Selecting a script copies the cfg and returns to the menu; the menu then shows only that collection.
Run:  python make_collections.py E:
"""
import json, os, struct, sys, zlib

BASE_CFG = r'D:\Backup\working_state_2026-11-01\gamemenu_baseline.cfg'   # unchanged settings with every game visible
CLS = r'D:\Backup\tools\gl_class.json'
GL = r'D:\Backup\firmware_extract\lib\gl.bin'
BITMAP = 0x830
COLLECTIONS = [                     # file, script number+name, systems shown, title in the menu
    ('all',     '10_Col_All',     None,                                   '전체 게임 보기'),
    ('arcade',  '11_Col_Arcade',  {'Arcade', 'Arcade (기타)', 'Unreadable'}, '아케이드만'),
    ('md',      '12_Col_MD',      {'Mega Drive'},                          '메가드라이브만'),
    ('sfc',     '13_Col_SFC',     {'SNES'},                                '슈퍼패미컴만'),
    ('nes',     '14_Col_NES',     {'NES'},                                 '패미컴만'),
    ('ps1',     '15_Col_PS1',     {'PlayStation'},                         '플레이스테이션만'),
]


def build(base, show):
    b = bytearray(base)
    g = open(GL, 'rb').read()
    cls = json.load(open(CLS))
    for i in range(9800):
        name = g[224 + i * 112 + 4:224 + i * 112 + 40].split(b'\0')[0]
        keep = True if show is None else (cls[i] in show or name in (b'END_OF_THE_LIST', b''))
        byte, bit = BITMAP + i // 8, i % 8
        if keep:
            b[byte] |= (1 << bit)
        else:
            b[byte] &= ~(1 << bit) & 0xff
    crc = zlib.crc32(bytes(b[:6224])) & 0xffffffff
    b[6224:6228] = struct.pack('>I', crc)
    return bytes(b)


def main():
    drive = (sys.argv[1] if len(sys.argv) > 1 else 'E:').rstrip('\/') + os.sep
    base = open(BASE_CFG, 'rb').read()
    assert len(base) == 6228
    cdir = os.path.join(drive, 'pandory', 'collections')
    sdir = os.path.join(drive, 'roms_pandory', 'scripts')
    os.makedirs(cdir, exist_ok=True)
    mp = os.path.join(drive, 'pandory', 'names_map.txt')
    names = open(mp, encoding='utf-8').read() if os.path.exists(mp) else ''
    add = ''
    for key, script, show, title in COLLECTIONS:
        data = build(base, show)
        open(os.path.join(cdir, key + '.cfg'), 'wb').write(data)
        visible = sum((data[BITMAP + i // 8] >> (i % 8)) & 1 for i in range(9800))
        sh = '#!/bin/bash\n# Collection "%s": installs the menu setting that shows only these games, then returns to the menu (the menu restarts and reads it).\n' % key
        sh += 'CARD=$(cd "$(dirname "$0")/../.." && pwd)\n'
        sh += 'if [ ! -f "$CARD/pandory/collections/original.cfg" ]; then cat /userdata/gamemenu.cfg > "$CARD/pandory/collections/original.cfg"; fi\n'
        sh += ('cat "$CARD/pandory/collections/%s.cfg" > /userdata/gamemenu.cfg\nsync\n') % key
        open(os.path.join(sdir, script + '.sh'), 'w', newline='\n').write(sh)
        fname = script + '.sh'
        if fname not in names:
            add += '%s | [모음] %s\n' % (fname, title)
        print('%-8s visible stock entries: %d' % (key, visible))
    if add:
        open(mp, 'a', encoding='utf-8', newline='\n').write(add)


if __name__ == '__main__':
    main()
