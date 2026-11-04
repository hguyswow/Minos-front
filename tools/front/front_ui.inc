// front_ui.inc - MinosFront v3 screens: system carousel, game list with preview, RetroArch settings entry.
// Included at the end of minosfront.c (uses its globals: R, sys[], nsys, card, text(), video_up/down(), LOG()).
//
// Preview pictures: <card>/pandory/snap/<file name without extension>_1.jpg .. _3.jpg  (made on the PC by tools/build_previews.py
// from the stock preview videos). The three pictures are shown one after another, like a short clip.
//
// Test without the device:  MINOS_SNAP=<dir> SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy minosfront <card>
//   renders the screens with the software renderer and writes BMP files into <dir>.
#include <math.h>

#define STB_IMAGE_IMPLEMENTATION
#define STBI_ONLY_JPEG
#define STBI_NO_STDIO_CALLBACKS
#include "stb_image.h"

typedef SDL_Color Col;
static const Col C_TXT = {236, 240, 250, 255}, C_DIM = {176, 164, 214, 255}, C_ACC = {255, 222, 70, 255}, C_PANEL = {14, 8, 34, 238},
                 C_ROW = {112, 36, 142, 255}, C_LINE = {130, 70, 210, 255}, C_BLACK = {0, 0, 0, 255};

static void fillc(Col c) { SDL_SetRenderDrawBlendMode(R, c.a == 255 ? SDL_BLENDMODE_NONE : SDL_BLENDMODE_BLEND); SDL_SetRenderDrawColor(R, c.r, c.g, c.b, c.a); }
static void rect(int x, int y, int w, int h, Col c) { fillc(c); SDL_Rect q = {x, y, w, h}; SDL_RenderFillRect(R, &q); }
static void rbox(int x, int y, int w, int h, int r, Col c) {      // rounded rectangle
    if (r * 2 > h) r = h / 2; if (r * 2 > w) r = w / 2;
    fillc(c); SDL_Rect m = {x, y + r, w, h - 2 * r}; SDL_RenderFillRect(R, &m);
    for (int i = 0; i < r; i++) {
        float dy = r - i - 0.5f; int dx = r - (int)(sqrtf((float)(r * r) - dy * dy) + 0.5f);
        SDL_Rect t = {x + dx, y + i, w - 2 * dx, 1}, b = {x + dx, y + h - 1 - i, w - 2 * dx, 1};
        SDL_RenderFillRect(R, &t); SDL_RenderFillRect(R, &b);
    }
}
static Col mix(Col a, Col b, float t) { Col c = {(Uint8)(a.r + (b.r - a.r) * t), (Uint8)(a.g + (b.g - a.g) * t), (Uint8)(a.b + (b.b - a.b) * t), (Uint8)(a.a + (b.a - a.a) * t)}; return c; }
static Col alpha(Col c, int a) { c.a = (Uint8)a; return c; }

// text helpers
static void text_fit(const char *t, int x, int y, int size, Col c, int maxw) {   // cuts with ".." when too long
    t = tr(t);
    if (text_w(t, size) <= maxw) { text(t, x, y, size, c, 0); return; }
    char buf[300]; int n = 0; const char *p = t; int w = text_w("..", size);
    while (*p && n < 280) { const char *q = p; int cp = utf8(&q); int cw = glyph(cp, size)->adv; if (w + cw > maxw) break; w += cw; while (p < q && n < 280) buf[n++] = *p++; }
    buf[n] = 0; strcat(buf, ".."); text(buf, x, y, size, c, 0);
}
static void text_c(const char *t, int cx, int y, int size, Col c, int maxw) { int w = text_w(t, size); if (w > maxw) { text_fit(t, cx - maxw / 2, y, size, c, maxw); return; } text(t, cx - w / 2, y, size, c, 0); }
static void text_wrap(const char *t, int x, int y, int size, Col c, int maxw, int maxlines, int lineh) {
    t = tr(t); char line[300]; int n = 0, w = 0, ln = 0; const char *p = t;
    while (*p && ln < maxlines) {
        const char *q = p; int cp = utf8(&q); int cw = glyph(cp, size)->adv;
        if (w + cw > maxw && n > 0) { line[n] = 0; if (ln == maxlines - 1) { text_fit(t + (p - t) - n, x, y + ln * lineh, size, c, maxw); return; } text(line, x, y + ln * lineh, size, c, 0); ln++; n = 0; w = 0; }
        while (p < q && n < 280) line[n++] = *p++; w += cw;
    }
    if (n > 0 && ln < maxlines) { line[n] = 0; text(line, x, y + ln * lineh, size, c, 0); }
}
static void pill(int *x, int y, const char *key, const char *label) {      // "[A] label" footer hint, advances x
    int kw = text_w(key, 20) + 22, lw = text_w(label, 20);
    rbox(*x, y, kw, 32, 8, mix(C_ACC, C_BLACK, 0.55f)); text(key, *x + 11, y + 4, 20, C_ACC, 0);
    text(label, *x + kw + 10, y + 4, 20, C_DIM, 0); *x += kw + 10 + lw + 26;
}
static void chip(int x, int y, int w, const char *k, const char *v, Col vc) {
    rbox(x, y, w, 36, 10, alpha(C_ROW, 120)); text(k, x + 12, y + 6, 19, C_DIM, 0); int vw = text_w(v, 20); text(v, x + w - vw - 12, y + 6, 20, vc, 0);
}

// per-system accent and monogram
static Col sys_color(const char *folder) {
    static const struct { const char *f; Col c; } t[] = {
        {"arcade", {255, 184, 64, 255}}, {"_fav", {255, 210, 90, 255}}, {"_top", {255, 140, 190, 255}}, {"_genre", {140, 200, 255, 255}}, {"_recent", {120, 230, 160, 255}}, {"md", {70, 150, 255, 255}}, {"snes", {170, 120, 255, 255}}, {"nes", {255, 92, 92, 255}},
        {"genesis", {90, 190, 255, 255}}, {"32x", {80, 210, 200, 255}}, {"pce", {255, 140, 60, 255}}, {"gba", {150, 110, 240, 255}},
        {"gbc", {110, 220, 120, 255}}, {"gb", {150, 200, 90, 255}}, {"_settings", {200, 205, 220, 255}}, {"_prefs", {120, 230, 200, 255}}};
    for (unsigned i = 0; i < sizeof t / sizeof t[0]; i++) if (!strcmp(folder, t[i].f)) return t[i].c;
    Col d = {120, 200, 190, 255}; return d;
}
static void monogram(const char *label, int cx, int cy, int size, Col c) {
    label = tr(label);
    char one[8] = {0}; const char *p = label; const char *q = p; utf8(&q); int n = (int)(q - p); if (n > 6) n = 6; memcpy(one, p, n);
    int r = size / 2; rbox(cx - r, cy - r, size, size, size / 4, alpha(c, 60)); text_c(one, cx, cy - (int)(size * 0.38f), (int)(size * 0.72f), c, size);
}

// ---------- preview pictures ----------
typedef struct { SDL_Texture *tex[3]; int n; char key[200]; } Preview;
static Preview pv;
static void preview_free(void) { for (int i = 0; i < 3; i++) if (pv.tex[i]) { SDL_DestroyTexture(pv.tex[i]); pv.tex[i] = NULL; } pv.n = 0; pv.key[0] = 0; }
static void preview_load(const char *file, const char *folder) {
    preview_free(); snprintf(pv.key, sizeof pv.key, "%s/%s", folder, file);
    char base[200]; snprintf(base, sizeof base, "%s", file); char *dot = strrchr(base, '.'); if (dot) *dot = 0;
    for (int i = 1; i <= 3; i++) {
        char p[420]; snprintf(p, sizeof p, "%s/pandory/snap/%s_%d.jpg", card, base, i);
        int w, h, ch; unsigned char *px = stbi_load(p, &w, &h, &ch, 3); if (!px) continue;
        SDL_Texture *t = SDL_CreateTexture(R, SDL_PIXELFORMAT_RGB24, SDL_TEXTUREACCESS_STATIC, w, h);
        if (t) { SDL_UpdateTexture(t, NULL, px, w * 3); pv.tex[pv.n++] = t; }
        stbi_image_free(px);
    }
}

// ---------- RetroArch's own settings menu (no game) ----------
static int launch_ra_menu(void) {
    char ra[320], base[320], logp[320], home[320]; static const char ovr[] = "/tmp/minos_ra_menu.cfg";
    snprintf(ra, sizeof ra, "%s/pandory/ra/retroarch", card); snprintf(base, sizeof base, "%s/pandory/ra/ra.cfg", card);
    snprintf(logp, sizeof logp, "%s/ra_menu_front.log", card); snprintf(home, sizeof home, "%s/pandory/ra", card);
    if (access(ra, R_OK) || access(base, R_OK)) { LOG("no RetroArch for the menu"); return 1; }
    { FILE *f = fopen(ovr, "w"); if (f) { fputs("menu_show_start_screen = \"false\"\n", f); fclose(f); } }
    { char lay[340]; snprintf(lay, sizeof lay, "%s/pandory/ra/layouts/_all.cfg", card); append_file(ovr, lay); snprintf(lay, sizeof lay, "%s/pandory/ra/layouts/_menu.cfg", card); append_file(ovr, lay); }
    video_down();
    pid_t pid = fork();
    if (pid == 0) {
        setenv("HOME", home, 1); setenv("XDG_CONFIG_HOME", home, 1); setenv("XDG_RUNTIME_DIR", "/data", 1);
        int fd = open(logp, O_WRONLY | O_CREAT | O_TRUNC, 0644); if (fd >= 0) { dup2(fd, 1); dup2(fd, 2); close(fd); }
        char *argv[] = { "ld-linux-armhf.so.3", "--library-path", "/usr/lib:/lib", ra, "--menu", "--config", base, "--appendconfig", (char *)ovr, NULL };
        execv("/lib/ld-linux-armhf.so.3", argv); _exit(127);
    }
    if (pid > 0) wait_ra(pid);
    return video_up();
}

// ---------- drawing: "old Korean arcade" theme ----------
// Everything is drawn by code (no copied pictures): neon signs, marquee bulbs, a 100-won coin, CRT scanlines and a perspective grid floor.
static Uint32 g_now; static char g_keystat[48] = "순정";
static const Col C_PK = {255, 62, 172, 255}, C_CY = {44, 230, 255, 255}, C_YL = {255, 222, 70, 255};
static void disc(int cx, int cy, int r, Col c) { fillc(c); for (int dy = -r; dy <= r; dy++) { int dx = (int)(sqrtf((float)(r * r - dy * dy)) + 0.5f); SDL_Rect q = {cx - dx, cy + dy, 2 * dx + 1, 1}; SDL_RenderFillRect(R, &q); } }
static void outline(int x, int y, int w, int h, int r, int th, Col line, Col fill) { rbox(x, y, w, h, r, line); rbox(x + th, y + th, w - 2 * th, h - 2 * th, r > th ? r - th : 1, fill); }
static void neon(const char *t, int x, int y, int size, Col c, int maxw) {          // glowing sign text
    static const int dx[] = {-3, 3, 0, 0, -2, 2, -2, 2}, dy[] = {0, 0, -3, 3, -2, -2, 2, 2};
    for (int i = 0; i < 8; i++) text(t, x + dx[i], y + dy[i], size, alpha(c, 34), maxw);
    text(t, x, y, size, mix(c, (Col){255, 255, 255, 255}, 0.5f), maxw);
}
static void neon_c(const char *t, int cx, int y, int size, Col c, int maxw) { while (size > 16 && text_w(t, size) > maxw) size -= 2; int w = text_w(t, size); neon(t, cx - w / 2, y, size, c, 0); }
static void bulbs(int x, int y, int w, int n, Col c, int phase) {
    for (int i = 0; i < n; i++) { int bx = x + (n > 1 ? w * i / (n - 1) : 0); int on = (int)((g_now / 260 + (Uint32)i + (Uint32)phase) % 3) == 0;
        if (on) disc(bx, y, 8, alpha(c, 45)); disc(bx, y, on ? 5 : 4, on ? mix(c, (Col){255, 255, 255, 255}, 0.4f) : alpha(c, 80)); }
}
static void coin(int cx, int cy, int r) {                                          // a 100-won style coin
    disc(cx, cy, r + 2, alpha(C_YL, 60)); disc(cx, cy, r, (Col){190, 150, 30, 255}); disc(cx, cy, r - 2, (Col){250, 214, 90, 255}); disc(cx, cy, r - 5, (Col){226, 184, 56, 255});
    text_c("100", cx, cy - (int)(r * 0.55f), (int)(r * 0.95f), (Col){120, 84, 8, 255}, r * 2);
}
static void draw_background(void) {
    for (int y = 0; y < H; y += 6) rect(0, y, W, 6, mix((Col){40, 14, 70, 255}, (Col){6, 4, 16, 255}, (float)y / (H * 0.8f > 1 ? H * 0.8f : 1)));
    // perspective grid floor
    fillc(alpha(C_PK, 46));
    for (int i = -14; i <= 14; i++) SDL_RenderDrawLine(R, 640 + i * 14, 420, 640 + i * 150, H);
    for (int k = 0; k < 9; k++) { int y = 420 + (int)(k * k * 3.9f) + 2; if (y < H) SDL_RenderDrawLine(R, 0, y, W, y); }
    rect(0, 0, W, 4, C_PK);
}
static void draw_crt(void) {                                                       // scanlines + dark corners, drawn last
    fillc(alpha(C_BLACK, 46)); for (int y = 0; y < H; y += 3) { SDL_Rect q = {0, y, W, 1}; SDL_RenderFillRect(R, &q); }
    for (int i = 0; i < 8; i++) { Col c = alpha(C_BLACK, (8 - i) * 9); rect(0, i * 5, W, 5, c); rect(0, H - (i + 1) * 5, W, 5, c); rect(i * 5, 0, 5, H, c); rect(W - (i + 1) * 5, 0, 5, H, c); }
}
static unsigned nz_seed;
static int nz_rand(int n) { nz_seed = nz_seed * 1664525u + 1013904223u; return (int)((nz_seed >> 8) % (unsigned)n); }
static void draw_noise(void) {                                  // old-TV static: a few specks all the time, a short crackle burst every few seconds
    nz_seed = (unsigned)(g_now / 50) * 2654435761u + 7;
    fillc(alpha((Col){255, 255, 255, 255}, 60)); for (int i = 0; i < 7; i++) { SDL_Rect q = {nz_rand(W), nz_rand(H), 2 + nz_rand(3), 1}; SDL_RenderFillRect(R, &q); }
    unsigned ph = g_now % 8000;
    if (ph < 420 || (ph > 4300 && ph < 4450)) {
        int n = ph < 420 ? 70 : 24;
        for (int i = 0; i < n; i++) { Col c = alpha((Col){230 + nz_rand(25), 230 + nz_rand(25), 255, 255}, 40 + nz_rand(70)); fillc(c); SDL_Rect q = {nz_rand(W), nz_rand(H), 10 + nz_rand(190), 1 + nz_rand(2)}; SDL_RenderFillRect(R, &q); }
        int by = nz_rand(H - 40); fillc(alpha((Col){255, 255, 255, 255}, 16)); SDL_Rect b = {0, by, W, 6 + nz_rand(14)}; SDL_RenderFillRect(R, &b);
    }
}
static void draw_topbar(const char *right) {
    rect(0, 4, W, 66, alpha(C_BLACK, 120)); rect(0, 70, W, 2, alpha(C_PK, 170)); bulbs(30, 70, W - 60, 40, C_YL, 0);
    outline(26, 8, 186, 56, 12, 3, C_YL, (Col){178, 24, 40, 255}); { int fs = 42; while (fs > 18 && text_w("오락실", fs) > 168) fs -= 2; text_c("오락실", 119, 12 + (42 - fs) / 2, fs, C_YL, 176); } rect(36, 14, 4, 4, C_YL); rect(198, 14, 4, 4, C_YL);
    text("MinosFront", 232, 34, 22, C_CY, 0); text("1회 100원", 232, 10, 20, C_YL, 0);
    coin(W - 50, 38, 22);
    if (right && right[0]) { int w = text_w(right, 24); neon(right, W - 100 - w, 22, 24, C_CY, 0); }
}
static void draw_footer(const char *a, const char *b, const char *c) {
    rect(0, 664, W, 56, alpha(C_BLACK, 140)); rect(0, 664, W, 2, alpha(C_CY, 140));
    int x = 34; if (a) pill(&x, 676, "A", a); if (b) pill(&x, 676, "B", b); if (c) { pill(&x, 676, "E F", c); }
    { const char *em = "문의: hguyswow@gmail.com", *gh = "github.com/hguyswow/Minos-front"; int w = text_w(em, 15), w2 = text_w(gh, 15);
      text(em, W - 24 - w, 672, 15, alpha(C_DIM, 210), 0); text(gh, W - 24 - w2, 692, 15, alpha(C_DIM, 210), 0); }
}

static void draw_systems(const int *show, int nshow, float curf, int cur) {
    draw_background(); draw_topbar("");
    for (int pass = 0; pass < 2; pass++)            // far cards first, selected card last (on top)
        for (int i = 0; i < nshow; i++) {
            float d = (float)i - curf; if (d > nshow / 2.0f) d -= nshow; if (d < -nshow / 2.0f) d += nshow;
            float ad = fabsf(d); if (ad > 2.6f) continue;
            int sel = ad < 0.5f; if ((pass == 1) != sel) continue;
            float k = 1.0f - fminf(ad, 1.0f) * 0.30f;
            int cw = (int)(380 * k), ch = (int)(340 * k); int cx = 640 + (int)(d * 300 + (d > 0 ? 40 : d < 0 ? -40 : 0) * fminf(ad, 1.0f));
            int x = cx - cw / 2, y = 340 - ch / 2 + (int)(ad * 14);
            Sys *s = &sys[show[i]]; Col ac = sys_color(s->folder); int fade = (int)(255 * (1.0f - fmaxf(0, ad - 1.2f) * 0.6f));
            rbox(x + 6, y + 10, cw, ch, 20, alpha(C_BLACK, (int)(110 * (fade / 255.0f))));
            outline(x, y, cw, ch, 20, sel ? 4 : 2, alpha(ac, sel ? 255 : (int)(150 * fade / 255.0f)), alpha((Col){22, 12, 44, 255}, fade));
            rbox(x + 8, y + 8, cw - 16, (int)(ch * 0.17f), 10, alpha(ac, (int)(70 * fade / 255.0f)));                      // marquee strip
            if (sel) bulbs(x + 24, y + 10 + (int)(ch * 0.085f), cw - 48, 12, ac, 1);
            monogram(s->label, cx, y + (int)(ch * 0.44f), (int)(116 * k), alpha(ac, fade));
            if (sel) neon_c(s->label, cx, y + (int)(ch * 0.66f), (int)(34 * k + 4), ac, cw - 24); else text_c(s->label, cx, y + (int)(ch * 0.66f), (int)(34 * k + 4), alpha(C_DIM, fade), cw - 24);
            char cnt[48];
            if (!strcmp(s->folder, "_orig")) snprintf(cnt, sizeof cnt, "판도라 기본 화면"); else if (!strcmp(s->folder, "_settings")) snprintf(cnt, sizeof cnt, "상세 설정"); else if (!strcmp(s->folder, "_prefs")) snprintf(cnt, sizeof cnt, "언어 · 소리 · 시작"); else if (!strcmp(s->folder, "_genre")) snprintf(cnt, sizeof cnt, "장르로 골라 보기"); else if (!strcmp(s->folder, "_keytest")) snprintf(cnt, sizeof cnt, "버튼 신호 확인"); else snprintf(cnt, sizeof cnt, "%d개 게임", s->n);
            text_c(cnt, cx, y + (int)(ch * 0.83f), (int)(24 * k + 2), alpha(sel ? C_YL : C_DIM, fade), cw - 24);
        }
    int dx = 640 - nshow * 9; for (int i = 0; i < nshow; i++) { Col c = i == cur ? C_YL : alpha(C_LINE, 200); rbox(dx + i * 18, 566, i == cur ? 14 : 8, 8, 4, c); if (i == cur) dx += 6; }
    draw_footer("열기", "원래 메뉴", NULL); text("← → 기종 선택", 640, 678, 22, C_DIM, 0);
    { int lx = 430; pill(&lx, 676, "코인", lang_en ? "한국어" : "English"); }
    { int lx = 900; pill(&lx, 676, "D", "아무 게임"); }
    if (sys[vi_rec].n) { int lx = 34; pill(&lx, 624, "C", "마지막 게임 이어하기"); }
    { rbox(574, 606, 132, 14, 7, C_YL); rbox(577, 609, 126, 8, 4, (Col){10, 4, 18, 255}); coin(540, 612, 18); if ((g_now / 600) % 2 == 0) neon_c("동전을 넣어 주세요", 640, 628, 26, C_PK, 420); }
    draw_noise(); draw_crt();
}

static void draw_list(Sys *s, int sel, float topf, const Disp *shown, Uint32 now) {
    Col ac = sys_color(s->folder);
    draw_background(); char right[160]; snprintf(right, sizeof right, "%s   [%s]   %d / %d", s->label, s->n ? group_of(s->title[sel]) : "-", s->n ? sel + 1 : 0, s->n); draw_topbar(right);
    outline(30, 86, 730, 566, 18, 3, alpha(C_CY, 190), C_PANEL);
    int rows = 10, rowh = 52, y0 = 102; SDL_Rect clip = {38, y0 - 2, 716, rows * rowh + 4}; SDL_RenderSetClipRect(R, &clip);
    int first = (int)floorf(topf); float frac = topf - first;
    for (int i = -1; i <= rows + 1; i++) {
        int idx = first + i; if (idx < 0 || idx >= s->n) continue;
        int y = y0 + (int)((i - frac) * rowh); int issel = idx == sel;
        if (issel) { rbox(42, y, 706, rowh - 6, 10, alpha(C_ROW, 255)); rect(42, y + 3, 5, rowh - 12, C_YL); if ((now / 400) % 2 == 0) text(">", 52, y + 6, 28, C_YL, 0); }
        char num[16]; snprintf(num, sizeof num, "%04d", idx + 1);
        text(num, 78, y + 11, 20, issel ? C_CY : C_DIM, 0); if (s->lib && fav_has(s->file[idx])) text("★", 142, y + 9, 22, C_YL, 0);
        text_fit(s->title[idx], 172, y + 7, 27, issel ? C_TXT : alpha(C_TXT, 190), 560);
    }
    SDL_RenderSetClipRect(R, NULL);
    if (s->n > rows) {
        int th = (int)(rows * (float)(rowh * rows) / (s->n * rowh)); if (th < 28) th = 28; int ty = y0 + (int)((topf / (float)(s->n - rows)) * (rows * rowh - th));
        rbox(748, y0, 6, rows * rowh, 3, alpha(C_LINE, 120)); rbox(748, ty < y0 ? y0 : ty, 6, th, 3, C_PK);
    }
    // right: CRT monitor with the preview picture
    outline(784, 86, 466, 566, 18, 3, alpha(C_PK, 190), C_PANEL);
    int px = 806, py = 106, pw = 422, ph = 316;
    rbox(px - 14, py - 12, pw + 28, ph + 24, 20, (Col){52, 48, 64, 255}); rbox(px - 8, py - 6, pw + 16, ph + 12, 14, (Col){20, 18, 28, 255});
    rbox(px, py, pw, ph, 10, (Col){4, 4, 10, 255});
    if (pv.n > 0) { SDL_Texture *t = pv.tex[(now / 700) % pv.n]; SDL_Rect d = {px, py, pw, ph}; SDL_RenderCopy(R, t, NULL, &d); }
    else text_c("미리보기 없음", px + pw / 2, py + ph / 2 - 14, 28, C_DIM, pw);
    fillc(alpha(C_BLACK, 60)); for (int y = py; y < py + ph; y += 3) { SDL_Rect q = {px, y, pw, 1}; SDL_RenderFillRect(R, &q); }
    disc(px + pw - 8, py + ph + 20, 4, ((now / 500) % 2) ? C_PK : alpha(C_PK, 90));
    if (s->n) {
        text_wrap(s->title[sel], 800, 446, 29, C_YL, 434, 2, 36);
        { char ml[160]; meta_line(s->file[sel], ml, sizeof ml); if (ml[0]) text_fit(ml, 800, 520, 21, C_CY, 330); else text_fit(s->file[sel], 800, 522, 18, C_DIM, 300); }
        if (s->lib && fav_has(s->file[sel])) text("★ 즐겨찾기", 1140, 522, 19, C_YL, 0);
        const char *r = !strcmp(shown->stretch, "true") ? "가득 채움" : !strcmp(shown->stretch, "false") ? "원래 비율" : "가득 채움";
        const char *q = !strcmp(shown->smooth, "true") ? "부드럽게" : !strcmp(shown->smooth, "false") ? "선명하게" : "부드럽게";
        { const char *r2 = !strcmp(shown->stretch, "false") ? "원래" : "가득"; const char *q2 = !strcmp(shown->smooth, "false") ? "선명" : "부드럽게"; const char *k2 = !strcmp(g_keystat, "순정") ? "순정" : "내 배치";
          chip(800, 552, 140, "비율", r2, C_CY); chip(950, 552, 150, "화질", q2, C_CY); chip(1110, 552, 130, "버튼", k2, !strcmp(g_keystat, "순정") ? C_CY : C_YL); }
        text("C 즐겨찾기   D 다음 글자   코인 게임별 설정", 800, 600, 20, C_DIM, 0);
        { char pi[100]; plays_info(s->file[sel], pi, sizeof pi); if (pi[0]) text(pi, 800, 628, 19, C_CY, 0); }
    }
    draw_footer("실행", "뒤로", "100개씩"); text("← → 10개씩", 455, 678, 22, C_DIM, 0);
    { int hx = 660; pill(&hx, 676, "Start", "게임 중 단축키"); }
    draw_crt();
}

static void draw_gsm(const char *title, const int *v, int row) {
    static const char *a[] = {"기본 (가득 채움)", "가득 채움", "원래 비율"}, *b[] = {"기본 (부드럽게)", "부드럽게", "선명하게"}, *c[] = {"기본 (켬)", "켬", "끔"};
    rect(0, 0, W, H, alpha(C_BLACK, 190)); rbox(290, 40, 700, 640, 22, (Col){24, 32, 62, 255}); rbox(290, 40, 700, 6, 3, C_ACC);
    text_c("이 게임 설정", 640, 58, 34, C_TXT, 620); text_c(title, 640, 104, 22, C_DIM, 620);
    const char *lab[] = {"화면 비율", "화질", "이어하기", "화면 테두리", "버튼 배치"}; const char **opt[] = {a, b, c, NULL, NULL};
    for (int i = 0; i < 5; i++) { int y = 140 + i * 78; rbox(330, y, 620, 64, 12, i == row ? C_ROW : alpha(C_ROW, 90));
        text(lab[i], 360, y + 16, 28, i == row ? C_TXT : C_DIM, 0); char t[96];
        if (i < 3) snprintf(t, sizeof t, "← %s →", opt[i][v[i]]); else if (i == 3) snprintf(t, sizeof t, "← %s →", v[3] ? tr(bezel_name[v[3] - 1]) : tr("기본 (설정값 따라감)")); else snprintf(t, sizeof t, "%s   (A 눌러 편집)", g_keystat);
        int w = text_w(t, i < 3 ? 28 : i == 3 ? 26 : 22); text(t, 920 - w, y + (i < 4 ? 16 : 20), i < 4 ? (i == 3 ? 26 : 28) : 22, i == row ? C_ACC : C_DIM, 0); }
    text_c("이어하기: 끝낼 때 자동 저장, 다시 실행하면 그 자리에서 시작", 640, 548, 20, C_DIM, 640);
    text_c("화면 테두리는 '원래 비율' 게임에만 보입니다", 640, 578, 20, C_DIM, 640);
    text_c("↑ ↓ 항목    ← → 바꾸기    A 저장하고 닫기 / 편집", 640, 628, 22, C_DIM, 620);
}
static void draw_confirm(void) {
    rect(0, 0, W, H, alpha(C_BLACK, 170)); rbox(400, 270, 480, 170, 20, (Col){26, 34, 64, 255}); rbox(400, 270, 480, 6, 3, C_ACC);
    text_c("종료할까요?", 640, 300, 38, C_TXT, 440); int x = 482; pill(&x, 372, "A", "예"); pill(&x, 372, "B", "아니오");
}

static void draw_help(void) {
    static const char *k[] = {"Start + 코인", "Start + A", "Start + E", "Start + F", "Start + B", "Start + D", "Start + ↑ / ↓", "Start + →", "Start + ←", "Start + C", "코인 + 버튼"};
    static const char *v[] = {"게임 끝내기 (MinosFront로 돌아옴)", "지금 상태 저장", "저장한 상태 불러오기", "일시정지", "게임 리셋", "빨리감기 켜기 / 끄기",
                              "저장 칸 번호 바꾸기", "소리 크게", "소리 작게", "RetroArch 메뉴 (코인 2초 누르기도 가능)", "그 버튼 연사 켜기 / 끄기 (한 번 더 하면 끔)"};
    rect(0, 0, W, H, alpha(C_BLACK, 190)); rbox(150, 24, 980, 672, 22, (Col){24, 32, 62, 255}); rbox(150, 24, 980, 6, 3, C_ACC);
    text_c("게임 중 단축키", 640, 40, 34, C_TXT, 800); text_c("Start 를 누른 채로 다른 버튼을 누릅니다   |   Start 만 4초 누르면 강제 종료", 640, 84, 20, C_DIM, 940);
    for (int i = 0; i < 11; i++) { int y = 122 + i * 46; rbox(180, y, 920, 40, 10, alpha(C_ROW, i % 2 ? 70 : 120));
        text(k[i], 200, y + 6, 24, C_ACC, 0); text_fit(v[i], 450, y + 6, 24, C_TXT, 630); }
    int x = 560; pill(&x, 636, "A", "닫기");
}
// ---------- button test ----------
// Shows every key / joystick signal that arrives, with a counter, so extra buttons can be checked. Hold Start 1.5 s to leave.
static int kt_count[512], kt_nj, kt_open_done; static char kt_log[10][90]; static int kt_nlog; static SDL_Joystick *kt_js[4];
static void kt_open(void) {
    if (kt_open_done) return; kt_open_done = 1;
    if (SDL_InitSubSystem(SDL_INIT_JOYSTICK) == 0) { kt_nj = SDL_NumJoysticks(); for (int i = 0; i < kt_nj && i < 4; i++) kt_js[i] = SDL_JoystickOpen(i); }
}
static void kt_add(const char *fmt, ...) {
    va_list a; va_start(a, fmt); char b[90]; vsnprintf(b, sizeof b, fmt, a); va_end(a);
    if (kt_nlog < 10) snprintf(kt_log[kt_nlog++], 90, "%s", b); else { memmove(kt_log[0], kt_log[1], 90 * 9); snprintf(kt_log[9], 90, "%s", b); }
}
static void kt_event(const SDL_Event *e) {
    if (e->type == SDL_KEYDOWN && !e->key.repeat) { int sc = e->key.keysym.scancode; if (sc >= 0 && sc < 512) kt_count[sc]++; kt_add("키  %s   (번호 %d)", SDL_GetScancodeName(sc), sc); }
    else if (e->type == SDL_JOYBUTTONDOWN) kt_add("조이스틱 %d  버튼 %d", e->jbutton.which, e->jbutton.button);
    else if (e->type == SDL_JOYHATMOTION && e->jhat.value) kt_add("조이스틱 %d  방향패드 %d", e->jhat.which, e->jhat.value);
    else if (e->type == SDL_JOYAXISMOTION && (e->jaxis.value > 16000 || e->jaxis.value < -16000)) kt_add("조이스틱 %d  축 %d  %s", e->jaxis.which, e->jaxis.axis, e->jaxis.value > 0 ? "+" : "-");
}
static void draw_keytest(Uint32 holdms) {
    draw_background(); draw_topbar("버튼 테스트");
    char t[120]; snprintf(t, sizeof t, "버튼을 아무거나 눌러 보세요. 신호가 오면 아래에 나타납니다.   (조이스틱 %d개 인식)", kt_nj); text(t, 40, 90, 22, C_DIM, 0);
    const Uint8 *kb2 = SDL_GetKeyboardState(NULL);
    int n = 0; for (int sc = 0; sc < 512; sc++) if (kt_count[sc]) {
        int col = n % 6, row = n / 6; int x = 40 + col * 200, y = 130 + row * 70; if (row > 3) break;
        int on = kb2[sc]; rbox(x, y, 188, 60, 12, on ? mix(C_ACC, C_BLACK, 0.3f) : C_PANEL);
        text_fit(SDL_GetScancodeName(sc), x + 12, y + 6, 24, on ? C_TXT : C_ACC, 164); char c[32]; snprintf(c, sizeof c, "%d 번 눌림", kt_count[sc]); text(c, x + 12, y + 34, 18, C_DIM, 0); n++; }
    if (!n) text("아직 눌린 버튼이 없습니다", 40, 150, 26, C_DIM, 0);
    rbox(40, 420, 1200, 230, 14, C_PANEL); text("최근 신호", 60, 430, 20, C_DIM, 0);
    for (int i = 0; i < kt_nlog; i++) text(kt_log[kt_nlog - 1 - i], 60, 460 + i * 19, 18, i ? C_DIM : C_TXT, 0);
    rect(0, 664, W, 56, alpha(C_BLACK, 110)); rect(0, 664, W, 1, alpha(C_LINE, 140));
    text(holdms ? "Start 를 계속 누르는 중... 나가기" : "나가기: Start 를 1.5초 누르고 있기", 34, 678, 22, holdms ? C_ACC : C_DIM, 0);
}

#include "front_editor.inc"

// ---------- start-up splash (about 3 seconds, any key skips it) ----------
#define SPLASH_MS 3200
static void draw_splash(Uint32 t) {
    g_now = t;
    if (t < 450) {                                                  // CRT warm-up: a white line opens up into the picture
        rect(0, 0, W, H, C_BLACK); float k = t / 450.0f; int h = 3 + (int)(k * k * H); fillc(alpha((Col){235, 240, 255, 255}, 255 - (int)(k * 120))); SDL_Rect q = {0, H / 2 - h / 2, W, h}; SDL_RenderFillRect(R, &q);
        draw_crt(); return; }
    draw_background(); bulbs(120, 150, W - 240, 30, C_YL, 0); bulbs(120, 560, W - 240, 30, C_YL, 1);
    int dy = t < 800 ? (int)((800 - t) * 0.25f) : 0;                // the sign drops in
    outline(400, 190 - dy, 480, 150, 20, 5, C_YL, (Col){178, 24, 40, 255}); text_c("오락실", 640, 204 - dy, 104, C_YL, 440);
    neon_c("DX2 PLUS", 640, 372, 74, C_CY, 900);
    text_c("MinosFront", 640, 462, 28, C_DIM, 400);
    if (t > 1300) {                                                 // a coin falls into the slot
        float k = (t - 1300) / 650.0f; if (k > 1) k = 1; int cy = (int)(-40 + k * k * 560);
        rbox(574, 590, 132, 14, 7, C_YL); rbox(577, 593, 126, 8, 4, (Col){10, 4, 18, 255});
        if (k < 1) coin(640, cy, 26); }
    if (t > 2000) { if (((t - 2000) / 220) % 2 == 0 || t > 2900) neon_c("CREDIT 1", 640, 616, 30, C_PK, 300); }
    if (t > 2400) neon_c("GAME START", 640, 106, 40, C_PK, 500);
    draw_noise();
    if (t < 700) { fillc(alpha(C_BLACK, 255 - (int)(t - 450) * 255 / 250)); SDL_Rect q = {0, 0, W, H}; if (t > 450) SDL_RenderFillRect(R, &q); }
    if (t > SPLASH_MS - 350) { int a = (int)(t - (SPLASH_MS - 350)) * 255 / 350; if (a > 255) a = 255; fillc(alpha(C_BLACK, a)); SDL_Rect q = {0, 0, W, H}; SDL_RenderFillRect(R, &q); }
    draw_crt();
}
