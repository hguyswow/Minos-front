import sys,struct; sys.path.insert(0,r'D:\Backup\tools')
from gm import *
from capstone import *
from capstone.arm import *
T0,TOFF,TSZ=0x150d0,0x60d0,0x33c08
code=d[TOFF:TOFF+TSZ]
def cstr(v):
    o=va2off(v)
    if o is None: return None
    s=d[o:o+60].split(b'\0')[0]
    return s.decode('latin1') if len(s)>2 and all(32<=c<127 for c in s) else None
def run(start,end):
    md=Cs(CS_ARCH_ARM,CS_MODE_ARM); md.detail=True; md.skipdata=True
    regs={}
    for i in md.disasm(code[start-T0:end-T0],start):
        note=''
        ops=i.operands
        try:
            if i.mnemonic=='ldr' and ops[1].type==ARM_OP_MEM and ops[1].mem.base==ARM_REG_PC:
                v=struct.unpack_from('<I',d,va2off(i.address+8+ops[1].mem.disp))[0]; regs[ops[0].reg]=v; note=f'; lit {v:#x}'
            elif i.mnemonic=='movw': regs[ops[0].reg]=ops[1].imm&0xffff
            elif i.mnemonic=='movt':
                v=(regs.get(ops[0].reg,0)&0xffff)|(ops[1].imm<<16); regs[ops[0].reg]=v; note=f'; const {v:#x}'
            elif i.mnemonic=='add' and len(ops)==3 and ops[1].type==ARM_OP_REG and ops[1].reg==ARM_REG_PC and ops[2].type==ARM_OP_REG:
                p=regs.get(ops[2].reg)
                if p is not None:
                    t=(p+i.address+8)&0xffffffff; s=cstr(t); note=f'; ={t:#x} "{s}"' if s else f'; ={t:#x}'
        except Exception: pass
        print(f'{i.address:x}: {i.mnemonic:8s} {i.op_str} {note}')
if __name__=='__main__':
    run(int(sys.argv[1],16),int(sys.argv[2],16))
