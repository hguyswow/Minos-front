r"""Replaces the loud original boot opening (demo*.avi on the card) with a quiet MinosFront opening.

  python make_boot_video.py F:                 (needs ffmpeg on PATH; frames from `MINOS_SPLASH=seq` into C:\dev\seq, see docs)
The originals are copied to <card>\demo_original\ first; copy them back to undo.
Video: XVID + MP3 like the originals, one soft coin chime instead of music.
"""
import os, shutil, subprocess, sys

card = (sys.argv[1] if len(sys.argv) > 1 else "F:").rstrip("\/") + "\\"
seq = sys.argv[2] if len(sys.argv) > 2 else r"C:\dev\seq"
SIZES = {"demo.avi": (1280, 720), "demo_1024x600.avi": (1024, 600), "demo_640x480.avi": (640, 480), "demo_384x224.avi": (384, 224)}
bak = os.path.join(card, "demo_original"); os.makedirs(bak, exist_ok=True)
for n in os.listdir(card):
    if n.startswith("demo") and n.endswith(".avi") and not os.path.exists(os.path.join(bak, n)):
        shutil.copy2(os.path.join(card, n), os.path.join(bak, n))
chime = "aevalsrc='0.22*sin(2*PI*1318*t)*exp(-9*t)*lt(t,0.35)+0.18*sin(2*PI*1975*(t-0.09))*exp(-7*(t-0.09))*gt(t,0.09)*lt(t,0.7)':s=48000:d=0.8,adelay=1300|1300,apad=whole_dur=4.2"
for name, (w, h) in SIZES.items():
    out = os.path.join(card, name)
    cmd = ["ffmpeg", "-y", "-v", "error", "-framerate", "24", "-i", os.path.join(seq, "seq_%04d.bmp"), "-f", "lavfi", "-i", chime,
           "-vf", "tpad=stop_mode=clone:stop_duration=1.0,fade=t=out:st=3.9:d=0.3,scale=%d:%d:flags=lanczos,format=yuv420p" % (w, h),
           "-c:v", "mpeg4", "-vtag", "XVID", "-q:v", "3", "-c:a", "libmp3lame", "-b:a", "96k", "-ac", "2", "-shortest", out]
    subprocess.check_call(cmd)
    print(name, os.path.getsize(out))
    if name == "demo.avi":
        shutil.copy2(out, os.path.join(card, "demo_en.avi"))
    else:
        shutil.copy2(out, os.path.join(card, name.replace("demo", "demo_en")))
