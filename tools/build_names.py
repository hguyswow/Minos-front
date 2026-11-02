import struct, sys
SRC = r'D:\Backup\firmware_extract\lib\name.bin'
OUT = r'D:\Backup\names_patch\name_ext.bin'
R = 1408
orig = open(SRC, 'rb').read()
assert len(orig) == 9800 * R
entries = [  # (key, english, korean)
 ('XRICK', 'XRick (32X)', 'XRick (32X)'),
 ('CB4K', 'Crazy Balloon 4K', 'Crazy Balloon 4K'),
 ('TTG', 'Tobu Tobu Girl', 'Tobu Tobu Girl'),
 ('INW', 'Inwaders', 'Inwaders'),
 ('ACO', 'SP-Acoman', 'SP-Acoman'),
 ('DUUX', 'Duux', 'Duux'),
 ('UCITY', 'uCity', 'uCity'),
 ('ADV1', 'Advanced Daisenryaku (Kor v1.0.1)', '어드밴스드 대전략 한글 v1.0.1'),
 ('ADV2', 'Advanced Daisenryaku (Kor v1.0.2 Mod)', '어드밴스드 대전략 한글 v1.0.2 Mod'),
 ('BLOW', 'Blowfish', 'Blowfish'),
 ('MW4', 'Monster World 4 (Kor)', '몬스터월드4 한글'),
 ('MW4G', 'Monster World 4 (Kor Gold)', '몬스터월드4 한글 골드'),
 ('SGRL', 'Sangokushi Retsuden (Kor v18)', '삼국지열전 한글 v18'),
 ('MW3', 'Monster World 3 Rev (Kor)', '몬스터월드3 Rev 한글'),
 ('SZY', 'Sam Ziyun (Kor)', 'Sam Ziyun 한글'),
 ('REFL', 'Reflectron', 'Reflectron'),
 ('SANT', 'Santatlantean', 'Santatlantean'),
 ('QUAKE', 'Quake', 'Quake'),
 ('APPLY', 'Apply Names (script)', '이름 적용 (스크립트)'),
 ('REBOOT', 'Reboot (script)', '재부팅 (스크립트)'),
]
def u32(s, maxchars):
    return s[:maxchars].encode('utf-32le')
def rec(key, eng, kor):
    b = bytearray(R)
    def put(slot, data):
        o = slot * 64
        b[o:o + len(data)] = data
    put(0, u32(kor, 16))            # simplified-Chinese slot
    put(2, key.encode('ascii')[:63])  # search key
    put(3, u32(kor, 16))            # traditional-Chinese slot
    put(13, eng.encode('ascii')[:63])  # English
    put(14, u32(kor, 64))           # Korean (slots 14-17)
    return bytes(b)
new = b''.join(rec(*e) for e in entries)
open(OUT, 'wb').write(orig + new)
print('wrote', OUT, len(orig + new), 'records', (len(orig) + len(new)) // R)
