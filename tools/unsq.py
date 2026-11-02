import os, sys
from PySquashfsImage import SquashFsImage

img, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
n = 0
with open(img, 'rb') as f:
    im = SquashFsImage(f)
    for node in im:
        p = node.path.lstrip('/')
        dst = os.path.join(out, p)
        try:
            if node.is_dir:
                os.makedirs(dst, exist_ok=True)
            elif node.is_file:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with open(dst, 'wb') as o:
                    for chunk in node.iter_bytes():
                        o.write(chunk)
                n += 1
        except Exception as e:
            print('skip', p, e)
print('files', n)
