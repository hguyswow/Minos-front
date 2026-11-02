// MinosFront v0 - tiny EmulationStation-like launcher for the Pandora Saga DX2 Plus.
// SDL2 (device build, KMSDRM + GLES2) + stb_truetype/stb_image. Korean text via a TTF font.
// Usage: minosfront CARD_ROOT [auto_exit_seconds]
#include <SDL.h>
#include <dirent.h>
#include <strings.h>
#include <dlfcn.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>
#include "ra_settings.inc"

#define STB_TRUETYPE_IMPLEMENTATION
#include "stb_truetype.h"

#define W 1280
#define H 720
#define MAXSYS 24
#define MAXGAME 2048

static FILE *lg;
#define LOG(...) do { if (lg) { fprintf(lg, __VA_ARGS__); fputc('\n', lg); fflush(lg); } } while (0)

typedef struct { char folder[40], label[64], core[160]; int n; char **file, **title; char **gcore, **fold; int lib; char **ofile, **otitle, **ogcore; } Sys;   // lib=1: original game list (pandory/library.tsv), files in <card>/roms, core per game
static Sys sys[MAXSYS]; static int nsys;
static char card[256];

// ---------- font ----------
static stbtt_fontinfo font; static unsigned char *fontdata;
typedef struct { int cp, size; SDL_Texture *tex; int w, h, xo, yo, adv; } Glyph;
#define GCACHE 6000
static Glyph gc[GCACHE]; static int ngc;
static SDL_Renderer *R;

static Glyph *glyph(int cp, int size) {
    for (int i = 0; i < ngc; i++) if (gc[i].cp == cp && gc[i].size == size) return &gc[i];
    if (ngc >= GCACHE) { for (int i = 0; i < ngc; i++) if (gc[i].tex) SDL_DestroyTexture(gc[i].tex); ngc = 0; }
    Glyph *g = &gc[ngc++]; g->cp = cp; g->size = size; g->tex = NULL;
    float sc = stbtt_ScaleForPixelHeight(&font, (float)size);
    int adv, lsb; stbtt_GetCodepointHMetrics(&font, cp, &adv, &lsb); g->adv = (int)(adv * sc + 0.5f);
    int w, h, xo, yo;
    unsigned char *bm = stbtt_GetCodepointBitmap(&font, 0, sc, cp, &w, &h, &xo, &yo);
    g->w = w; g->h = h; g->xo = xo; g->yo = yo;
    if (bm && w > 0 && h > 0) {
        SDL_Surface *s = SDL_CreateRGBSurfaceWithFormat(0, w, h, 32, SDL_PIXELFORMAT_ABGR8888);
        Uint32 *px = (Uint32 *)s->pixels;
        for (int i = 0; i < w * h; i++) px[i] = 0x00FFFFFFu | ((Uint32)bm[i] << 24);
        g->tex = SDL_CreateTextureFromSurface(R, s);
        SDL_SetTextureBlendMode(g->tex, SDL_BLENDMODE_BLEND);
        SDL_FreeSurface(s);
    }
    if (bm) stbtt_FreeBitmap(bm, NULL);
    return g;
}

#include "front_i18n.inc"

static int utf8(const char **p) {
    const unsigned char *s = (const unsigned char *)*p; int c = *s++;
    if (c < 0x80) { *p = (const char *)s; return c; }
    if ((c & 0xE0) == 0xC0) { c = ((c & 0x1F) << 6) | (s[0] & 0x3F); s += 1; }
    else if ((c & 0xF0) == 0xE0) { c = ((c & 0x0F) << 12) | ((s[0] & 0x3F) << 6) | (s[1] & 0x3F); s += 2; }
    else if ((c & 0xF8) == 0xF0) { c = ((c & 0x07) << 18) | ((s[0] & 0x3F) << 12) | ((s[1] & 0x3F) << 6) | (s[2] & 0x3F); s += 3; }
    *p = (const char *)s; return c;
}

static int text_w(const char *t, int size) {
    t = tr(t);
    int w = 0; while (*t) { int cp = utf8(&t); w += glyph(cp, size)->adv; } return w;
}

static void text(const char *t, int x, int y, int size, SDL_Color c, int maxw) {
    t = tr(t);
    float sc = stbtt_ScaleForPixelHeight(&font, (float)size);
    int asc, desc, gap; stbtt_GetFontVMetrics(&font, &asc, &desc, &gap);
    int base = y + (int)(asc * sc);
    int penx = x;
    while (*t) {
        int cp = utf8(&t); Glyph *g = glyph(cp, size);
        if (maxw && penx + g->adv > x + maxw) break;
        if (g->tex) {
            SDL_SetTextureColorMod(g->tex, c.r, c.g, c.b); SDL_SetTextureAlphaMod(g->tex, c.a);
            SDL_Rect d = { penx + g->xo, base + g->yo, g->w, g->h };
            SDL_RenderCopy(R, g->tex, NULL, &d);
        }
        penx += g->adv;
    }
}

// ---------- data ----------
static int cmpstr(const void *a, const void *b) { return strcmp(*(char *const *)a, *(char *const *)b); }

static void default_sys(void) {
    static const char *d[][3] = {
        {"genesis", "메가드라이브", "picodrive_libretro.so"}, {"32x", "세가 32X", "picodrive_libretro.so"},
        {"pce", "PC엔진", "mednafen_pce_fast_libretro.so"}, {"gba", "게임보이 어드밴스", "mgba_libretro.so"},
        {"gbc", "게임보이 컬러", "gambatte_libretro.so"}, {"gb", "게임보이", "gambatte_libretro.so"},
        {"atari2600", "아타리 2600", "stella2014_libretro.so"}, {"amiga", "아미가", "puae_libretro.so"},
        {"atarist", "아타리 ST", "hatari_libretro.so"}, {"ports", "포트", "tyrquake_libretro.so"}};
    for (unsigned i = 0; i < sizeof d / sizeof d[0] && nsys < MAXSYS; i++) {
        Sys *s = &sys[nsys++]; snprintf(s->folder, sizeof s->folder, "%s", d[i][0]); snprintf(s->label, sizeof s->label, "%s", d[i][1]);
        snprintf(s->core, sizeof s->core, "%s/pandory/cores/%s", card, d[i][2]);
    }
}

// The original game list (about 5,000 games in <card>/roms) with Korean names, built on the PC by tools/build_library.py.
// Lines: system \t file \t title \t core   (core = a stock firmware libretro core in /usr/lib/libretro)
static void load_library(void) {
    static const char *keys[] = {"arcade", "md", "snes", "nes", "ps1"};
    static const char *labels[] = {"아케이드", "메가드라이브 (순정 목록)", "슈퍼패미컴", "패미컴", "플레이스테이션"};
    char p[300]; snprintf(p, sizeof p, "%s/pandory/library.tsv", card);
    FILE *f = fopen(p, "r"); if (!f) { LOG("no library.tsv"); return; }
    fseek(f, 0, SEEK_END); long sz = ftell(f); fseek(f, 0, SEEK_SET);
    if (sz <= 0 || sz > 8 * 1024 * 1024) { fclose(f); return; }
    char *buf = malloc((size_t)sz + 1); size_t r = fread(buf, 1, (size_t)sz, f); fclose(f); buf[r] = 0;
    int cnt[5] = {0}; for (char *q = buf; *q; ) { for (int k = 0; k < 5; k++) { size_t l = strlen(keys[k]); if (!strncmp(q, keys[k], l) && q[l] == '\t') { cnt[k]++; break; } } char *nl = strchr(q, '\n'); if (!nl) break; q = nl + 1; }
    int idx[5]; for (int k = 0; k < 5; k++) { idx[k] = -1; if (cnt[k] > 0 && nsys < MAXSYS) {
        Sys *s = &sys[nsys]; idx[k] = nsys++; s->lib = 1; snprintf(s->folder, sizeof s->folder, "%s", keys[k]); snprintf(s->label, sizeof s->label, "%s", labels[k]);
        s->file = calloc((size_t)cnt[k], sizeof(char *)); s->title = calloc((size_t)cnt[k], sizeof(char *)); s->gcore = calloc((size_t)cnt[k], sizeof(char *)); } }
    for (char *q = buf; *q; ) {
        char *nl = strchr(q, '\n'); if (nl) *nl = 0;
        char *c[4]; int nc = 0; c[nc++] = q; for (char *t = q; *t && nc < 4; t++) if (*t == '\t') { *t = 0; c[nc++] = t + 1; }
        if (nc == 4) for (int k = 0; k < 5; k++) if (idx[k] >= 0 && !strcmp(c[0], keys[k])) {
            Sys *s = &sys[idx[k]]; int i = s->n++; s->file[i] = strdup(c[1]); s->title[i] = strdup(c[2]);
            char cp[200]; snprintf(cp, sizeof cp, "/usr/lib/libretro/%s_libretro.so", c[3]); s->gcore[i] = strdup(cp); break; }
        if (!nl) break; q = nl + 1;
    }
    free(buf);
    for (int k = 0; k < 5; k++) if (idx[k] >= 0) LOG("library %s: %d games", keys[k], sys[idx[k]].n);
}

static void load_titles(char **keys, char **vals, int *n) {
    char p[300]; snprintf(p, sizeof p, "%s/pandory/names_map.txt", card);
    FILE *f = fopen(p, "r"); *n = 0; if (!f) return;
    char line[512];
    while (fgets(line, sizeof line, f) && *n < 4000) {
        if (line[0] == '#') continue;
        char *bar = strchr(line, '|'); if (!bar) continue;
        *bar = 0; char *k = line, *v = bar + 1;
        while (*k == ' ') k++; char *e = k + strlen(k); while (e > k && (e[-1] == ' ')) *--e = 0;
        while (*v == ' ') v++; e = v + strlen(v); while (e > v && (e[-1] == '\n' || e[-1] == '\r' || e[-1] == ' ')) *--e = 0;
        keys[*n] = strdup(k); vals[*n] = strdup(v); (*n)++;
    }
    fclose(f);
}

static void scan(void) {
    static char *keys[4000], *vals[4000]; int nk; load_titles(keys, vals, &nk);
    for (int si = 0; si < nsys; si++) {
        Sys *s = &sys[si]; if (s->lib) continue;   // the original list is already loaded
        char dir[300]; snprintf(dir, sizeof dir, "%s/roms_pandory/%s", card, s->folder);
        DIR *d = opendir(dir); if (!d) continue;
        s->file = calloc(MAXGAME, sizeof(char *)); s->title = calloc(MAXGAME, sizeof(char *));
        struct dirent *e; char *tmp[MAXGAME]; int n = 0;
        while ((e = readdir(d)) && n < MAXGAME) { if (e->d_name[0] == '.') continue; size_t l = strlen(e->d_name); if (l > 4 && !strcasecmp(e->d_name + l - 4, ".txt")) continue; tmp[n++] = strdup(e->d_name); }
        closedir(d); qsort(tmp, n, sizeof(char *), cmpstr);
        for (int i = 0; i < n; i++) {
            s->file[i] = tmp[i]; const char *t = NULL;
            for (int k = 0; k < nk; k++) if (!strcmp(keys[k], tmp[i])) { t = vals[k]; break; }
            if (t) s->title[i] = strdup(t); else { char *x = strdup(tmp[i]); char *dot = strrchr(x, '.'); if (dot) *dot = 0; for (char *c = x; *c; c++) if (*c == '_') *c = ' '; s->title[i] = x; }
        }
        s->n = n; LOG("system %s: %d games", s->folder, n);
    }
}


// ---------- minimal libretro host ----------
typedef struct { const char *path; const void *data; size_t size; const char *meta; } RGameInfo;
typedef struct { const char *library_name, *library_version, *valid_extensions; int need_fullpath, block_extract; } RSysInfo;
typedef struct { unsigned base_width, base_height, max_width, max_height; float aspect_ratio; } RGeom;
typedef struct { double fps, sample_rate; } RTiming;
typedef struct { RGeom geometry; RTiming timing; } RAvInfo;
typedef struct { const char *key, *value; } RVar;
typedef void (*rlog_t)(int, const char *, ...);
typedef struct { rlog_t log; } RLogIf;

static void *core; static int px_fmt = 2; static SDL_Texture *vtex; static int vw, vh;
static float aspect = 4.0f / 3.0f; static int stretch = 0; static double core_fps = 60.0, core_rate = 44100.0;
static SDL_AudioDeviceID adev; static char sysdir[300], savedir[300];
static const Uint8 *kb;

static void core_log(int lvl, const char *fmt, ...) {
    if (!lg) return;
    va_list a; va_start(a, fmt); fprintf(lg, "[core %d] ", lvl); vfprintf(lg, fmt, a); va_end(a); fflush(lg);
}

static int env_cb(unsigned cmd, void *data) {
    switch (cmd & 0xFFFF) {
    case 2: *(int *)data = 0; return 1;                         // overscan
    case 3: *(int *)data = 1; return 1;                         // can dupe
    case 8: return 1;                                           // performance level
    case 9: *(const char **)data = sysdir; return 1;            // system dir
    case 10: px_fmt = *(int *)data; LOG("pixel format %d", px_fmt); return 1;
    case 11: case 12: case 13: case 16: case 21: case 22: case 34: case 35: case 36: return 1;
    case 15: ((RVar *)data)->value = NULL; return 0;            // variables: use core defaults
    case 17: *(int *)data = 0; return 1;                        // variable update
    case 18: return 1;                                          // support no game
    case 24: *(unsigned *)data = (1u << 1) | (1u << 0); return 1;
    case 27: ((RLogIf *)data)->log = core_log; return 1;
    case 30: *(const char **)data = sysdir; return 1;
    case 31: *(const char **)data = savedir; return 1;
    case 32: { RAvInfo *a = data; aspect = a->geometry.aspect_ratio > 0 ? a->geometry.aspect_ratio : (float)a->geometry.base_width / a->geometry.base_height; core_fps = a->timing.fps; return 1; }
    case 37: { RGeom *g = data; aspect = g->aspect_ratio > 0 ? g->aspect_ratio : (float)g->base_width / g->base_height; return 1; }
    case 39: *(unsigned *)data = 0; return 1;                   // language: English
    case 7: return 1;
    default: return 0;
    }
}

static void video_cb(const void *data, unsigned w, unsigned h, size_t pitch) {
    if (!data) return;
    Uint32 fmt = px_fmt == 0 ? SDL_PIXELFORMAT_ARGB1555 : (px_fmt == 1 ? SDL_PIXELFORMAT_ARGB8888 : SDL_PIXELFORMAT_RGB565);
    if (!vtex || (int)w != vw || (int)h != vh) {
        if (vtex) SDL_DestroyTexture(vtex);
        vtex = SDL_CreateTexture(R, fmt, SDL_TEXTUREACCESS_STREAMING, w, h); vw = w; vh = h;
        SDL_SetTextureBlendMode(vtex, SDL_BLENDMODE_NONE);
    }
    SDL_UpdateTexture(vtex, NULL, data, (int)pitch);
    SDL_SetRenderDrawColor(R, 0, 0, 0, 255); SDL_RenderClear(R);
    SDL_Rect d = {0, 0, W, H};
    if (!stretch) {
        int dw = (int)(H * aspect), dh = H;
        if (dw > W) { dw = W; dh = (int)(W / aspect); }
        d.w = dw; d.h = dh; d.x = (W - dw) / 2; d.y = (H - dh) / 2;
    }
    SDL_RenderCopy(R, vtex, NULL, &d);
    SDL_RenderPresent(R);
}

static void audio_push(const int16_t *buf, size_t frames) {
    if (adev && SDL_GetQueuedAudioSize(adev) < (Uint32)(core_rate * 4 * 0.4)) SDL_QueueAudio(adev, buf, (Uint32)(frames * 4));
}
static size_t audio_batch_cb(const int16_t *buf, size_t frames) { audio_push(buf, frames); return frames; }
static void audio_sample_cb(int16_t l, int16_t r) { int16_t b[2]; b[0] = l; b[1] = r; audio_push(b, 1); }
static void input_poll_cb(void) { SDL_PumpEvents(); kb = SDL_GetKeyboardState(NULL); }
static int16_t input_state_cb(unsigned port, unsigned dev, unsigned idx, unsigned id) {
    (void)idx;
    if (port != 0 || dev != 1 || !kb) return 0;
    // RetroPad ids: B0 Y1 SELECT2 START3 UP4 DOWN5 LEFT6 RIGHT7 A8 X9 L10 R11
    static const int map[12] = {SDL_SCANCODE_A, SDL_SCANCODE_D, SDL_SCANCODE_5, SDL_SCANCODE_1, SDL_SCANCODE_UP, SDL_SCANCODE_DOWN,
                                SDL_SCANCODE_LEFT, SDL_SCANCODE_RIGHT, SDL_SCANCODE_B, SDL_SCANCODE_E, SDL_SCANCODE_F, SDL_SCANCODE_C};
    return id < 12 ? kb[map[id]] : 0;
}

static void play(Sys *s, int gi) {
    char rom[400]; snprintf(rom, sizeof rom, "%s/roms_pandory/%s/%s", card, s->folder, s->file[gi]);
    LOG("play core=%s rom=%s", s->core, rom);
    core = dlopen(s->core, RTLD_NOW | RTLD_LOCAL);
    if (!core) { LOG("dlopen failed: %s", dlerror()); return; }
    void (*retro_set_environment)(int (*)(unsigned, void *)) = (void (*)(int (*)(unsigned, void *)))dlsym(core, "retro_set_environment");
    void (*retro_set_video_refresh)(void (*)(const void *, unsigned, unsigned, size_t)) = (void (*)(void (*)(const void *, unsigned, unsigned, size_t)))dlsym(core, "retro_set_video_refresh");
    void (*retro_set_audio_sample)(void (*)(int16_t, int16_t)) = (void (*)(void (*)(int16_t, int16_t)))dlsym(core, "retro_set_audio_sample");
    void (*retro_set_audio_sample_batch)(size_t (*)(const int16_t *, size_t)) = (void (*)(size_t (*)(const int16_t *, size_t)))dlsym(core, "retro_set_audio_sample_batch");
    void (*retro_set_input_poll)(void (*)(void)) = (void (*)(void (*)(void)))dlsym(core, "retro_set_input_poll");
    void (*retro_set_input_state)(int16_t (*)(unsigned, unsigned, unsigned, unsigned)) = (void (*)(int16_t (*)(unsigned, unsigned, unsigned, unsigned)))dlsym(core, "retro_set_input_state");
    void (*retro_init)(void) = (void (*)(void))dlsym(core, "retro_init"); void (*retro_deinit)(void) = (void (*)(void))dlsym(core, "retro_deinit");
    void (*retro_get_system_info)(RSysInfo *) = (void (*)(RSysInfo *))dlsym(core, "retro_get_system_info"); void (*retro_get_system_av_info)(RAvInfo *) = (void (*)(RAvInfo *))dlsym(core, "retro_get_system_av_info");
    int (*retro_load_game)(const RGameInfo *) = (int (*)(const RGameInfo *))dlsym(core, "retro_load_game"); void (*retro_unload_game)(void) = (void (*)(void))dlsym(core, "retro_unload_game"); void (*retro_run)(void) = (void (*)(void))dlsym(core, "retro_run");
    size_t (*retro_get_memory_size)(unsigned) = (size_t (*)(unsigned))dlsym(core, "retro_get_memory_size"); void * (*retro_get_memory_data)(unsigned) = (void * (*)(unsigned))dlsym(core, "retro_get_memory_data");
    if (!retro_set_environment || !retro_init || !retro_load_game || !retro_run) { LOG("core symbols missing"); dlclose(core); return; }
    snprintf(sysdir, sizeof sysdir, "%s/pandory/system", card); snprintf(savedir, sizeof savedir, "%s/pandory/saves", card);
    mkdir(sysdir, 0777); mkdir(savedir, 0777);
    px_fmt = 2; aspect = 4.0f / 3.0f; vtex = NULL; vw = vh = 0;
    retro_set_environment(env_cb); retro_init();
    retro_set_video_refresh(video_cb); retro_set_audio_sample(audio_sample_cb); retro_set_audio_sample_batch(audio_batch_cb);
    retro_set_input_poll(input_poll_cb); retro_set_input_state(input_state_cb);
    RSysInfo si; memset(&si, 0, sizeof si); retro_get_system_info(&si);
    LOG("core: %s %s need_fullpath=%d ext=%s", si.library_name, si.library_version, si.need_fullpath, si.valid_extensions);
    RGameInfo gi2; memset(&gi2, 0, sizeof gi2); gi2.path = rom; void *buf = NULL;
    if (!si.need_fullpath) {
        FILE *f = fopen(rom, "rb");
        if (!f) { LOG("rom open failed"); retro_deinit(); dlclose(core); return; }
        fseek(f, 0, SEEK_END); long n = ftell(f); fseek(f, 0, SEEK_SET); buf = malloc(n); fread(buf, 1, n, f); fclose(f);
        gi2.data = buf; gi2.size = n;
    }
    if (!retro_load_game(&gi2)) { LOG("retro_load_game failed"); free(buf); retro_deinit(); dlclose(core); return; }
    RAvInfo av; memset(&av, 0, sizeof av); retro_get_system_av_info(&av);
    core_fps = av.timing.fps > 1 ? av.timing.fps : 60.0; core_rate = av.timing.sample_rate > 1000 ? av.timing.sample_rate : 44100.0;
    aspect = av.geometry.aspect_ratio > 0 ? av.geometry.aspect_ratio : (float)av.geometry.base_width / av.geometry.base_height;
    LOG("av: %ux%u aspect %.3f fps %.2f rate %.0f fmt %d", av.geometry.base_width, av.geometry.base_height, aspect, core_fps, core_rate, px_fmt);
    char sp[420]; snprintf(sp, sizeof sp, "%s/%s.srm", savedir, s->file[gi]);
    if (retro_get_memory_size && retro_get_memory_data) {
        size_t n = retro_get_memory_size(0); void *m = retro_get_memory_data(0);
        if (n && m) { FILE *f = fopen(sp, "rb"); if (f) { fread(m, 1, n, f); fclose(f); LOG("loaded save %s", sp); } }
    }
    SDL_InitSubSystem(SDL_INIT_AUDIO);
    SDL_AudioSpec want, have; memset(&want, 0, sizeof want); want.freq = (int)core_rate; want.format = AUDIO_S16SYS; want.channels = 2; want.samples = 1024;
    adev = SDL_OpenAudioDevice(NULL, 0, &want, &have, 0);
    if (adev) { SDL_PauseAudioDevice(adev, 0); LOG("audio ok %d Hz", have.freq); } else LOG("audio open failed: %s", SDL_GetError());
    Uint64 freq = SDL_GetPerformanceFrequency(), next = SDL_GetPerformanceCounter();
    double frame = 1.0 / core_fps; long frames = 0; int hold = 0, run = 1;
    while (run) {
        retro_run(); frames++;
        kb = SDL_GetKeyboardState(NULL);
        if (kb[SDL_SCANCODE_Q] || (kb[SDL_SCANCODE_1] && kb[SDL_SCANCODE_F] && kb[SDL_SCANCODE_E])) { if (++hold > core_fps) run = 0; } else hold = 0;
        next += (Uint64)(frame * freq);
        Uint64 now = SDL_GetPerformanceCounter();
        if (next > now) { Uint32 ms = (Uint32)((next - now) * 1000 / freq); if (ms > 0) SDL_Delay(ms); }
        else if (now - next > freq / 4) next = now;
    }
    LOG("stopped after %ld frames", frames);
    if (retro_get_memory_size && retro_get_memory_data) {
        size_t n = retro_get_memory_size(0); void *m = retro_get_memory_data(0);
        if (n && m) { FILE *f = fopen(sp, "wb"); if (f) { fwrite(m, 1, n, f); fclose(f); LOG("saved %s", sp); } }
    }
    if (adev) { SDL_CloseAudioDevice(adev); adev = 0; }
    retro_unload_game(); retro_deinit(); dlclose(core); core = NULL; free(buf);
    if (vtex) { SDL_DestroyTexture(vtex); vtex = NULL; }
}

// ---------- ui ----------
static SDL_Window *win;
static int video_up(void) {
    if (SDL_InitSubSystem(SDL_INIT_VIDEO) != 0) { LOG("video init failed: %s", SDL_GetError()); return 0; }
    int snapm = getenv("MINOS_SNAP") != NULL;
    win = SDL_CreateWindow("minosfront", 0, 0, W, H, snapm ? 0 : SDL_WINDOW_FULLSCREEN_DESKTOP);
    if (!win) { LOG("window failed: %s", SDL_GetError()); return 0; }
    R = SDL_CreateRenderer(win, -1, snapm ? SDL_RENDERER_SOFTWARE : SDL_RENDERER_ACCELERATED);
    if (!R) { LOG("renderer failed: %s", SDL_GetError()); return 0; }
    SDL_RenderSetLogicalSize(R, W, H); SDL_ShowCursor(0);
    ngc = 0; memset(gc, 0, sizeof gc);
    return 1;
}
static void preview_free(void);
static void video_down(void) {
    preview_free();
    for (int i = 0; i < ngc; i++) if (gc[i].tex) SDL_DestroyTexture(gc[i].tex);
    ngc = 0; if (R) SDL_DestroyRenderer(R); if (win) SDL_DestroyWindow(win); R = NULL; win = NULL;
    SDL_QuitSubSystem(SDL_INIT_VIDEO);
}

#include "front_user.inc"
#include "front_keys.inc"

// Plays the game with our own RetroArch 1.22.2 (pandory/ra/retroarch, config pandory/ra/ra.cfg).
// The screen ratio / smoothing come from pandory.xml (game > system > global), the same file the PC editor writes.
// The card is FAT (no exec), so the binary is started through the dynamic loader. No shell is involved,
// so odd characters in file names are harmless.  Returns 0 if the screen could not be brought back.
static int use_ra = 1, ra_skip_ratio = 0;   // front.cfg: player=builtin / ratio=off
static int launch_ra(Sys *s, int gi) {
    if (test_mode()) { LOG("test mode: not starting RetroArch"); return 1; }
    char ra[320], base[320], xml[320], rom[600], logp[320], home[320];
    static const char ovr[] = "/tmp/minos_ra_game.cfg";
    snprintf(ra, sizeof ra, "%s/pandory/ra/retroarch", card);
    snprintf(base, sizeof base, "%s/pandory/ra/ra.cfg", card);
    snprintf(xml, sizeof xml, "%s/pandory/pandory.xml", card);
    if (s->lib) snprintf(rom, sizeof rom, "%s/roms/%s", card, s->file[gi]);
    else snprintf(rom, sizeof rom, "%s/roms_pandory/%s/%s", card, s->folder, s->file[gi]);
    const char *fd = (s->fold && s->fold[gi]) ? s->fold[gi] : s->folder;
    const char *corepath = (s->lib && s->gcore && s->gcore[gi]) ? s->gcore[gi] : s->core;
    snprintf(logp, sizeof logp, "%s/ra_run.log", card);
    snprintf(home, sizeof home, "%s/pandory/ra", card);
    if (access(ra, R_OK) || access(base, R_OK)) { LOG("custom RetroArch missing -> built-in player"); if (!s->lib) play(s, gi); return 1; }
    LOG("launch: core=%s rom=%s", corepath, rom);
    Disp d; xml_display(xml, fd, s->file[gi], &d); apply_gs(s->file[gi], &d);
    LOG("ra: %s/%s stretch='%s' smooth='%s'", fd, s->file[gi], d.stretch, d.smooth);
    write_ra_override(ovr, &d, ra_skip_ratio);
    { char lay[340];
      snprintf(lay, sizeof lay, "%s/pandory/ra/layouts/_all.cfg", card); append_file(ovr, lay);                   // overrides for every game (e.g. video driver)
      snprintf(lay, sizeof lay, "%s/pandory/ra/layouts/%s.cfg", card, fd); append_file(ovr, lay); }
    { GS *g = gs_find(s->file[gi]); int rs = resume_def; if (g && g->resume[0]) rs = !strcmp(g->resume, "true"); FILE *rf = fopen(ovr, "a");
      if (rf) { fprintf(rf, "savestate_auto_save = \"%s\"\nsavestate_auto_load = \"%s\"\n", rs ? "true" : "false", rs ? "true" : "false"); fclose(rf); } }
    { char gk[320]; BtnInfo *bb = bi_find(s->file[gi]); group_key(bb, fd, gk, sizeof gk); const char *sp = km_resolve(s->file[gi], gk, NULL); if (sp) km_apply(ovr, sp, corepath, s->file[gi]); }        // per-system button layout
    video_down();
    pid_t pid = fork();
    if (pid == 0) {
        setenv("HOME", home, 1); setenv("XDG_CONFIG_HOME", home, 1); setenv("XDG_RUNTIME_DIR", "/data", 1);
        int fd = open(logp, O_WRONLY | O_CREAT | O_TRUNC, 0644); if (fd >= 0) { dup2(fd, 1); dup2(fd, 2); close(fd); }
        char *argv[] = { "ld-linux-armhf.so.3", "--library-path", "/usr/lib:/lib", ra, "--config", base,
                         "--appendconfig", (char *)ovr, "-L", (char *)corepath, rom, NULL };
        execv("/lib/ld-linux-armhf.so.3", argv); _exit(127);
    }
    if (pid > 0) wait_ra(pid); else LOG("fork failed");
    return video_up();
}

#include "front_ui.inc"

int main(int argc, char **argv) {
    snprintf(card, sizeof card, "%s", argc > 1 ? argv[1] : "/mnt/sdcard");
    int autoexit = argc > 2 ? atoi(argv[2]) : 0;
    char lp[300]; snprintf(lp, sizeof lp, "%s/front.log", card); lg = fopen(lp, "w");
    LOG("minosfront start card=%s", card);
    char fp[300]; snprintf(fp, sizeof fp, "%s/pandory/front/NanumGothic.ttf", card);
    FILE *ff = fopen(fp, "rb"); if (!ff) { LOG("font missing: %s", fp); return 2; }
    fseek(ff, 0, SEEK_END); long fs = ftell(ff); fseek(ff, 0, SEEK_SET); fontdata = malloc(fs); fread(fontdata, 1, fs, ff); fclose(ff);
    if (!stbtt_InitFont(&font, fontdata, stbtt_GetFontOffsetForIndex(fontdata, 0))) { LOG("font init failed"); return 3; }
    { char cp[300]; snprintf(cp, sizeof cp, "%s/pandory/front/front.cfg", card); FILE *cf = fopen(cp, "r");
      if (cf) { char l[200]; while (fgets(l, sizeof l, cf)) { if (!strncmp(l, "stretch=1", 9)) stretch = 1; if (!strncmp(l, "player=builtin", 14)) use_ra = 0; if (!strncmp(l, "ratio=off", 9)) ra_skip_ratio = 1; if (!strncmp(l, "quit_hold=", 10)) quit_hold = atoi(l + 10); if (!strncmp(l, "resume=", 7)) resume_def = atoi(l + 7); } fclose(cf); }
      LOG("stretch=%d", stretch); }
    make_virtual("_recent", "최근 한 게임", &vi_rec); make_virtual("_fav", "즐겨찾기", &vi_fav);
    load_library(); default_sys(); scan();
    nfav = ld_lines("favorites.txt", favs, MAXFAV); nrecent = ld_lines("recent.txt", recent, MAXREC); gs_load(); pos_load(); refill_virtual(); protect_cfg(); { const char *ml = getenv("MINOS_LANG"); if (ml && *ml ? strcmp(ml, "ko") != 0 : lang_load()) set_lang(1); }
    if (nsys < MAXSYS) { Sys *st = &sys[nsys++]; memset(st, 0, sizeof *st); snprintf(st->folder, sizeof st->folder, "_settings"); snprintf(st->label, sizeof st->label, "RetroArch 설정"); }
    if (nsys < MAXSYS) { Sys *st = &sys[nsys++]; memset(st, 0, sizeof *st); snprintf(st->folder, sizeof st->folder, "_keytest"); snprintf(st->label, sizeof st->label, "버튼 테스트"); }
    if (nsys < MAXSYS) { Sys *st = &sys[nsys++]; memset(st, 0, sizeof *st); snprintf(st->folder, sizeof st->folder, "_orig"); snprintf(st->label, sizeof st->label, "원래 메뉴"); }
    int show[MAXSYS], nshow = 0, cur0 = 0; rebuild_show(show, &nshow, &cur0);
    { int first = 0; for (int j = 0; j < nshow; j++) if (sys[show[j]].folder[0] != '_') { first = j; break; } cur0 = first;
      for (int j = 0; j < nshow; j++) if (!strcmp(sys[show[j]].folder, lastsys)) cur0 = j; }
    const char *snapdir = getenv("MINOS_SNAP");
    if (SDL_Init(SDL_INIT_EVENTS | SDL_INIT_AUDIO) != 0) { LOG("init failed"); return 4; }
    if (!video_up()) return 5;

    const char *sp = getenv("MINOS_SPLASH"); if (sp && !*sp) sp = NULL;
    if (!test_mode() || sp) {
        if (sp) { Uint32 tt = (Uint32)atoi(sp); draw_splash(tt); SDL_Surface *sf = SDL_CreateRGBSurfaceWithFormat(0, W, H, 32, SDL_PIXELFORMAT_ARGB8888); SDL_RenderReadPixels(R, NULL, SDL_PIXELFORMAT_ARGB8888, sf->pixels, sf->pitch);
            char bp[400]; snprintf(bp, sizeof bp, "%s/splash.bmp", getenv("MINOS_SNAP")); SDL_SaveBMP(sf, bp); SDL_FreeSurface(sf); return 0; }
        Uint32 st = SDL_GetTicks(); int skip = 0; SDL_FlushEvents(SDL_FIRSTEVENT, SDL_LASTEVENT);
        while (!skip && SDL_GetTicks() - st < SPLASH_MS) { SDL_Event e2; while (SDL_PollEvent(&e2)) if (e2.type == SDL_KEYDOWN || e2.type == SDL_QUIT) skip = 1; draw_splash(SDL_GetTicks() - st); SDL_RenderPresent(R); SDL_Delay(12); }
        SDL_FlushEvents(SDL_FIRSTEVENT, SDL_LASTEVENT);
    }
    int help = 0, gsm = 0, gsrow = 0, gsval[3] = {0, 0, 0}, mode = 0, cur = cur0, sel = 0, top = 0, confirm = 0;
    int lastcur = -1, lastsel = -1; Uint32 pvchg = 0; Disp shown; memset(&shown, 0, sizeof shown);   // cached per-game display options for the info panel
    Uint32 t0 = SDL_GetTicks(); int quit = 0;
    while (!quit) {
        if (autoexit && SDL_GetTicks() - t0 > (Uint32)autoexit * 1000) break;
        static const char *inj; static int injinit, injwait;   // test only: MINOS_KEYS="RRAD..." injects one key per frame (R L U N=down A B C D E F I S=start)
        if (!injinit) { inj = getenv("MINOS_KEYS"); injinit = 1; }
        if (inj && *inj) { static const char *ks = "RLUNABCDEFIS"; static const int sc[] = {SDL_SCANCODE_RIGHT, SDL_SCANCODE_LEFT, SDL_SCANCODE_UP, SDL_SCANCODE_DOWN, SDL_SCANCODE_A, SDL_SCANCODE_B, SDL_SCANCODE_C, SDL_SCANCODE_D, SDL_SCANCODE_E, SDL_SCANCODE_F, SDL_SCANCODE_I, SDL_SCANCODE_1};
            const char *q = strchr(ks, *inj++); if (q) { SDL_Event ev; memset(&ev, 0, sizeof ev); ev.type = SDL_KEYDOWN; ev.key.keysym.scancode = sc[q - ks]; SDL_PushEvent(&ev); } SDL_Delay(30); }
        SDL_Event e;
        while (SDL_PollEvent(&e)) {
            if (e.type == SDL_QUIT) quit = 1;
            if (mode == 2) { kt_event(&e); continue; }
            if (mode == 3) { if (e.type == SDL_KEYDOWN && ed_key(e.key.keysym.scancode)) { mode = 1; lastcur = -1; } continue; }
            if (e.type != SDL_KEYDOWN) continue;
            int k = e.key.keysym.scancode; Sys *s = nshow ? &sys[show[cur]] : NULL;
            if (k == SDL_SCANCODE_Q) quit = 1;
            if (help) { if (k == SDL_SCANCODE_A || k == SDL_SCANCODE_B || k == SDL_SCANCODE_1) help = 0; continue; }
            if (gsm) {
                if (k == SDL_SCANCODE_UP) gsrow = (gsrow + 3) % 4; else if (k == SDL_SCANCODE_DOWN) gsrow = (gsrow + 1) % 4;
                else if (k == SDL_SCANCODE_RIGHT && gsrow < 3) gsval[gsrow] = (gsval[gsrow] + 1) % 3;
                else if (k == SDL_SCANCODE_LEFT && gsrow < 3) gsval[gsrow] = (gsval[gsrow] + 2) % 3;
                else if (k == SDL_SCANCODE_A || k == SDL_SCANCODE_B || k == SDL_SCANCODE_I) {
                    static const char *tv[] = {"", "true", "false"}; gs_set(s->file[sel], tv[gsval[0]], tv[gsval[1]], tv[gsval[2]]); gsm = 0; lastcur = -1;
                    if (gsrow == 3 && k == SDL_SCANCODE_A) { ed_open(s->file[sel], s->title[sel], (s->fold && s->fold[sel]) ? s->fold[sel] : s->folder); mode = 3; } }
                continue; }
            if (confirm) { if (k == SDL_SCANCODE_A) quit = 1; else if (k == SDL_SCANCODE_B) confirm = 0; continue; }
            if (mode == 0) {
                if (k == SDL_SCANCODE_RIGHT && nshow) cur = (cur + 1) % nshow;
                else if (k == SDL_SCANCODE_LEFT && nshow) cur = (cur + nshow - 1) % nshow;
                else if (k == SDL_SCANCODE_A && nshow) {
                    if (!strcmp(s->folder, "_orig")) quit = 1;
                    else if (!strcmp(s->folder, "_keytest")) { kt_open(); mode = 2; }
                    else if (!strcmp(s->folder, "_settings")) { if (!launch_ra_menu()) quit = 1; t0 = SDL_GetTicks(); SDL_PumpEvents(); SDL_FlushEvents(SDL_FIRSTEVENT, SDL_LASTEVENT); }
                    else { mode = 1; sel = s->folder[0] == '_' ? 0 : pos_get(s->folder); if (sel >= s->n) sel = 0; if (getenv("MINOS_GAME")) for (int q = 0; q < s->n; q++) if (!strcmp(s->file[q], getenv("MINOS_GAME"))) sel = q; top = sel > 4 ? sel - 4 : 0; lastcur = -1; } }
                else if (k == SDL_SCANCODE_I) { set_lang(!lang_en); lang_save(); }
                else if (k == SDL_SCANCODE_B || k == SDL_SCANCODE_1) confirm = 1;
            } else {
                if (k == SDL_SCANCODE_DOWN && s->n) sel = (sel + 1) % s->n;
                else if (k == SDL_SCANCODE_UP && s->n) sel = (sel + s->n - 1) % s->n;
                else if (k == SDL_SCANCODE_RIGHT && s->n) { sel += 10; if (sel >= s->n) sel = s->n - 1; }
                else if (k == SDL_SCANCODE_F && s->n) { sel += 100; if (sel >= s->n) sel = s->n - 1; }      // F: 100 down
                else if (k == SDL_SCANCODE_E && s->n) { sel -= 100; if (sel < 0) sel = 0; }                  // E: 100 up
                else if (k == SDL_SCANCODE_LEFT && s->n) { sel -= 10; if (sel < 0) sel = 0; }
                else if (k == SDL_SCANCODE_1) help = 1;
                else if (k == SDL_SCANCODE_D && s->n) sel = jump_group(s, sel);
                else if (k == SDL_SCANCODE_I && s->n) {
                    GS *g = gs_find(s->file[sel]); gsval[0] = gsval[1] = gsval[2] = 0;
                    if (g) { gsval[0] = !strcmp(g->stretch, "true") ? 1 : !strcmp(g->stretch, "false") ? 2 : 0; gsval[1] = !strcmp(g->smooth, "true") ? 1 : !strcmp(g->smooth, "false") ? 2 : 0; }
                    if (g) gsval[2] = !strcmp(g->resume, "true") ? 1 : !strcmp(g->resume, "false") ? 2 : 0;
                    gsm = 1; gsrow = 0; }
                else if (k == SDL_SCANCODE_C && s->n && s->lib) {
                    fav_toggle(s->file[sel]); refill_virtual(); if (s->n == 0) mode = 0; rebuild_show(show, &nshow, &cur);
                    if (sel >= s->n) sel = s->n ? s->n - 1 : 0; lastcur = -1; }
                else if (k == SDL_SCANCODE_B) { if (s->folder[0] != '_') { pos_set(s->folder, sel); snprintf(lastsys, sizeof lastsys, "%s", s->folder); pos_save(); } mode = 0; }
                else if (k == SDL_SCANCODE_A && s->n) {
                    if (s->lib) { recent_push(s->file[sel]); if (s->folder[0] != '_') { pos_set(s->folder, sel); snprintf(lastsys, sizeof lastsys, "%s", s->folder); } pos_save(); }
                    int isrec = s == &sys[vi_rec]; const char *lf = s->file[sel];
                    if (use_ra || s->lib) { if (!launch_ra(s, sel)) { quit = 1; } } else play(s, sel);
                    if (s->lib) { refill_virtual(); if (isrec) { sel = 0; top = 0; } else (void)lf; }
                    t0 = SDL_GetTicks(); SDL_PumpEvents(); SDL_FlushEvents(SDL_FIRSTEVENT, SDL_LASTEVENT); lastcur = -1; preview_free(); }
                if (mode == 1 && s) { if (sel < top) top = sel; if (sel >= top + 10) top = sel - 9; }
            }
        }
        // ----- draw -----
        Uint32 now = SDL_GetTicks(); static float curf = 0, topf = 0; static int snapstep = 0;
        if (snapdir) now = 1400;
        g_now = now;
        { float dc = (float)cur - curf; if (dc > nshow / 2.0f) dc -= nshow; if (dc < -nshow / 2.0f) dc += nshow;
          curf += dc * 0.35f; if (fabsf(dc) < 0.02f) curf = (float)cur; if (curf < 0) curf += nshow; if (curf >= nshow) curf -= nshow;
          topf += ((float)top - topf) * 0.4f; if (fabsf((float)top - topf) < 0.02f) topf = (float)top; }
        if (!nshow) { draw_background(); draw_topbar(""); text("게임이 없습니다 (roms_pandory 폴더를 확인하세요)", 60, 300, 36, C_TXT, 0); }
        else if (mode == 3) draw_editor();
        else if (mode == 2) {
            static Uint32 kh; const Uint8 *kbs = SDL_GetKeyboardState(NULL);
            if (kbs[SDL_SCANCODE_1]) { if (!kh) kh = now; if (now - kh > 1500) { mode = 0; kh = 0; } } else kh = 0;
            draw_keytest(kh ? now - kh : 0);
        }
        else if (mode == 0) draw_systems(show, nshow, curf, cur);
        else {
            Sys *s = &sys[show[cur]];
            if (s->n && (lastcur != cur || lastsel != sel)) { char xp[320]; snprintf(xp, sizeof xp, "%s/pandory/pandory.xml", card); xml_display(xp, (s->fold && s->fold[sel]) ? s->fold[sel] : s->folder, s->file[sel], &shown); apply_gs(s->file[sel], &shown); km_status(s->file[sel], (s->fold && s->fold[sel]) ? s->fold[sel] : s->folder); lastcur = cur; lastsel = sel; pvchg = now; preview_free(); }
            if (s->n && pvchg && (snapdir || now - pvchg > 160)) { preview_load(s->file[sel], (s->fold && s->fold[sel]) ? s->fold[sel] : s->folder); pvchg = 0; }
            draw_list(s, sel, topf, &shown, now);
        }
        if (gsm && nshow && mode == 1) draw_gsm(sys[show[cur]].title[sel], gsval, gsrow);
        if (help) draw_help();
        if (confirm) draw_confirm();
        if (inj && !*inj && ++injwait > 60) {
            if (snapdir) { SDL_Surface *sf = SDL_CreateRGBSurfaceWithFormat(0, W, H, 32, SDL_PIXELFORMAT_ARGB8888); SDL_RenderReadPixels(R, NULL, SDL_PIXELFORMAT_ARGB8888, sf->pixels, sf->pitch);
                char bp[400]; snprintf(bp, sizeof bp, "%s/final.bmp", snapdir); SDL_SaveBMP(sf, bp); SDL_FreeSurface(sf); }
            quit = 1; }
        if (snapdir && !inj) {
            static const char *nm[] = {"1_systems", "2_list", "3_confirm", "4_help"};
            SDL_Surface *sf = SDL_CreateRGBSurfaceWithFormat(0, W, H, 32, SDL_PIXELFORMAT_ARGB8888);
            SDL_RenderReadPixels(R, NULL, SDL_PIXELFORMAT_ARGB8888, sf->pixels, sf->pitch);
            char bp[400]; snprintf(bp, sizeof bp, "%s/%s.bmp", snapdir, nm[snapstep]); SDL_SaveBMP(sf, bp); SDL_FreeSurface(sf);
            if (++snapstep >= 4) quit = 1;
            else if (snapstep == 1) { mode = 1; sel = 6 < sys[show[cur]].n ? 6 : 0; top = 0; topf = 0; }
            else if (snapstep == 2) confirm = 1;
            else if (snapstep == 3) { confirm = 0; help = 1; }
            SDL_Delay(1); continue;
        }
        SDL_RenderPresent(R); SDL_Delay(8);
    }
    if (nshow) { Sys *s = &sys[show[cur]]; if (s->folder[0] != '_') { if (mode == 1) pos_set(s->folder, sel); snprintf(lastsys, sizeof lastsys, "%s", s->folder); pos_save(); } }
    LOG("exit");
    video_down(); SDL_Quit(); if (lg) fclose(lg);
    return 0;
}
