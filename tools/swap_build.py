import collections, os, shutil, zipfile, subprocess, re
SRC_NAME = r'D:\Backup\firmware_extract\lib\name.bin'
GL = r'D:\Backup\firmware_extract\lib\gl.bin'
OUT_NAME = r'D:\Backup\names_patch\name_swap.bin'
ROMDIR = r'U:\databank2\game\7.emul\roms\genesis\MDroms(kor)'
CARD = 'E:' + chr(92)
BK = r'D:\Backup\orig_stock_swap'
FF = r'C:\Users\hguys\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe'
R = 1408
games = [  # stock rom (replaced), source file, english, korean
 ('md_tmnttfu', 'Advanced Daisenryaku - Deutsch Dengeki Sakusen (Japan) (Rev A) [T-Kor v1.0.1].md', 'Advanced Daisenryaku (Kor v1.0.1)', '어드밴스드 대전략 한글 v1.0.1'),
 ('md_contracorps', 'Advanced Daisenryaku - Deutsch Dengeki Sakusen (Japan) (Rev A) [T-Kor v1.0.2 Mod].md', 'Advanced Daisenryaku (Kor v1.0.2 Mod)', '어드밴스드 대전략 한글 v1.0.2 Mod'),
 ('md_teenagemuwux', 'Monsterwold4_kor.md', 'Monster World 4 (Kor)', '몬스터월드4 한글'),
 ('md_strider2u', 'Monsterwold4_kor_gold.md', 'Monster World 4 (Kor Gold)', '몬스터월드4 한글 골드'),
 ('md_battletoadsdwux', 'Sangokushi_Retsuden_Korean_v18.bin', 'Sangokushi Retsuden (Kor v18)', '삼국지열전 한글 v18'),
 ('md_elemast', 'mw3rev_ko.md', 'Monster World 3 Rev (Kor)', '몬스터월드3 Rev 한글'),
 ('md_raidenwux', 'sam ziyun_kor.md', 'Sam Ziyun (Kor)', 'Sam Ziyun 한글'),
]
g = open(GL, 'rb').read(); n = bytearray(open(SRC_NAME, 'rb').read())
idx = collections.defaultdict(list)
for i in range(9800):
    idx[g[224+i*112+4:224+i*112+40].split(b'\0')[0].decode('latin1')].append(i)
os.makedirs(BK, exist_ok=True)
def u32(s, m): return s[:m].encode('utf-32le')
report = []
for rom, src, eng, kor in games:
    # 1. back up originals
    for p in (os.path.join(CARD,'roms',rom+'.zip'), os.path.join(CARD,'movies',rom+'.avi')):
        b = os.path.join(BK, os.path.basename(p))
        if os.path.exists(p) and not os.path.exists(b): shutil.copy2(p, b)
    # 2. new zip with our rom
    inner = re.sub(r'[^A-Za-z0-9_.-]', '_', os.path.splitext(os.path.basename(src))[0]) + '.md'
    zp = os.path.join(CARD,'roms',rom+'.zip')
    with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z: z.write(os.path.join(ROMDIR, src), inner)
    # 3. patch name records
    for i in idx[rom]:
        base = i * R
        n[base:base+R] = bytes(R)
        def put(slot, data): n[base+slot*64: base+slot*64+len(data)] = data
        put(0, u32(kor, 16)); put(2, rom[3:].upper().encode()[:60]); put(3, u32(kor, 16))
        put(13, eng.encode('ascii')[:63]); put(14, u32(kor, 64))
    # 4. preview video named by the stock rom
    vf = ("drawtext=fontfile='C\:/Windows/Fonts/malgunbd.ttf':text='MEGA DRIVE':fontcolor=0x66aaff:fontsize=24:x=(w-text_w)/2:y=60,"
          f"drawtext=fontfile='C\:/Windows/Fonts/malgunbd.ttf':text='{kor}':fontcolor=white:fontsize=40:x=(w-text_w)/2:y=h/2-30")
    subprocess.run([FF, '-y', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=0x101830:s=640x480:r=30:d=6.5', '-vf', vf,
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-b:v', '600k', '-an', os.path.join(CARD,'movies',rom+'.avi')], check=True)
    report.append((rom, [i+1 for i in idx[rom]], kor, os.path.getsize(zp)))
open(OUT_NAME, 'wb').write(n)
for r in report: print(r)
print('name.bin size', len(n))
