"""Finds the code that uses a string of the Pandory executable and prints the instructions around it.
  python pandory_xref.py F:/pandory/pandory 0xe9f2c        (file offset of the string, e.g. from  strings -t x)
"""
import struct, sys
from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM, CS_MODE_THUMB

path, soff = sys.argv[1], int(sys.argv[2], 0)
d = open(path, "rb").read()
phoff, = struct.unpack_from("<I", d, 0x1C); phentsize, phnum = struct.unpack_from("<HH", d, 0x2A)
segs = []
for i in range(phnum):
    t, off, va, pa, fs, ms, fl, al = struct.unpack_from("<IIIIIIII", d, phoff + i * phentsize)
    if t == 1:
        segs.append((off, va, fs, fl))


def off2va(o):
    for off, va, fs, fl in segs:
        if off <= o < off + fs:
            return va + o - off


va = off2va(soff)
print("string offset 0x%x -> vaddr 0x%x : %r" % (soff, va, d[soff:soff + 40].split(b"\0")[0]))
# executable segment
for off, vaa, fs, fl in segs:
    if fl & 1:
        code, base = d[off:off + fs], vaa
        break
hits = []
for i in range(0, len(code) - 3, 4):                         # literal pool words and PC-relative loads
    if struct.unpack_from("<I", code, i)[0] == va:
        hits.append(base + i)
rel = [h for h in hits]
print("literal words pointing at it:", [hex(h) for h in rel])
for mode, name in ((CS_MODE_THUMB, "thumb"),):
    md = Cs(CS_ARCH_ARM, mode)
    for h in rel[:4]:
        # find the instruction that loads this literal: scan back up to 400 bytes for 'ldr rX, [pc, #n]' reaching h
        start = max(base, h - 600)
        ins = list(md.disasm(code[start - base:h - base], start))
        users = [x for x in ins if x.mnemonic.startswith("ldr") and "pc" in x.op_str]
        for u in users:
            try:
                disp = int(u.op_str.split("#")[1].rstrip("]"), 0)
            except Exception:
                continue
            if ((u.address + 4) & ~3) + disp == h:
                print("\nloaded at 0x%x (%s): %s %s" % (u.address, name, u.mnemonic, u.op_str))
                a0 = u.address - 24
                for x in md.disasm(code[a0 - base:a0 - base + 120], a0):
                    print("   0x%x: %-8s %s" % (x.address, x.mnemonic, x.op_str))

# position independent code: "ldr rX, [pc, #n]" loads (string - pc), then "add rX, pc"
print("\nPC-relative search")
found = []
for i in range(0, len(code) - 3, 4):
    w = struct.unpack_from("<I", code, i)[0]
    pc = (va - w) & 0xFFFFFFFF
    a = pc - 4                                              # address of the 'add rX, pc' instruction
    if base <= a < base + len(code) - 2:
        hw = struct.unpack_from("<H", code, a - base)[0]
        if (hw & 0xFF78) == 0x4478:
            found.append((base + i, a))
print([(hex(l), hex(a)) for l, a in found])
md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
for lit, a in found[:3]:
    s0 = a - 40
    print("\n-- around add at 0x%x (literal at 0x%x)" % (a, lit))
    for x in md.disasm(code[s0 - base:s0 - base + 200], s0):
        print("   0x%x: %-8s %s" % (x.address, x.mnemonic, x.op_str))
