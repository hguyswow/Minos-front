import sys,struct
from capstone import *
f=sys.argv[1]
d=open(f,'rb').read()
shoff=struct.unpack_from('<I',d,0x20)[0]; shentsize,shnum,shstrndx=struct.unpack_from('<HHH',d,0x2e)
secs=[struct.unpack_from('<IIIIIIIIII',d,shoff+i*shentsize) for i in range(shnum)]
def nm(o): s=d[secs[shstrndx][4]+o:]; return s[:s.index(0)].decode()
S={nm(s[0]):s for s in secs}
t=S['.text']; ro=S.get('.rodata')
code=d[t[4]:t[4]+t[5]]
thumb=(struct.unpack_from('<I',d,0x18)[0]&1)==1
print('text',hex(t[3]),'size',t[5],'entry thumb?',thumb)
def cstr(v):
    for n,s in S.items():
        if s[3] and s[3]<=v<s[3]+s[5] and s[1]!=8:
            o=s[4]+v-s[3]; x=d[o:o+80].split(b'\0')[0]
            if len(x)>1 and all(32<=c<127 for c in x): return x.decode()
    return None
md=Cs(CS_ARCH_ARM,CS_MODE_THUMB if thumb else CS_MODE_ARM); md.detail=True; md.skipdata=True
regs={}
for i in md.disasm(code,t[3]):
    note=''
    try:
        if i.mnemonic.startswith('ldr') and 'pc' in i.op_str and '[' in i.op_str:
            import re
            m=re.search(r'#(-?0x[0-9a-f]+|-?\d+)',i.op_str)
            disp=int(m.group(1),0) if m else 0
            base=((i.address+4)&~3) if thumb else i.address+8
            a=base+disp
            for n,s in S.items():
                if s[3] and s[3]<=a<s[3]+s[5] and s[1]!=8:
                    v=struct.unpack_from('<I',d,s[4]+a-s[3])[0]; r=i.op_str.split(',')[0]
                    regs[r]=v; note=f'; lit {v:#x}'
                    break
        if i.mnemonic in('add','add.w') and 'pc' in i.op_str:
            r=i.op_str.split(',')[0]
            if r in regs:
                base=(i.address+4) if thumb else i.address+8
                t2=(regs[r]+base)&0xffffffff; s2=cstr(t2); note=f'; ={t2:#x} "{s2}"' if s2 else f'; ={t2:#x}'
    except Exception as e: pass
    print(f'{i.address:x}: {i.mnemonic} {i.op_str} {note}')
