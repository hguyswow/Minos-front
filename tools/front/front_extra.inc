// front_extra.inc - genre picker ("장르별 찾기") and the idle (attract) screen.
// Included after front_prefs.inc (uses the drawing helpers and the meta table of front_user.inc).

// ---------- genre picker ----------
// The genres of libretro-database and catver.ini are named differently; map them to one name.
static const char *gnorm(const char *g) {
    if (!strcasecmp(g, "Fighting")) return "Fighter";
    if (!strcasecmp(g, "Racing")) return "Driving";
    if (!strcasecmp(g, "Role-Playing")) return "RPG";
    if (!strcasecmp(g, "Beat'em Up")) return "Action";
    return g;
}
typedef struct { char name[40]; int n; } GenreN;
static GenreN gens[64]; static int ngen, g_sel, g_top;
static int vi_genre = -1;                                  // the "_genre" tile; it also holds the games of the chosen genre

static void genres_build(void) {
    ngen = 0;
    for (int i = 0; i < nmeta; i++) {
        const char *g = metas[i].genre; if (!g[0]) continue; g = gnorm(g);
        int k = 0; while (k < ngen && strcasecmp(gens[k].name, g)) k++;
        if (k == ngen) { if (ngen >= 64) continue; snprintf(gens[ngen].name, sizeof gens[0].name, "%s", g); gens[ngen].n = 0; ngen++; }
        gens[k].n++;
    }
    for (int i = 1; i < ngen; i++) { GenreN t = gens[i]; int j = i; while (j > 0 && gens[j - 1].n < t.n) { gens[j] = gens[j - 1]; j--; } gens[j] = t; }
    g_sel = g_top = 0;
}
// puts every game of the chosen genre into the "_genre" tile (all library systems), returns how many
static int genre_fill(int gi) {
    if (vi_genre < 0 || gi < 0 || gi >= ngen) return 0;
    Sys *v = &sys[vi_genre]; v->n = 0;
    for (int si = 0; si < nsys; si++) {
        Sys *s = &sys[si]; if (!s->lib || s->folder[0] == '_') continue;
        for (int i = 0; i < s->n && v->n < MAXFAV; i++) {
            Meta *m = meta_find(s->file[i]); if (!m || !m->genre[0] || strcasecmp(gnorm(m->genre), gens[gi].name)) continue;
            int j = v->n++; v->file[j] = s->file[i]; v->title[j] = s->title[i]; v->gcore[j] = s->gcore[i]; v->fold[j] = s->folder;
        }
    }
    snprintf(v->label, sizeof v->label, "%s: %s", lang_en ? "Genre" : "장르", lang_en ? gens[gi].name : genre_ko(gens[gi].name));
    return v->n;
}
// returns 1 = leave the picker, 2 = a genre was chosen (open its list)
static int genre_key(int k) {
    if (k == SDL_SCANCODE_B || k == SDL_SCANCODE_1) return 1;
    if (!ngen) return 0;
    if (k == SDL_SCANCODE_DOWN) g_sel = (g_sel + 1) % ngen; else if (k == SDL_SCANCODE_UP) g_sel = (g_sel + ngen - 1) % ngen;
    else if (k == SDL_SCANCODE_RIGHT) { g_sel += 8; if (g_sel >= ngen) g_sel = ngen - 1; } else if (k == SDL_SCANCODE_LEFT) { g_sel -= 8; if (g_sel < 0) g_sel = 0; }
    else if (k == SDL_SCANCODE_A) return genre_fill(g_sel) > 0 ? 2 : 0;
    if (g_sel < g_top) g_top = g_sel; if (g_sel >= g_top + 9) g_top = g_sel - 8;
    return 0;
}
static void draw_genres(void) {
    draw_background(); draw_topbar("장르별 찾기");
    if (!ngen) { text_c("게임 정보가 없습니다", 640, 300, 30, C_DIM, 800); draw_footer(NULL, "뒤로", NULL); draw_noise(); draw_crt(); return; }
    for (int r = 0; r < 9; r++) {
        int i = g_top + r; if (i >= ngen) break; int y = 100 + r * 62, on = i == g_sel;
        rbox(300, y, 680, 54, 12, on ? alpha(C_ROW, 255) : C_PANEL); if (on) rect(304, y + 8, 5, 38, C_YL);
        const char *nm = lang_en ? gens[i].name : genre_ko(gens[i].name);
        text(nm, 340, y + 8, 28, on ? C_YL : C_TXT, 0);
        char c[24]; snprintf(c, sizeof c, "%d", gens[i].n); int w = text_w(c, 26); text(c, 950 - w, y + 10, 26, on ? C_CY : C_DIM, 0);
    }
    draw_footer("열기", "뒤로", NULL); draw_noise(); draw_crt();
}

// ---------- idle (attract) screen ----------

static void draw_idle(Uint32 now) {
    rect(0, 0, W, H, C_BLACK);
    unsigned n = now / 7000; int px = 640 + (int)((n * 397u) % 360) - 180, py = 300 + (int)((n * 211u) % 160) - 80;
    float k = (now % 7000) / 7000.0f; float a = k < 0.12f ? k / 0.12f : k > 0.88f ? (1.0f - k) / 0.12f : 1.0f;      // fade in / out at every move
    Col dim = alpha(C_PK, (int)(200 * a)); if ((now / 600) % 2 == 0) neon_c("INSERT COIN", px, py, 64, dim, 900);
    text_c("아무 버튼이나 누르세요", px, py + 90, 22, alpha(C_DIM, (int)(170 * a)), 600);
    coin(px - 250, py + 18, 22); bulbs(px - 260, py + 150, 520, 14, alpha(C_YL, (int)(140 * a)), (int)(now / 500) & 1);
    draw_noise();
}
