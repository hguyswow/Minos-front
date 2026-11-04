// front_bezel.inc - screen frames (RetroArch overlays) for games that run at their own ratio ("original").
// The frames are made by tools/make_bezels.py (pandory/bezel/bezel_<w>_<h>.png + .cfg); the ratio of every arcade game comes from pandory/aspects.tsv
// (tools/build_aspects.py).  RetroArch is told to use exactly the ratio of the frame's window, so the picture fills the window.

static int bezel_on = 1;                                   // front.cfg bezel: 0 off, 1 neon, 2 plain, 3 cabinet, 4 Korean titles, 5 arcade machines, 6 memories, 7 mixed (per game)
static const char *bezel_dir[] = {"", "bezel", "bezel_plain", "bezel_cabinet", "bezel_kor", "bezel_arcade", "bezel_memory"};
static const char *bezel_name[] = {"꺼짐", "네온", "단순", "오락실", "한글판", "아케이드", "추억", "섞어서"};
typedef struct { char *file; float r; } Asp;
static Asp *asps; static int nasp;

static void bezel_load(void) {
    if (bezel_on < 0 || bezel_on > 7) bezel_on = 1;
    char p[400]; snprintf(p, sizeof p, "%s/pandory/aspects.tsv", card); FILE *f = fopen(p, "r"); if (!f) return;
    int cap = 0; char l[200]; while (fgets(l, sizeof l, f)) cap++; rewind(f); asps = calloc((size_t)cap + 1, sizeof(Asp));
    while (fgets(l, sizeof l, f)) {
        char *t = strchr(l, '\t'); if (!t) continue; *t++ = 0; int a = 0, b = 0; if (sscanf(t, "%d:%d", &a, &b) != 2 || a <= 0 || b <= 0) continue;
        asps[nasp].file = strdup(l); asps[nasp].r = (float)a / (float)b; nasp++;
    }
    fclose(f); LOG("aspects: %d games", nasp);
}

// Appends the overlay settings for this game to the override file. Returns 1 when a frame is used.
static int bezel_apply(const char *ovr, const char *file, const char *folder, int forced) {     // forced >= 0: style chosen for this game
    int on = forced >= 0 ? forced : bezel_on; if (!on) return 0;
    int style = on; if (style == 7) { unsigned h = 5381; for (const char *c = file; *c; c++) h = h * 33 + (unsigned char)*c; style = 1 + (int)(h % 6); }
    float r = 4.0f / 3.0f;
    if (!strcmp(folder, "gba")) r = 1.5f; else if (!strcmp(folder, "gb") || !strcmp(folder, "gbc")) r = 10.0f / 9.0f;
    for (int i = 0; i < nasp; i++) if (!strcmp(asps[i].file, file)) { r = asps[i].r; break; }
    static const struct { const char *key; float r; } fr[] = { {"4_3", 4.0f / 3.0f}, {"3_4", 0.75f}, {"3_2", 1.5f}, {"10_9", 10.0f / 9.0f}, {"5_4", 1.25f} };
    int best = -1; float bd = 0.07f;
    for (int i = 0; i < 5; i++) { float d = r > fr[i].r ? r - fr[i].r : fr[i].r - r; if (d < bd) { bd = d; best = i; } }
    if (best < 0) return 0;                                  // wide / odd screens: no frame
    char cfg[400]; snprintf(cfg, sizeof cfg, "%s/pandory/%s/bezel_%s.cfg", card, bezel_dir[style], fr[best].key);
    struct stat st; if (stat(cfg, &st) != 0) return 0;
    FILE *f = fopen(ovr, "a"); if (!f) return 0;
    fprintf(f, "aspect_ratio_index = \"20\"\nvideo_aspect_ratio = \"%.6f\"\nvideo_scale_integer = \"false\"\n", fr[best].r);
    fprintf(f, "input_overlay = \"%s\"\ninput_overlay_enable = \"true\"\ninput_overlay_opacity = \"1.000000\"\ninput_overlay_scale_landscape = \"1.000000\"\ninput_overlay_hide_in_menu = \"true\"\n", cfg);
    fclose(f); LOG("bezel: %s for %s", fr[best].key, file); return 1;
}
