r"""Screen frames ("bezels") for MinosFront / RetroArch overlays.

  python make_bezels.py F:

Writes <card>/pandory/bezel/bezel_<w>_<h>.png (1280x720, transparent window) and bezel_<w>_<h>.cfg for the aspect ratios 4:3, 3:4 (vertical arcade),
3:2 (GBA), 10:9 (GB/GBC) and 5:4.  MinosFront turns one on when a game runs at its own ratio ("original") and sets RetroArch to exactly that ratio,
so the picture fills the window.  The art is dark on purpose (no burn-in, no distraction)."""
import os, sys
from PIL import Image, ImageDraw, ImageFilter

W, H = 1280, 720
RATIOS = {"4_3": 4 / 3, "3_4": 3 / 4, "3_2": 3 / 2, "10_9": 10 / 9, "5_4": 5 / 4}


def make(key, ratio, plain=False):
    ww = int(round(H * ratio)); x0 = (W - ww) // 2
    if plain:
        img = Image.new("RGBA", (W, H), (14, 14, 18, 255)); d = ImageDraw.Draw(img)
        d.rounded_rectangle((x0 + 1, -4, x0 + ww - 1, H + 4), 22, outline=(70, 70, 82, 255), width=2)
        mask = Image.new("L", (W, H), 255); ImageDraw.Draw(mask).rounded_rectangle((x0 + 4, 4, x0 + ww - 4, H - 4), 18, fill=0); img.putalpha(mask)
        return img, x0, ww
    img = Image.new("RGBA", (W, H))
    px = img.load()
    for y in range(H):                                              # night-purple background with a soft vertical gradient
        for x in range(W):
            t = y / H; s = abs(x - W / 2) / (W / 2)
            px[x, y] = (int(10 + 10 * t + 8 * s), int(6 + 4 * t), int(24 + 22 * s + 10 * t), 255)
    stripes = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(stripes)
    for x in range(0, W, 8):                                        # faint pinstripes like a cabinet panel
        sd.line([(x, 0), (x, H)], fill=(255, 255, 255, 7))
    img = Image.alpha_composite(img, stripes)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0)); g = ImageDraw.Draw(glow)
    box = (x0 - 3, -6, x0 + ww + 3, H + 6)
    g.rounded_rectangle(box, 30, outline=(255, 70, 170, 255), width=7)
    glow = glow.filter(ImageFilter.GaussianBlur(9))
    img = Image.alpha_composite(img, glow)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((x0 - 2, -4, x0 + ww + 2, H + 4), 26, outline=(255, 90, 180, 255), width=3)    # pink line
    d.rounded_rectangle((x0 + 2, 0, x0 + ww - 2, H), 24, outline=(70, 220, 255, 230), width=2)           # cyan line
    for side in (0, 1):                                              # small bulbs on the side panels
        cx = (x0 // 2) if side == 0 else (W - x0 // 2)
        if x0 > 60:
            for k in range(6):
                cy = 70 + k * 116; d.ellipse((cx - 5, cy - 5, cx + 5, cy + 5), fill=(255, 210, 80, 200))
    mask = Image.new("L", (W, H), 255); m = ImageDraw.Draw(mask)
    m.rounded_rectangle((x0 + 4, 4, x0 + ww - 4, H - 4), 22, fill=0)       # the window: the picture shows through, corners rounded
    img.putalpha(mask)
    return img, x0, ww


def main(card):
    for sub, plain in (("bezel", False), ("bezel_plain", True)):
        out = os.path.join(card, "pandory", sub); os.makedirs(out, exist_ok=True)
        for key, r in RATIOS.items():
            img, x0, ww = make(key, r, plain)
            img.save(os.path.join(out, "bezel_%s.png" % key), optimize=True)
            nl = chr(10)
            open(os.path.join(out, "bezel_%s.cfg" % key), "w", newline=nl).write(nl.join(["overlays = 1", 'overlay0_overlay = "bezel_%s.png"' % key, "overlay0_full_screen = true", "overlay0_descs = 0"]) + nl)
            print(sub, key, ww, "wide window at x=%d" % x0)


if __name__ == "__main__":
    main((sys.argv[1] if len(sys.argv) > 1 else "F:").rstrip("\/") + os.sep)
