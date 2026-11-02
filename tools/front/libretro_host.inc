
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

#define SYM(t, n) t n = (t)dlsym(core, #n)
static void play(Sys *s, int gi) {
    char rom[400]; snprintf(rom, sizeof rom, "%s/roms_pandory/%s/%s", card, s->folder, s->file[gi]);
    LOG("play core=%s rom=%s", s->core, rom);
    core = dlopen(s->core, RTLD_NOW | RTLD_LOCAL);
    if (!core) { LOG("dlopen failed: %s", dlerror()); return; }
    SYM(void (*)(int (*)(unsigned, void *)), retro_set_environment);
    SYM(void (*)(void (*)(const void *, unsigned, unsigned, size_t)), retro_set_video_refresh);
    SYM(void (*)(void (*)(int16_t, int16_t)), retro_set_audio_sample);
    SYM(void (*)(size_t (*)(const int16_t *, size_t)), retro_set_audio_sample_batch);
    SYM(void (*)(void (*)(void)), retro_set_input_poll);
    SYM(void (*)(int16_t (*)(unsigned, unsigned, unsigned, unsigned)), retro_set_input_state);
    SYM(void (*)(void), retro_init); SYM(void (*)(void), retro_deinit);
    SYM(void (*)(RSysInfo *), retro_get_system_info); SYM(void (*)(RAvInfo *), retro_get_system_av_info);
    SYM(int (*)(const RGameInfo *), retro_load_game); SYM(void (*)(void), retro_unload_game); SYM(void (*)(void), retro_run);
    SYM(size_t (*)(unsigned), retro_get_memory_size); SYM(void *(*)(unsigned), retro_get_memory_data);
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
