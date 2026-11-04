r"""Screen frames ("bezels") for MinosFront / RetroArch overlays.

  python make_bezels.py F:

Writes <card>/pandory/<style>/bezel_<w>_<h>.png (1280x720, transparent window) and bezel_<w>_<h>.cfg for the aspect ratios 4:3, 3:4 (vertical arcade),
3:2 (GBA), 10:9 (GB/GBC) and 5:4.  Styles (folder): bezel (neon), bezel_plain, bezel_cabinet (90s arcade cabinet side art + chrome T-molding),
bezel_kor (stickers with the nicknames of the pirated Korean arcade titles), bezel_memory (sunburst machine side with price list and paper notes, synthwave grid side), bezel_arcade (two lit arcade machines with attract text, CRT-style frame, warning sticker, 100 won display).
MinosFront turns one on when a game runs at its own ratio ("original") and sets RetroArch to exactly that ratio, so the picture fills the window.
Only the side panels are drawn; the overlay is one static PNG, so it costs the CPU nothing.  All art is original (no game characters or logos)."""
import os, random, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1280, 720
RATIOS = {"4_3": 4 / 3, "3_4": 3 / 4, "3_2": 3 / 2, "10_9": 10 / 9, "5_4": 5 / 4}
FONT = r"C:\Windows\Fonts\malgunbd.ttf"
TITLES = ["독수리오형제", "보글보글", "스파2", "갤러그", "너구리", "1942", "100원", "신나는 오락실", "게임 오버?", "1P 2P", "콘티뉴", "고수 등장"]
STICK = [(255, 214, 10), (255, 80, 120), (60, 220, 255), (120, 255, 120), (255, 150, 40), (200, 120, 255)]


def font(sz):
    try:
        return ImageFont.truetype(FONT, sz)
    except Exception:
        return ImageFont.load_default()


def finish(img, x0, ww, r=22):
    mask = Image.new("L", (W, H), 255)
    ImageDraw.Draw(mask).rounded_rectangle((x0 + 4, 4, x0 + ww - 4, H - 4), r, fill=0)      # the window: the picture shows through
    img.putalpha(mask)
    return img


def plain(x0, ww):
    img = Image.new("RGBA", (W, H), (14, 14, 18, 255)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((x0 + 1, -4, x0 + ww - 1, H + 4), 22, outline=(70, 70, 82, 255), width=2)
    return finish(img, x0, ww, 18)


def neon(x0, ww):
    img = Image.new("RGBA", (W, H)); px = img.load()
    for y in range(H):                                              # night-purple background with a soft vertical gradient
        for x in range(W):
            t = y / H; s = abs(x - W / 2) / (W / 2)
            px[x, y] = (int(10 + 10 * t + 8 * s), int(6 + 4 * t), int(24 + 22 * s + 10 * t), 255)
    stripes = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(stripes)
    for x in range(0, W, 8):
        sd.line([(x, 0), (x, H)], fill=(255, 255, 255, 7))
    img = Image.alpha_composite(img, stripes)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle((x0 - 3, -6, x0 + ww + 3, H + 6), 30, outline=(255, 70, 170, 255), width=7)
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(9)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((x0 - 2, -4, x0 + ww + 2, H + 4), 26, outline=(255, 90, 180, 255), width=3)
    d.rounded_rectangle((x0 + 2, 0, x0 + ww - 2, H), 24, outline=(70, 220, 255, 230), width=2)
    if x0 > 60:
        for cx in (x0 // 2, W - x0 // 2):
            for k in range(6):
                cy = 70 + k * 116; d.ellipse((cx - 5, cy - 5, cx + 5, cy + 5), fill=(255, 210, 80, 200))
    return finish(img, x0, ww)


def molding(img, x0, ww, col=(190, 196, 206)):
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((x0 - 6, -8, x0 + ww + 6, H + 8), 28, outline=(60, 62, 70, 255), width=3)
    d.rounded_rectangle((x0 - 3, -6, x0 + ww + 3, H + 6), 26, outline=col, width=5)          # chrome T-molding
    d.rounded_rectangle((x0 + 1, -2, x0 + ww - 1, H + 2), 24, outline=(30, 30, 36, 255), width=3)


def cabinet(x0, ww):
    rnd = random.Random(7)
    img = Image.new("RGBA", (W, H), (22, 22, 26, 255)); px = img.load()
    for y in range(H):
        for x in range(W):                                           # black laminate with fine grain
            v = rnd.randint(-5, 5); b = 22 + v; px[x, y] = (b, b, b + 4, 255)
    side = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(side)
    for left in (True, False):                                       # 90s side art: three slanted racing stripes
        xs = 0 if left else W - x0
        cols = [(230, 40, 40), (255, 150, 20), (255, 225, 60)]
        for i, c in enumerate(cols):
            o = i * 26
            pts = [(xs, 560 - o), (xs + x0, 420 - o), (xs + x0, 470 - o), (xs, 610 - o)] if left else [(xs, 420 - o), (xs + x0, 560 - o), (xs + x0, 610 - o), (xs, 470 - o)]
            sd.polygon(pts, fill=c + (255,))
    img = Image.alpha_composite(img, side)
    d = ImageDraw.Draw(img)
    if x0 >= 110:
        for left in (True, False):                                   # coin-door style bits: two coin slots + a lamp
            cx = x0 // 2 if left else W - x0 // 2
            f = font(max(14, min(24, x0 // 9)))
            d.text((cx, 60), "1UP" if left else "2UP", font=f, fill=(255, 225, 60, 255), anchor="mm")
            for dy in (0, 54):
                d.rounded_rectangle((cx - 16, 100 + dy, cx + 16, 140 + dy), 6, fill=(8, 8, 10, 255), outline=(170, 175, 185, 255), width=3)
                d.line([(cx, 108 + dy), (cx, 132 + dy)], fill=(255, 70, 50, 255), width=3)
            d.ellipse((cx - 9, 230, cx + 9, 248), fill=(255, 70, 50, 255), outline=(255, 210, 200, 255), width=2)
    molding(img, x0, ww)
    return finish(img, x0, ww)


def sticker(text, col, sz, rot, rnd):
    f = font(sz); tw = int(f.getlength(text)) + 22; th = int(sz * 1.45)
    st = Image.new("RGBA", (tw + 8, th + 8), (0, 0, 0, 0)); d = ImageDraw.Draw(st)
    d.rounded_rectangle((4, 4, tw + 3, th + 3), 10, fill=col + (255,), outline=(255, 255, 255, 255), width=3)
    dark = (20, 16, 30, 255)
    d.text((tw // 2 + 4, th // 2 + 4), text, font=f, fill=dark, anchor="mm")
    return st.rotate(rot, expand=True, resample=Image.BICUBIC)


def kor(x0, ww):
    rnd = random.Random(11)
    img = Image.new("RGBA", (W, H), (16, 14, 40, 255)); d = ImageDraw.Draw(img)
    for y in range(0, H, 14):                                        # halftone dots, like a cheap poster
        for x in range(0, W, 14):
            d.ellipse((x, y, x + 4, y + 4), fill=(40, 34, 90, 255))
    for left in (True, False):
        xs = 0 if left else W - x0; cx = xs + x0 // 2
        n = 5 if x0 < 140 else 6 if x0 < 250 else 8
        gap = H / n; k = rnd.randint(0, len(TITLES) - 1)
        for i in range(n):
            t = TITLES[(k + i * 5 + (0 if left else 3)) % len(TITLES)]
            sz = 40
            while sz > 12 and font(sz).getlength(t) + 30 > (x0 - 14) / 0.97: sz -= 2
            sz = min(sz, 46)
            st = sticker(t, STICK[(i + (0 if left else 2)) % len(STICK)], sz, rnd.choice([-9, -5, 5, 9]), rnd)
            img.alpha_composite(st, (max(0, int(cx - st.width / 2)), int(gap * i + gap / 2 - st.height / 2)))
    molding(img, x0, ww, (255, 214, 10))
    return finish(img, x0, ww)


IMPACT = r"C:\Windows\Fonts\impact.ttf"


def font2(sz, path=IMPACT):
    try:
        return ImageFont.truetype(path, sz)
    except Exception:
        return font(sz)


def bolt(d, x, y, h, w, col):
    pts = [(x, y), (x - w * .35, y + h * .38), (x + w * .05, y + h * .38), (x - w * .5, y + h), (x + w * .45, y + h * .5), (x, y + h * .5), (x + w * .5, y)]
    d.polygon(pts, fill=col)


def cabinet_front(img, xs, w, left):
    """an arcade machine seen from the front: lit marquee, screen with attract text, joystick panel, coin door, warning sticker, 100 won display"""
    cw = int(min(w - 14, 240)); cx = xs + w // 2; X0 = cx - cw // 2; X1 = cx + cw // 2
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0)); g = ImageDraw.Draw(glow)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((X0, -20, X1, H + 20), 14, fill=(22, 24, 42, 255), outline=(210, 45, 80, 255), width=4)
    d.rectangle((X0 + 3, 0, X0 + 7, H), fill=(40, 44, 80, 255))
    sc = cw / 240.0
    # marquee
    d.rounded_rectangle((X0 + 8, 16, X1 - 8, 92), 8, fill=(14, 8, 30, 255), outline=(255, 70, 100, 255), width=3)
    g.rounded_rectangle((X0 + 8, 16, X1 - 8, 92), 8, outline=(255, 70, 100, 255), width=6)
    t1, t2 = ("AMUSEMENT", "ARCADE") if left else ("ARCADE", "CHAMPION")
    f = font2(max(12, int(30 * sc)))
    for i, (t, col) in enumerate(((t1, (255, 210, 60, 255)), (t2, (90, 230, 255, 255)))):
        yy = 38 + i * 30 * max(.6, sc)
        d.text((cx, yy), t, font=f, fill=col, anchor="mm"); g.text((cx, yy), t, font=f, fill=col, anchor="mm")
    # monitor
    d.rounded_rectangle((X0 + 12, 108, X1 - 12, 332), 12, fill=(8, 8, 12, 255), outline=(70, 74, 100, 255), width=3)
    d.rounded_rectangle((X0 + 24, 122, X1 - 24, 318), 6, fill=(6, 12, 40, 255))
    fa, fb = font2(max(11, int(24 * sc))), font2(max(10, int(21 * sc)))
    if left:
        lines = [("INSERT COIN", (255, 150, 40, 255), fa, 150), ("1P PLAY", (80, 210, 255, 255), fb, 215), ("2P PLAY", (80, 210, 255, 255), fb, 245)]
    else:
        lines = [("GAME", (255, 190, 40, 255), fa, 150), ("START!", (255, 190, 40, 255), fa, 182), ("1P PLAY", (80, 210, 255, 255), fb, 235), ("2P PLAY", (80, 210, 255, 255), fb, 262)]
    for t, c, fo, y in lines:
        d.text((cx, y), t, font=fo, fill=c, anchor="mm"); g.text((cx, y), t, font=fo, fill=c, anchor="mm")
    d.text((cx + cw * .22, 303), "CREDIT 00", font=font2(max(9, int(13 * sc))), fill=(190, 220, 255, 255), anchor="mm")
    # control panel with joystick and buttons
    d.polygon([(X0 + 8, 346), (X1 - 8, 346), (X1 + 2, 428), (X0 - 2, 428)], fill=(54, 56, 72, 255), outline=(150, 155, 175, 255))
    jx = cx - cw * .26
    d.rectangle((jx - 3, 372, jx + 3, 392), fill=(170, 170, 180, 255)); d.ellipse((jx - 11, 360, jx + 11, 382), fill=(225, 40, 50, 255), outline=(255, 150, 150, 255))
    for i, c in enumerate(((60, 130, 255), (60, 130, 255), (255, 60, 60), (60, 130, 255), (60, 130, 255), (255, 60, 60))):
        bx = cx + cw * .05 + (i % 3) * cw * .15; by = 372 + (i // 3) * 22
        d.ellipse((bx - 8, by - 8, bx + 8, by + 8), fill=c + (255,), outline=(235, 235, 245, 255))
    # coin door
    d.rectangle((X0 + 10, 440, X1 - 10, 548), fill=(10, 10, 14, 255), outline=(72, 74, 90, 255), width=2)
    for dx in (-cw * .2, cw * .08):
        box = (cx + dx, 458, cx + dx + cw * .12, 486)
        d.rectangle(box, fill=(255, 45, 45, 255)); g.rectangle(box, fill=(255, 45, 45, 255))
        d.rectangle((cx + dx, 508, cx + dx + cw * .12, 536), fill=(24, 24, 30, 255), outline=(110, 112, 128, 255))
    # warning sticker
    d.rectangle((X0 + 8, 562, X1 - 8, 626), fill=(238, 228, 196, 255), outline=(50, 40, 30, 255), width=2)
    d.rectangle((X0 + 8, 562, X1 - 8, 580), fill=(30, 26, 22, 255))
    if cw >= 140:
        fs = font(max(11, int(15 * sc)))
        d.text((cx, 571), "! 경고", font=fs, fill=(255, 214, 10, 255), anchor="mm")
        d.text((cx, 595), "과도한 게임은", font=fs, fill=(30, 26, 22, 255), anchor="mm")
        d.text((cx, 614), "건강에 해롭습니다", font=fs, fill=(30, 26, 22, 255), anchor="mm")
    else:
        d.polygon([(cx, 565), (cx - 6, 577), (cx + 6, 577)], fill=(255, 214, 10, 255))
        for yy in (594, 604, 614):
            d.line([(X0 + 16, yy), (X1 - 16, yy)], fill=(80, 70, 60, 255), width=2)
    # 100 won LED display
    d.rectangle((X0 + 8, 640, X1 - 8, 706), fill=(32, 5, 8, 255), outline=(210, 45, 55, 255), width=3)
    f1 = font(max(14, int(30 * sc))); f2 = font2(max(9, int(15 * sc)))
    d.text((cx, 663), "100원", font=f1, fill=(255, 70, 60, 255), anchor="mm"); g.text((cx, 663), "100원", font=f1, fill=(255, 70, 60, 255), anchor="mm")
    d.text((cx, 692), "INSERT COIN", font=f2, fill=(255, 120, 100, 255), anchor="mm")
    return glow


def arcade(x0, ww):
    img = Image.new("RGBA", (W, H)); px = img.load()
    for y in range(H):                                              # blue-violet night wall
        t = y / H
        for x in range(W):
            px[x, y] = (int(14 + 18 * t), int(14 + 6 * t), int(52 + 22 * (1 - t)), 255)
    bl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); b = ImageDraw.Draw(bl)
    for left in (True, False):                                      # yellow lightning bolts and red flames behind the machines
        xs = 0 if left else W - x0
        for fx, fy, fh, fw in ((.18, 40, 300, 90), (.8, 250, 360, 110), (.45, 420, 260, 70)):
            bolt(b, xs + x0 * fx, fy, fh, fw, (255, 214, 40, 235))
        for i in range(5):
            fx = xs + x0 * (.1 + .2 * i); fh = 70 + (i * 37 % 60)
            b.polygon([(fx - 16, H), (fx, H - fh - 40), (fx + 18, H)], fill=(255, 90, 30, 190))
    img = Image.alpha_composite(img, bl.filter(ImageFilter.GaussianBlur(1.5)))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for left in (True, False):
        xs = 0 if left else W - x0
        glow = Image.alpha_composite(glow, cabinet_front(img, xs, x0, left))
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(6)))
    d = ImageDraw.Draw(img)
    for i in range(22):                                              # dark CRT plastic frame around the picture, bevelled
        c = int(8 + (22 - i) * 2.6); d.rounded_rectangle((x0 - 22 + i, -30 + i, x0 + ww + 22 - i, H + 30 - i), 30, outline=(c, c, c + 4, 255), width=1)
    d.rounded_rectangle((x0 - 1, -4, x0 + ww + 1, H + 4), 24, outline=(100, 104, 116, 255), width=2)
    return finish(img, x0, ww)


PIXEL = r"C:\Windows\Fonts\consolab.ttf"


def fit(text, maxw, start, path=FONT):
    sz = start
    while sz > 9 and ImageFont.truetype(path, sz).getlength(text) > maxw:
        sz -= 1
    return ImageFont.truetype(path, sz)


def paper(img, cx, cy, w, h, lines, fill, fg, rot, border=(60, 50, 40, 255), fs=20, path=FONT):
    st = Image.new("RGBA", (w + 8, h + 8), (0, 0, 0, 0)); d = ImageDraw.Draw(st)
    d.rectangle((4, 4, w + 3, h + 3), fill=fill, outline=border, width=3)
    n = len(lines)
    for i, t in enumerate(lines):
        d.text((w // 2 + 4, 4 + h * (i + .5) / n), t, font=fit(t, w - 14, fs, path), fill=fg, anchor="mm")
    st = st.rotate(rot, expand=True, resample=Image.BICUBIC)
    img.alpha_composite(st, (max(0, int(cx - st.width / 2)), max(0, int(cy - st.height / 2))))


SHIP = ["......##......", ".....####.....", "..rr######rr..", "##############", "#r##########r#", "..##..##..##..", "..r...rr...r.."]
ALIEN = ["..yy...", ".yyyy..", "..yy...", ".rrrr..", "r.rr.r.", "..rr...", ".r..r.."]
PCOL = {"#": (170, 180, 200, 255), "r": (230, 60, 50, 255), "y": (255, 214, 60, 255)}


def sprite(d, rows, x, y, k):
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch in PCOL:
                d.rectangle((x + i * k, y + j * k, x + (i + 1) * k - 1, y + (j + 1) * k - 1), fill=PCOL[ch])


def mem_left(img, xs, w):
    d = ImageDraw.Draw(img); cx = xs + w // 2
    pw = int(min(w - 14, 230)); P0 = cx - pw // 2; P1 = cx + pw // 2; sc = pw / 200.0
    pts = [(cx, 330)]
    cols = [(224, 52, 40, 255), (250, 204, 50, 255), (40, 72, 170, 255)]
    n = 18
    import math
    for i in range(n):                                               # sunburst rays red / yellow / blue
        a0 = 2 * math.pi * i / n; a1 = 2 * math.pi * (i + 1) / n
        d.polygon([(cx, 330), (cx + math.cos(a0) * 900, 330 + math.sin(a0) * 900), (cx + math.cos(a1) * 900, 330 + math.sin(a1) * 900)], fill=cols[i % 3])
    d.rectangle((xs, 0, xs + 3, H), fill=(20, 16, 14, 255)); d.rectangle((xs + w - 3, 0, xs + w, H), fill=(20, 16, 14, 255))
    # game screen with pixel ship, alien and the price list
    d.rounded_rectangle((P0, 18, P1, 238), 14, fill=(10, 10, 42, 255), outline=(255, 214, 60, 255), width=5)
    k = max(2, int(5 * sc)); sprite(d, SHIP, cx - 7 * k - int(14 * sc), 44, k); sprite(d, ALIEN, cx + int(22 * sc), 62, k)
    for i, (t, y) in enumerate((("INSERT COIN", 168), ("1 PLAY  50원", 194), ("1 PLAY 100원", 218))):
        d.text((cx, y), t, font=fit(t, pw - 28, 24 if i == 0 else 20), fill=(255, 215, 110, 255), anchor="mm")
    d.rounded_rectangle((P0, 250, P1, 330), 8, fill=(8, 8, 8, 255), outline=(240, 240, 240, 255), width=3)
    d.text((cx, 276), "INSERT COIN", font=fit("INSERT COIN", pw - 24, 26, PIXEL), fill=(245, 245, 245, 255), anchor="mm")
    f1 = fit("1P / 2P", pw - 60, 32, PIXEL); tw = f1.getlength("1P / 2P"); x = cx - tw / 2
    d.text((x, 308), "1P", font=f1, fill=(230, 60, 60, 255), anchor="lm"); x += f1.getlength("1P ")
    d.text((x, 308), "/", font=f1, fill=(245, 245, 245, 255), anchor="lm"); x += f1.getlength("/ ")
    d.text((x, 308), "2P", font=f1, fill=(70, 120, 255, 255), anchor="lm")
    paper(img, cx, 392, pw - 14, 84, ["과도한 오락은", "청소년의 정서에", "해롭습니다"], (240, 228, 196, 255), (30, 24, 20, 255), -3, fs=19)
    paper(img, cx + pw * .12, 462, int(pw * .6), 54, ["19세 미만", "출입금지"], (246, 236, 208, 255), (190, 30, 30, 255), 2, border=(190, 30, 30, 255), fs=19)
    # joystick and buttons in the corner
    d.polygon([(xs, 590), (xs + w * .75, 640), (xs + w * .75, H), (xs, H)], fill=(60, 60, 66, 255), outline=(20, 20, 20, 255))
    jx = P0 + pw * .22; d.ellipse((jx - 20, 662, jx + 20, 690), fill=(30, 30, 34, 255)); d.rectangle((jx - 4, 612, jx + 4, 672), fill=(190, 190, 200, 255))
    d.ellipse((jx - 20, 580, jx + 20, 620), fill=(205, 45, 45, 255), outline=(255, 150, 150, 255), width=2)
    d.ellipse((P0 + pw * .38, 654, P0 + pw * .38 + 40, 694), fill=(215, 50, 45, 255), outline=(255, 190, 180, 255), width=2)
    d.ellipse((P0 + pw * .66, 618, P0 + pw * .66 + 40, 658), fill=(50, 90, 220, 255), outline=(190, 210, 255, 255), width=2)


def mem_right(img, xs, w):
    d = ImageDraw.Draw(img); cx = xs + w // 2
    pw = int(min(w - 14, 230)); P0 = cx - pw // 2; P1 = cx + pw // 2; sc = pw / 200.0
    d.rectangle((xs, 0, xs + w, H), fill=(12, 10, 36, 255))
    for i in range(-8, 14):                                          # diagonal stripes at the top
        c = ((255, 150, 40), (60, 210, 255), (200, 80, 255), (255, 214, 60))[i % 4]
        d.line([(xs + i * 26, 160), (xs + i * 26 + 200, -40)], fill=c + (255,), width=7)
    d.rectangle((xs, 150, xs + w, 168), fill=(12, 10, 36, 255))
    mz = [(P0 + 50 * sc, 20), (P1 - 20, 20), (P1 - 20, 90), (P1 - 60 * sc, 90), (P1 - 60 * sc, 50), (P0 + 90 * sc, 50), (P0 + 90 * sc, 110)]
    d.line(mz, fill=(255, 70, 140, 255), width=4)
    for yy in range(330, H, 1):                                      # synthwave grid in the lower part
        pass
    for i in range(12):
        y = 330 + int((i / 11.0) ** 2 * (H - 330)); d.line([(xs, y), (xs + w, y)], fill=(60, 210, 255, 255) if i % 2 else (255, 70, 160, 255), width=2)
    for i in range(-8, 9):
        d.line([(cx + i * 6, 330), (cx + i * w / 8.0, H)], fill=(255, 70, 160, 255) if i % 2 else (60, 210, 255, 255), width=2)
    d.rectangle((xs, 330, xs + w, 342), fill=(12, 10, 36, 255))
    d.rectangle((P0, 175, P1, 315), fill=(6, 6, 10, 255), outline=(60, 210, 255, 255), width=3)
    for yy in range(185, 310, 14): d.line([(P0 + 4, yy), (P1 - 4, yy)], fill=(20, 60, 90, 255), width=1)
    for t, y, c, sz in (("HIGH SCORE", 200, (225, 50, 50, 255), 25), ("CREDIT 00", 245, (245, 245, 245, 255), 26), ("GAME OVER", 288, (255, 150, 40, 255), 26)):
        d.text((cx, y), t, font=fit(t, pw - 22, sz, PIXEL), fill=c, anchor="mm")
    paper(img, cx - pw * .05, 358, int(pw * .55), 36, ["우수업소"], (240, 228, 196, 255), (30, 24, 20, 255), -4, fs=22)
    paper(img, cx + pw * .04, 408, int(pw * .86), 40, ["보물섬 오락실"], (240, 228, 196, 255), (30, 24, 20, 255), 2, fs=24)
    paper(img, cx, 462, int(pw * .88), 46, ["은하 오락실"], (36, 70, 170, 255), (245, 245, 250, 255), -2, border=(235, 235, 245, 255), fs=26)
    # coin slot plate
    px0 = P1 - 80
    d.rounded_rectangle((px0, 600, P1, 706), 6, fill=(150, 152, 160, 255), outline=(60, 60, 66, 255), width=3)
    d.rounded_rectangle((px0 + 28, 620, px0 + 50, 660), 6, fill=(20, 20, 24, 255), outline=(220, 220, 228, 255), width=2)
    d.rectangle((px0 + 12, 672, P1 - 12, 694), fill=(235, 235, 240, 255), outline=(40, 40, 46, 255)); d.text(((px0 + P1) / 2, 683), "100원", font=font(14), fill=(30, 30, 34, 255), anchor="mm")


def memory(x0, ww):
    img = Image.new("RGBA", (W, H), (18, 15, 14, 255))
    for fn, xs, bx in ((mem_left, 0, 0), (mem_right, W - x0 + 24, W - x0)):
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); fn(layer, xs, x0 - 24)                 # drawn on its own layer, then cut to the panel
        img.alpha_composite(layer.crop((bx, 0, bx + x0, H)), (bx, 0))
    d = ImageDraw.Draw(img)
    for i in range(22):                                              # dark CRT plastic frame around the picture, bevelled
        c = int(8 + (22 - i) * 2.8); d.rounded_rectangle((x0 - 22 + i, -30 + i, x0 + ww + 22 - i, H + 30 - i), 30, outline=(c, c, c, 255), width=1)
    d.rounded_rectangle((x0 - 1, -4, x0 + ww + 1, H + 4), 24, outline=(110, 110, 118, 255), width=2)
    return finish(img, x0, ww)


STYLES = {"bezel": neon, "bezel_plain": plain, "bezel_cabinet": cabinet, "bezel_kor": kor, "bezel_arcade": arcade, "bezel_memory": memory}


def main(card):
    nl = chr(10)
    for sub, fn in STYLES.items():
        out = os.path.join(card, "pandory", sub); os.makedirs(out, exist_ok=True)
        for key, r in RATIOS.items():
            ww = int(round(H * r)); x0 = (W - ww) // 2
            fn(x0, ww).save(os.path.join(out, "bezel_%s.png" % key), optimize=True)
            open(os.path.join(out, "bezel_%s.cfg" % key), "w", newline=nl).write(nl.join(["overlays = 1", 'overlay0_overlay = "bezel_%s.png"' % key, "overlay0_full_screen = true", "overlay0_descs = 0"]) + nl)
        print(sub, "done")


if __name__ == "__main__":
    main((sys.argv[1] if len(sys.argv) > 1 else "F:").rstrip(chr(92) + "/") + os.sep)
