import sys,struct,re; sys.path.insert(0,r'D:\Backup\tools')
from gm import *
from capstone import *
from capstone.arm import *
T0,TOFF,TSZ=0x150d0,0x60d0,0x33c08
code=d[TOFF:TOFF+TSZ]
md=Cs(CS_ARCH_ARM,CS_MODE_THUMB); md.detail=True
ins=list(md.disasm(code,T0))
byaddr={i.address:k for k,i in enumerate(ins)}
def rd32(va):
    o=va2off(va); return struct.unpack_from('<I',d,o)[0] if o is not None else None
xrefs={}  # target -> [addr]
regs={}
for k,i in enumerate(ins):
    m=i.mnemonic
    try:
        ops=i.operands
        if m.startswith('ldr') and len(ops)==2 and ops[1].type==ARM_OP_MEM and ops[1].mem.base==ARM_REG_PC:
            a=((i.address+4)&~3)+ops[1].mem.disp
            v=rd32(a)
            regs[ops[0].reg]=(v,'lit')
        elif m=='movw' and ops[1].type==ARM_OP_IMM:
            regs[ops[0].reg]=(ops[1].imm&0xffff,'movw')
        elif m=='movt' and ops[1].type==ARM_OP_IMM:
            p=regs.get(ops[0].reg)
            lo=p[0] if p and p[1]=='movw' else 0
            regs[ops[0].reg]=(lo|(ops[1].imm<<16),'movwt')
        elif m in ('add','add.w') and len(ops)>=2 and ops[-1].type==ARM_OP_REG and ops[-1].reg==ARM_REG_PC:
            r=ops[0].reg; p=regs.get(r)
            if p: 
                t=(p[0]+i.address+4)&0xffffffff; xrefs.setdefault(t,[]).append(i.address)
        elif m in ('add','add.w') and len(ops)==3 and ops[1].type==ARM_OP_REG and ops[1].reg==ARM_REG_PC and ops[2].type==ARM_OP_REG:
            p=regs.get(ops[2].reg)
            if p: t=(p[0]+i.address+4)&0xffffffff; xrefs.setdefault(t,[]).append(i.address)
        # absolute address constants
        for r,(v,kind) in list(regs.items()):
            pass
        if m.startswith('ldr') and len(ops)==2 and ops[1].type==ARM_OP_MEM and ops[1].mem.base==ARM_REG_PC:
            v=regs[ops[0].reg][0]
            if v: xrefs.setdefault(v,[]).append(i.address)
        if m=='movt':
            v=regs[ops[0].reg][0]; xrefs.setdefault(v,[]).append(i.address)
    except Exception as e:
        pass
import pickle
pickle.dump((xrefs,),open(r'D:\Backup\tools\xrefs.pkl','wb'))
for s in (b'/tmp/addgame_list\x00',b'add_gamecount: %d',b'/user_add.avi',b'cp /udisk/game.txt /data/game.txt'):
    for v in find_str(s):
        print(s,hex(v),[hex(a) for a in xrefs.get(v,[])])
print('instrs',len(ins))
