// Prints the input descriptors (button names) a libretro core reports for a game.  usage: desc_dump core.so rom [system_dir]
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef struct { unsigned port, device, index, id; const char *desc; } Desc;
typedef struct { const char *path; const void *data; size_t size; const char *meta; } GI;
typedef struct { const char *n, *v, *e; int fp, be; } SI;
static const char *sysd = "/tmp";
static const char *PADN[] = {"B", "Y", "SELECT", "START", "UP", "DOWN", "LEFT", "RIGHT", "A", "X", "L", "R", "L2", "R2", "L3", "R3"};
static int env(unsigned cmd, void *d) {
    switch (cmd & 0xFFFF) {
    case 11: { Desc *x = d; for (; x->desc; x++) if (x->port == 0 && x->device == 1) printf("  retropad %-6s = %s\n", x->id < 16 ? PADN[x->id] : "?", x->desc); return 1; }
    case 9: case 30: case 31: *(const char **)d = sysd; return 1;
    case 3: *(int *)d = 1; return 1;
    case 10: case 8: case 12: case 13: case 16: case 21: case 22: return 1;
    case 15: ((const char **)d)[1] = NULL; return 0;
    case 17: *(int *)d = 0; return 1;
    case 18: return 1;
    default: return 0;
    }
}
static void vr(const void *a, unsigned b, unsigned c, size_t d) {} static void as(short l, short r) {} static size_t ab(const short *a, size_t n) { return n; } static void ip(void) {} static short is(unsigned a, unsigned b, unsigned c, unsigned d) { return 0; }
int main(int c, char **v) {
    if (c > 3) sysd = v[3]; void *h = dlopen(v[1], RTLD_NOW); if (!h) { puts(dlerror()); return 1; }
    void (*retro_set_environment)(int (*)(unsigned, void *)) = dlsym(h, "retro_set_environment"); void (*retro_init)(void) = dlsym(h, "retro_init");
    void (*retro_set_video_refresh)(void (*)(const void *, unsigned, unsigned, size_t)) = dlsym(h, "retro_set_video_refresh");
    void (*retro_set_audio_sample)(void (*)(short, short)) = dlsym(h, "retro_set_audio_sample"); void (*retro_set_audio_sample_batch)(size_t (*)(const short *, size_t)) = dlsym(h, "retro_set_audio_sample_batch");
    void (*retro_set_input_poll)(void (*)(void)) = dlsym(h, "retro_set_input_poll"); void (*retro_set_input_state)(short (*)(unsigned, unsigned, unsigned, unsigned)) = dlsym(h, "retro_set_input_state");
    void (*retro_get_system_info)(SI *) = dlsym(h, "retro_get_system_info"); int (*retro_load_game)(const GI *) = dlsym(h, "retro_load_game");
    retro_set_environment(env); retro_init(); retro_set_video_refresh(vr); retro_set_audio_sample(as); retro_set_audio_sample_batch(ab); retro_set_input_poll(ip); retro_set_input_state(is);
    SI si; memset(&si, 0, sizeof si); retro_get_system_info(&si); printf("core: %s %s\n", si.n, si.v);
    GI g; memset(&g, 0, sizeof g); g.path = v[2]; void *buf = NULL;
    if (!si.fp) { FILE *f = fopen(v[2], "rb"); if (!f) { puts("rom?"); return 2; } fseek(f, 0, SEEK_END); long n = ftell(f); fseek(f, 0, SEEK_SET); buf = malloc(n); fread(buf, 1, n, f); fclose(f); g.data = buf; g.size = n; }
    int ok = retro_load_game(&g); printf("load: %d\n", ok); return 0;
}
