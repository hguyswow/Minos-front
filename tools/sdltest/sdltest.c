// SDL2 display/input probe for the Pandora Saga DX2 Plus (device SDL2 2.0.7 with KMSDRM + GLES2 via libmali).
// Usage: sdltest LOGFILE [seconds]
#include <SDL.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static FILE *lg;
#define LOG(...) do { fprintf(lg, __VA_ARGS__); fputc('\n', lg); fflush(lg); } while (0)

int main(int argc, char **argv) {
    const char *path = argc > 1 ? argv[1] : "/tmp/sdltest.log";
    int secs = argc > 2 ? atoi(argv[2]) : 40;
    lg = fopen(path, "w");
    if (!lg) return 1;
    LOG("sdltest start; SDL compiled %d.%d.%d", SDL_MAJOR_VERSION, SDL_MINOR_VERSION, SDL_PATCHLEVEL);
    SDL_version v; SDL_GetVersion(&v);
    LOG("SDL linked %d.%d.%d", v.major, v.minor, v.patch);
    LOG("XDG_RUNTIME_DIR=%s", getenv("XDG_RUNTIME_DIR") ? getenv("XDG_RUNTIME_DIR") : "(null)");
    for (int i = 0; i < SDL_GetNumVideoDrivers(); i++) LOG("video driver %d: %s", i, SDL_GetVideoDriver(i));
    for (int i = 0; i < SDL_GetNumAudioDrivers(); i++) LOG("audio driver %d: %s", i, SDL_GetAudioDriver(i));

    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_JOYSTICK | SDL_INIT_EVENTS) != 0) {
        LOG("SDL_Init failed: %s", SDL_GetError());
        return 2;
    }
    LOG("SDL_Init ok; current video driver: %s", SDL_GetCurrentVideoDriver());
    int nd = SDL_GetNumVideoDisplays();
    LOG("displays: %d", nd);
    for (int d = 0; d < nd; d++) {
        SDL_DisplayMode m;
        if (SDL_GetDesktopDisplayMode(d, &m) == 0) LOG("display %d desktop mode %dx%d @%d", d, m.w, m.h, m.refresh_rate);
        for (int k = 0; k < SDL_GetNumDisplayModes(d) && k < 12; k++) {
            if (SDL_GetDisplayMode(d, k, &m) == 0) LOG("  mode %d: %dx%d @%d", k, m.w, m.h, m.refresh_rate);
        }
    }
    LOG("joysticks: %d", SDL_NumJoysticks());
    for (int i = 0; i < SDL_NumJoysticks(); i++) LOG("  joystick %d: %s", i, SDL_JoystickNameForIndex(i));

    SDL_Window *win = SDL_CreateWindow("sdltest", 0, 0, 1280, 720, SDL_WINDOW_FULLSCREEN_DESKTOP);
    if (!win) { LOG("CreateWindow failed: %s", SDL_GetError()); return 3; }
    int w = 0, h = 0; SDL_GetWindowSize(win, &w, &h);
    LOG("window ok %dx%d", w, h);
    SDL_Renderer *r = SDL_CreateRenderer(win, -1, SDL_RENDERER_ACCELERATED);
    if (!r) { LOG("accelerated renderer failed: %s", SDL_GetError()); r = SDL_CreateRenderer(win, -1, SDL_RENDERER_SOFTWARE); }
    if (!r) { LOG("renderer failed: %s", SDL_GetError()); return 4; }
    SDL_RendererInfo ri; SDL_GetRendererInfo(r, &ri);
    LOG("renderer: %s flags=%u maxtex=%dx%d", ri.name, ri.flags, ri.max_texture_width, ri.max_texture_height);

    SDL_Joystick *js[8] = {0};
    for (int i = 0; i < SDL_NumJoysticks() && i < 8; i++) js[i] = SDL_JoystickOpen(i);

    Uint32 t0 = SDL_GetTicks(), last = t0; int frames = 0, quit = 0;
    int boxes[8] = {0};
    while (!quit && SDL_GetTicks() - t0 < (Uint32)secs * 1000) {
        SDL_Event e;
        while (SDL_PollEvent(&e)) {
            switch (e.type) {
            case SDL_KEYDOWN: LOG("%u KEYDOWN scancode=%d key=%s", SDL_GetTicks() - t0, e.key.keysym.scancode, SDL_GetKeyName(e.key.keysym.sym)); if (e.key.keysym.sym == SDLK_q) quit = 1; boxes[e.key.keysym.scancode & 7] ^= 1; break;
            case SDL_KEYUP: LOG("%u KEYUP scancode=%d", SDL_GetTicks() - t0, e.key.keysym.scancode); break;
            case SDL_JOYBUTTONDOWN: LOG("%u JOYBUTTON %d down (joy %d)", SDL_GetTicks() - t0, e.jbutton.button, e.jbutton.which); boxes[e.jbutton.button & 7] ^= 1; break;
            case SDL_JOYBUTTONUP: LOG("%u JOYBUTTON %d up", SDL_GetTicks() - t0, e.jbutton.button); break;
            case SDL_JOYAXISMOTION: if (abs(e.jaxis.value) > 8000) LOG("%u JOYAXIS %d = %d", SDL_GetTicks() - t0, e.jaxis.axis, e.jaxis.value); break;
            case SDL_JOYHATMOTION: LOG("%u JOYHAT %d = %d", SDL_GetTicks() - t0, e.jhat.hat, e.jhat.value); break;
            case SDL_JOYDEVICEADDED: LOG("joystick added %d", e.jdevice.which); if (e.jdevice.which < 8) js[e.jdevice.which] = SDL_JoystickOpen(e.jdevice.which); break;
            case SDL_QUIT: quit = 1; break;
            default: break;
            }
        }
        Uint32 t = SDL_GetTicks() - t0;
        SDL_SetRenderDrawColor(r, 20, 20, 60, 255);
        SDL_RenderClear(r);
        // colour bars (checks colours and full-screen stretch)
        const Uint8 col[8][3] = {{255,0,0},{0,255,0},{0,0,255},{255,255,0},{255,0,255},{0,255,255},{255,255,255},{128,128,128}};
        for (int i = 0; i < 8; i++) {
            SDL_SetRenderDrawColor(r, col[i][0], col[i][1], col[i][2], 255);
            SDL_Rect bar = { i * (w / 8), 0, w / 8, h / 4 };
            SDL_RenderFillRect(r, &bar);
            if (boxes[i]) { SDL_Rect b = { i * (w / 8) + 10, h / 4 + 10, w / 8 - 20, h / 4 }; SDL_RenderFillRect(r, &b); }
        }
        // border and moving square (checks edges, refresh, tearing)
        SDL_SetRenderDrawColor(r, 255, 255, 255, 255);
        SDL_Rect bd = { 0, 0, w, h }; SDL_RenderDrawRect(r, &bd);
        SDL_Rect sq = { (int)((t / 4) % (Uint32)(w - 80)), h - 120, 80, 80 };
        SDL_RenderFillRect(r, &sq);
        SDL_RenderPresent(r);
        frames++;
        if (SDL_GetTicks() - last >= 5000) { LOG("%u fps ~%d", SDL_GetTicks() - t0, frames / 5); frames = 0; last = SDL_GetTicks(); }
        SDL_Delay(1);
    }
    LOG("finished");
    SDL_DestroyRenderer(r); SDL_DestroyWindow(win); SDL_Quit();
    fclose(lg);
    return 0;
}
