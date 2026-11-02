import struct, re, sys
d=open(r'D:\Backup\firmware_extract\usr\bin\gamemenu','rb').read()
segs=[(0x10000,0x1000,0x3eddc),(0x5ee9c,0x3fe9c,0x868096)]  # (va, off, filesz)
def off2va(o):
    for va,off,sz in segs:
        if off<=o<off+sz: return va+o-off
def va2off(v):
    for va,off,sz in segs:
        if va<=v<va+sz: return off+v-va
def find_str(s):
    r=[]
    for m in re.finditer(re.escape(s),d): r.append(off2va(m.start()))
    return r
