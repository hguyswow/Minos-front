// front_keys.inc - per-game / per-kind button layouts ("key maps") made in MinosFront.
//
// The device has six game buttons:   top row  B C D     bottom row  A E F      (keys b c d / a e f)
// A layout says, for each of them, which button(s) of the game it presses - one button, or several at once (e.g. Neo Geo "strong" = A+B).
// It is turned into RetroArch settings when the game starts:
//   * every game button gets the key of the physical button that should press it (input_player1_b = "d" ...);
//   * "one key presses two game buttons" uses RetroArch's input remap: spare RetroPad buttons (L3 R3 L2 R2) are bound to the same key and
//     remapped (.rmp file, written to /tmp) onto the extra game buttons.
// Data files:  pandory/buttons.tsv   file <TAB> core <TAB> "B:Button A|Y:Button B|..."   (button names each core reports; tools/desc_batch.sh)
//              pandory/front/keymaps.tsv   G|R <TAB> file or kind <TAB> "b=B+Y;c=X;d=A;a=B;e=L;f=R"
//  "R" = a whole kind of game (same core and same button names, e.g. all Neo Geo games).
#define MAXLG 10
typedef struct { int n; int id[MAXLG]; char name[MAXLG][48]; } Logi;          // the game's buttons, in the order the core lists them
static const char *PADN[] = {"B", "Y", "SELECT", "START", "UP", "DOWN", "LEFT", "RIGHT", "A", "X", "L", "R", "L2", "R2", "L3", "R3"};
static const char *PADCFG[] = {"b", "y", "select", "start", "up", "down", "left", "right", "a", "x", "l", "r", "l2", "r2", "l3", "r3"};
static const char *PK[6] = {"b", "c", "d", "a", "e", "f"};                      // physical buttons: top row b c d, bottom row a e f
static const char *STOCK_SPEC = "b=Y;c=X;d=A;a=B;e=L;f=R";                      // the stock mapping of this device
static int pad_id(const char *n) { for (int i = 0; i < 16; i++) if (!strcmp(PADN[i], n)) return i; return -1; }

typedef struct { char *file, *core, *desc; } BtnInfo;
static BtnInfo *bi; static int nbi, bi_loaded;
static void bi_load(void) {
    if (bi_loaded) return; bi_loaded = 1;
    char p[300]; snprintf(p, sizeof p, "%s/pandory/buttons.tsv", card); FILE *f = fopen(p, "r"); if (!f) { LOG("no buttons.tsv"); return; }
    fseek(f, 0, SEEK_END); long sz = ftell(f); fseek(f, 0, SEEK_SET); if (sz <= 0 || sz > 16 * 1024 * 1024) { fclose(f); return; }
    char *buf = malloc((size_t)sz + 1); size_t r = fread(buf, 1, (size_t)sz, f); fclose(f); buf[r] = 0;
    int cap = 0; for (char *q = buf; *q; q++) if (*q == '\n') cap++; bi = calloc((size_t)cap + 1, sizeof *bi);
    for (char *q = buf; *q; ) {
        char *nl = strchr(q, '\n'); if (nl) *nl = 0; size_t l = strlen(q); if (l && q[l - 1] == '\r') q[l - 1] = 0;
        char *t1 = strchr(q, '\t'); char *t2 = t1 ? strchr(t1 + 1, '\t') : NULL;
        if (t2) { *t1 = 0; *t2 = 0; bi[nbi].file = strdup(q); bi[nbi].core = strdup(t1 + 1); bi[nbi].desc = strdup(t2 + 1); nbi++; }
        if (!nl) break; q = nl + 1;
    }
    free(buf); LOG("buttons.tsv: %d games", nbi);
}
static BtnInfo *bi_find(const char *file) { bi_load(); for (int i = 0; i < nbi; i++) if (!strcmp(bi[i].file, file)) return &bi[i]; return NULL; }

static void logi_parse(const char *desc, Logi *L) {
    memset(L, 0, sizeof *L);
    if (desc && *desc) {
        char tmp[600], *s1 = NULL; snprintf(tmp, sizeof tmp, "%s", desc);
        for (char *tok = strtok_r(tmp, "|", &s1); tok && L->n < MAXLG; tok = strtok_r(NULL, "|", &s1)) {
            char *c = strchr(tok, ':'); if (!c) continue; *c = 0; int id = pad_id(tok); if (id < 0) continue;
            L->id[L->n] = id; snprintf(L->name[L->n], 48, "%s", c + 1); L->n++;
        }
    }
    if (L->n == 0) { static const int d[] = {0, 8, 1, 9, 10, 11}; for (int i = 0; i < 6; i++) { L->id[i] = d[i]; snprintf(L->name[i], 48, "%s", PADN[d[i]]); } L->n = 6; }
}
static const char *kname(const char *en) {                                     // short Korean names for the usual arcade button names
    static const char *T[][2] = {{"Weak Punch", "약손"}, {"Medium Punch", "중손"}, {"Strong Punch", "강손"}, {"Weak Kick", "약발"}, {"Medium Kick", "중발"}, {"Strong Kick", "강발"},
        {"Jump", "점프"}, {"Shot", "샷"}, {"Attack", "공격"}, {"Fire", "발사"}, {"Bomb", "폭탄"}, {"Start", "스타트"}, {"Coin", "코인"}, {"Punch", "주먹"}, {"Kick", "발"}, {"Special", "특수"}};
    for (unsigned i = 0; i < sizeof T / sizeof T[0]; i++) if (!strcmp(en, T[i][0])) return T[i][1];
    static char ring[4][64]; static int ri; const char *pre[] = {"Button ", "Fire "};
    for (int q = 0; q < 2; q++) { size_t l = strlen(pre[q]); if (!strncmp(en, pre[q], l) && strlen(en) < 8 + l) { char *o = ring[ri++ & 3]; snprintf(o, 64, "%s%s", q ? "발사" : "버튼", en + l); return o; } }
    return en;
}

// ----- stored layouts -----
typedef struct { char scope; char key[300]; char spec[100]; } KM;
static KM kmv[800]; static int nkm, km_loaded;
static void km_load(void) {
    if (km_loaded) return; km_loaded = 1; char *a[800]; int n = ld_lines("keymaps.tsv", a, 800);
    for (int i = 0; i < n; i++) {
        char *t1 = strchr(a[i], '\t'); char *t2 = t1 ? strchr(t1 + 1, '\t') : NULL;
        if (t2 && nkm < 800 && (a[i][0] == 'G' || a[i][0] == 'R')) { *t1 = 0; *t2 = 0; KM *k = &kmv[nkm++]; k->scope = a[i][0]; snprintf(k->key, sizeof k->key, "%s", t1 + 1); snprintf(k->spec, sizeof k->spec, "%s", t2 + 1); }
        free(a[i]);
    }
}
static void km_save(void) {
    char t[420]; FILE *f = tmp_open("keymaps.tsv", t, sizeof t); if (!f) return;
    for (int i = 0; i < nkm; i++) fprintf(f, "%c\t%s\t%s\n", kmv[i].scope, kmv[i].key, kmv[i].spec);
    tmp_done(f, "keymaps.tsv", t);
}
static KM *km_find(char scope, const char *key) { km_load(); for (int i = 0; i < nkm; i++) if (kmv[i].scope == scope && !strcmp(kmv[i].key, key)) return &kmv[i]; return NULL; }
static void km_set(char scope, const char *key, const char *spec) {             // spec NULL = delete
    KM *k = km_find(scope, key);
    if (!spec) { if (k) { *k = kmv[--nkm]; km_save(); } return; }
    if (!k) { if (nkm >= 800) return; k = &kmv[nkm++]; k->scope = scope; snprintf(k->key, sizeof k->key, "%s", key); }
    snprintf(k->spec, sizeof k->spec, "%s", spec); km_save();
}
static void group_key(const BtnInfo *b, const char *folder, char *out, size_t n) {
    if (b && b->desc[0]) snprintf(out, n, "%s|%s", b->core, b->desc); else snprintf(out, n, "%s|%s", b ? b->core : "?", folder);
}
static const char *km_resolve(const char *file, const char *gkey, char *which) {      // game layout > kind layout > none
    KM *k = km_find('G', file); if (k) { if (which) *which = 'G'; return k->spec; }
    k = km_find('R', gkey); if (k) { if (which) *which = 'R'; return k->spec; }
    if (which) *which = 0; return NULL;
}

// spec <-> masks (bit i = the game's i-th button, see Logi)
static void spec_to_masks(const char *spec, const Logi *L, int m[6]) {
    for (int i = 0; i < 6; i++) m[i] = 0;
    char tmp[120], *s1 = NULL; snprintf(tmp, sizeof tmp, "%s", spec);
    for (char *tok = strtok_r(tmp, ";", &s1); tok; tok = strtok_r(NULL, ";", &s1)) {
        char *eq = strchr(tok, '='); if (!eq) continue; *eq = 0; int p = -1; for (int i = 0; i < 6; i++) if (!strcmp(tok, PK[i])) p = i; if (p < 0) continue;
        char *s2 = NULL; for (char *o = strtok_r(eq + 1, "+", &s2); o; o = strtok_r(NULL, "+", &s2)) { int id = pad_id(o); for (int j = 0; j < L->n; j++) if (L->id[j] == id) m[p] |= 1 << j; }
    }
}
static void masks_to_spec(const int m[6], const Logi *L, char *out, size_t n) {
    out[0] = 0; size_t l = 0;
    for (int p = 0; p < 6; p++) {
        l += (size_t)snprintf(out + l, n - l, "%s%s=", p ? ";" : "", PK[p]); int first = 1;
        for (int j = 0; j < L->n; j++) if (m[p] & (1 << j)) { l += (size_t)snprintf(out + l, n - l, "%s%s", first ? "" : "+", PADN[L->id[j]]); first = 0; }
    }
}

// ----- turning a layout into RetroArch settings -----
static int core_libname(const char *corepath, char *out, size_t n) {              // the core's own name = the folder RetroArch looks into for remaps
    void *h = dlopen(corepath, RTLD_LAZY | RTLD_LOCAL); if (!h) return 0;
    typedef struct { const char *n, *v, *e; int fp, be; } SI; void (*gsi)(SI *) = (void (*)(SI *))dlsym(h, "retro_get_system_info"); int ok = 0;
    if (gsi) { SI si; memset(&si, 0, sizeof si); gsi(&si); if (si.n) { snprintf(out, n, "%s", si.n); ok = 1; } }
    dlclose(h); return ok;
}
// Appends the key settings to `ovr` and writes the remap file. Returns 1 when a layout was applied.
static int km_apply(const char *ovr, const char *spec, const char *corepath, const char *file) {
    int outs[6][10], nout[6]; memset(nout, 0, sizeof nout); int usedout[16]; memset(usedout, 0, sizeof usedout);
    { char tmp[120], *s1 = NULL; snprintf(tmp, sizeof tmp, "%s", spec);
      for (char *tok = strtok_r(tmp, ";", &s1); tok; tok = strtok_r(NULL, ";", &s1)) {
          char *eq = strchr(tok, '='); if (!eq) continue; *eq = 0; int p = -1; for (int i = 0; i < 6; i++) if (!strcmp(tok, PK[i])) p = i; if (p < 0) continue;
          char *s2 = NULL; for (char *o = strtok_r(eq + 1, "+", &s2); o; o = strtok_r(NULL, "+", &s2)) { int id = pad_id(o); if (id >= 0 && id != 2 && id != 3 && id < 16 && (id < 4 || id > 7) && nout[p] < 10) { outs[p][nout[p]++] = id; usedout[id] = 1; } } } }
    const char *bind[16]; int remap[16]; for (int i = 0; i < 16; i++) { bind[i] = NULL; remap[i] = i; }
    int spare[4], nspare = 0; { static const int cand[] = {14, 15, 12, 13}; for (int i = 0; i < 4; i++) if (!usedout[cand[i]]) spare[nspare++] = cand[i]; }
    int order[6], no = 0; for (int c = 1; c <= 10; c++) for (int p = 0; p < 6; p++) if (nout[p] == c) order[no++] = p;       // single-button keys first
    for (int oi = 0; oi < no; oi++) { int p = order[oi];
        for (int j = 0; j < nout[p]; j++) { int o = outs[p][j];
            if (!bind[o]) bind[o] = PK[p];
            else if (nspare > 0) { int s = spare[--nspare]; bind[s] = PK[p]; remap[s] = o; }
            else LOG("keymap: no spare button for %s on key %s", PADN[o], PK[p]); } }
    FILE *f = fopen(ovr, "a"); if (!f) return 0;
    fputs("input_remapping_directory = \"/tmp/minos_remap\"\ninput_remap_binds_enable = \"true\"\n", f);
    static const int ids[] = {0, 1, 8, 9, 10, 11, 12, 13, 14, 15};
    for (int i = 0; i < 10; i++) { int id = ids[i]; fprintf(f, "input_player1_%s = \"%s\"\n", PADCFG[id], bind[id] ? bind[id] : "nul"); }
    fclose(f);
    int anyrmp = 0; for (int i = 0; i < 16; i++) if (remap[i] != i) anyrmp = 1;
    if (anyrmp) {
        char lib[120]; if (!core_libname(corepath, lib, sizeof lib)) { LOG("keymap: core name unknown"); return 1; }
        char d1[200], d2[300], rp[420], base[200]; snprintf(base, sizeof base, "%s", file); char *dot = strrchr(base, '.'); if (dot) *dot = 0;
        snprintf(d1, sizeof d1, "/tmp/minos_remap"); mkdir(d1, 0777); snprintf(d2, sizeof d2, "%s/%s", d1, lib); mkdir(d2, 0777);
        snprintf(rp, sizeof rp, "%s/%s.rmp", d2, base); FILE *r = fopen(rp, "w");
        if (r) { for (int i = 0; i < 16; i++) if (remap[i] != i) fprintf(r, "input_player1_btn_%s = \"%d\"\n", PADCFG[i], remap[i]); fclose(r); LOG("keymap: remap file %s", rp); }
    }
    LOG("keymap applied: %s", spec); return 1;
}
