import sys,struct,re,pickle; sys.path.insert(0,r'D:\Backup\tools')
from gm import *
from capstone import *
from capstone.arm import *
T0,TOFF,TSZ=0x150d0,0x60d0,0x33c08
code=d[TOFF:TOFF+TSZ]
md=Cs(CS_ARCH_ARM,CS_MODE_ARM); md.detail=True; md.skipdata=True
ins=[i for i in md.disasm(code,T0) if i.id!=0]
print('decoded',len(ins))
def rd32(va):
    o=va2off(va); return struct.unpack_from('<I',d,o)[0] if o is not None else None
xrefs={}
regs={}
def addx(t,a): xrefs.setdefault(t&0xffffffff,[]).append(a)
for i in ins:
    m=i.mnemonic; ops=i.operands
    try:
        if m=='ldr' and len(ops)==2 and ops[1].type==ARM_OP_MEM and ops[1].mem.base==ARM_REG_PC:
            a=i.address+8+ops[1].mem.disp
            v=rd32(a)
            if v is not None: regs[ops[0].reg]=v; addx(v,i.address)
        elif m=='movw' and ops[1].type==ARM_OP_IMM:
            regs[ops[0].reg]=ops[1].imm&0xffff
        elif m=='movt' and ops[1].type==ARM_OP_IMM:
            lo=regs.get(ops[0].reg,0)&0xffff; v=lo|(ops[1].imm<<16); regs[ops[0].reg]=v; addx(v,i.address)
        elif m=='add' and len(ops)==3 and ops[1].type==ARM_OP_REG and ops[1].reg==ARM_REG_PC and ops[2].type==ARM_OP_REG:
            p=regs.get(ops[2].reg)
            if p is not None: addx(p+i.address+8,i.address)
        elif m=='add' and len(ops)==3 and ops[2].type==ARM_OP_REG and ops[2].reg==ARM_REG_PC and ops[1].type==ARM_OP_REG:
            p=regs.get(ops[1].reg)
            if p is not None: addx(p+i.address+8,i.address)
    except Exception: pass
pickle.dump(xrefs,open(r'D:\Backup\tools\xrefs.pkl','wb'))
for s in (b'/tmp/addgame_list\x00',b'add_gamecount: %d',b'/user_add.avi',b'cp /udisk/game.txt /data/game.txt',b'/tmp/scangame'):
    for v in find_str(s):
        print(s,hex(v),[hex(a) for a in xrefs.get(v,[])])
