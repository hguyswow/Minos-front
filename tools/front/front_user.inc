// front_user.inc - MinosFront's own small user data (all in <card>/pandory/front/):
//   favorites.txt / recent.txt   one game file name per line
//   last.cfg                     last system + list position per system
//   game_settings.tsv            per-game screen override: file <TAB> stretch <TAB> smooth   (true / false / empty = stock setting)
// Files are written only when something changes (favourite toggled, game started, list left, settings closed) to spare the card.
static void upath(char *b, size_t n, const char *name) { snprintf(b, n, "%s/pandory/front/%s", card, name); }
static int ld_lines(const char *name, char **a, int max) {
    char p[400]; upath(p, sizeof p, name); FILE *f = fopen(p, "r"); int n = 0; if (!f) return 0;
    char l[400]; while (n < max && fgets(l, sizeof l, f)) { size_t k = strlen(l); while (k && (l[k - 1] == '\n' || l[k - 1] == '\r')) l[--k] = 0; if (k) a[n++] = strdup(l); }
    fclose(f); return n;
}
static int test_mode(void) { return getenv("MINOS_KEYS") || getenv("MINOS_SNAP"); }   // headless tests must never change the card
// Pandory's menu music (mplayer) keeps the sound device busy: stop it so games get sound and the front is quiet.
static void kill_music(void) { if (test_mode()) return; system("killall mplayer >/dev/null 2>&1; sleep 0.3; killall -9 mplayer >/dev/null 2>&1"); }
static FILE *tmp_open(const char *name, char *t, size_t tn) { if (test_mode()) return NULL; char p[400]; upath(p, sizeof p, name); snprintf(t, tn, "%s.tmp", p); return fopen(t, "w"); }
static void tmp_done(FILE *f, const char *name, const char *t) { char p[400]; upath(p, sizeof p, name); fflush(f); fclose(f); if (rename(t, p) != 0) LOG("rename %s failed", name); }

#define MAXFAV 800
#define MAXREC 30
static char *favs[MAXFAV]; static int nfav;
static char *recent[MAXREC]; static int nrecent;
static int str_idx(char **a, int n, const char *f) { for (int i = 0; i < n; i++) if (!strcmp(a[i], f)) return i; return -1; }
static int fav_has(const char *f) { return str_idx(favs, nfav, f) >= 0; }
static void put_front(char **a, int *n, int max, const char *f) {            // newest first, no duplicates
    int i = str_idx(a, *n, f); if (i >= 0) { char *t = a[i]; memmove(a + 1, a, (size_t)i * sizeof(char *)); a[0] = t; return; }
    if (*n >= max) free(a[--*n]); memmove(a + 1, a, (size_t)*n * sizeof(char *)); a[0] = strdup(f); (*n)++;
}
static void lines_save(const char *name, char **a, int n) { char t[420]; FILE *f = tmp_open(name, t, sizeof t); if (!f) return; for (int i = 0; i < n; i++) fprintf(f, "%s\n", a[i]); tmp_done(f, name, t); }
static void fav_toggle(const char *f) {
    int i = str_idx(favs, nfav, f);
    if (i >= 0) { free(favs[i]); memmove(favs + i, favs + i + 1, (size_t)(nfav - i - 1) * sizeof(char *)); nfav--; } else put_front(favs, &nfav, MAXFAV, f);
    lines_save("favorites.txt", favs, nfav);
}
#include "front_plays.inc"
static void recent_push(const char *f) { put_front(recent, &nrecent, MAXREC, f); lines_save("recent.txt", recent, nrecent); plays_inc(f); }

// per-game screen overrides
typedef struct { char file[120]; char stretch[8], smooth[8], resume[8]; } GS;
static int idle_sec = 120;   // front.cfg idle=SECONDS (0 = off)
static int game_vol = 0;   // front.cfg game_vol= : RetroArch gain in dB for every game
static int resume_def = 1;   // front.cfg: resume=0 turns the automatic resume off
static GS gsv[2000]; static int ngs;
static GS *gs_find(const char *f) { for (int i = 0; i < ngs; i++) if (!strcmp(gsv[i].file, f)) return &gsv[i]; return NULL; }
static void gs_save(void) {
    char t[420]; FILE *f = tmp_open("game_settings.tsv", t, sizeof t); if (!f) return;
    for (int i = 0; i < ngs; i++) fprintf(f, "%s\t%s\t%s\t%s\n", gsv[i].file, gsv[i].stretch, gsv[i].smooth, gsv[i].resume);
    tmp_done(f, "game_settings.tsv", t);
}
static void gs_load(void) {
    char *a[2000]; int n = ld_lines("game_settings.tsv", a, 2000);
    for (int i = 0; i < n; i++) {
        char *c1 = strchr(a[i], '\t'); if (!c1 || ngs >= 2000) { free(a[i]); continue; } *c1++ = 0; char *c2 = strchr(c1, '\t'); char *c3 = NULL; if (c2) { *c2++ = 0; c3 = strchr(c2, '\t'); if (c3) *c3++ = 0; }
        GS *g = &gsv[ngs++]; snprintf(g->file, sizeof g->file, "%s", a[i]); g->stretch[0] = g->smooth[0] = g->resume[0] = 0; rs_val(g->stretch, c1); if (c2) rs_val(g->smooth, c2); if (c3) rs_val(g->resume, c3); free(a[i]);
    }
}
static void gs_set(const char *file, const char *st, const char *sm, const char *rs) {
    GS *g = gs_find(file);
    if (!st[0] && !sm[0] && !rs[0]) { if (g) { *g = gsv[--ngs]; gs_save(); } return; }
    if (!g) { if (ngs >= 2000) return; g = &gsv[ngs++]; snprintf(g->file, sizeof g->file, "%s", file); }
    snprintf(g->stretch, 8, "%s", st); snprintf(g->smooth, 8, "%s", sm); snprintf(g->resume, 8, "%s", rs); gs_save();
}
static void apply_gs(const char *file, Disp *d) { GS *g = gs_find(file); if (!g) return; if (g->stretch[0]) snprintf(d->stretch, 8, "%s", g->stretch); if (g->smooth[0]) snprintf(d->smooth, 8, "%s", g->smooth); }

// last position
static char lastsys[40]; static struct { char f[40]; int sel; } posv[MAXSYS + 8]; static int nposv;
static int pos_get(const char *f) { for (int i = 0; i < nposv; i++) if (!strcmp(posv[i].f, f)) return posv[i].sel; return 0; }
static void pos_set(const char *f, int sel) {
    for (int i = 0; i < nposv; i++) if (!strcmp(posv[i].f, f)) { posv[i].sel = sel; return; }
    if (nposv < MAXSYS + 8) { snprintf(posv[nposv].f, 40, "%s", f); posv[nposv++].sel = sel; }
}
static void pos_save(void) {
    char t[420]; FILE *f = tmp_open("last.cfg", t, sizeof t); if (!f) return;
    fprintf(f, "last=%s\n", lastsys); for (int i = 0; i < nposv; i++) fprintf(f, "sel.%s=%d\n", posv[i].f, posv[i].sel);
    tmp_done(f, "last.cfg", t);
}
static void pos_load(void) {
    char *a[100]; int n = ld_lines("last.cfg", a, 100);
    for (int i = 0; i < n; i++) {
        if (!strncmp(a[i], "last=", 5)) snprintf(lastsys, sizeof lastsys, "%s", a[i] + 5);
        else if (!strncmp(a[i], "sel.", 4)) { char *eq = strchr(a[i], '='); if (eq) { *eq = 0; pos_set(a[i] + 4, atoi(eq + 1)); } }
        free(a[i]);
    }
}

// first-letter groups for the quick jump (D key)
static const char *group_of(const char *t) {
    static const char *CHO[] = {"ㄱ","ㄱ","ㄴ","ㄷ","ㄷ","ㄹ","ㅁ","ㅂ","ㅂ","ㅅ","ㅅ","ㅇ","ㅈ","ㅈ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"};
    const char *p = t; int cp = utf8(&p);
    if (cp >= 0xAC00 && cp <= 0xD7A3) return CHO[(cp - 0xAC00) / 588];
    if ((cp >= 'A' && cp <= 'Z') || (cp >= 'a' && cp <= 'z')) return "A-Z";
    return "0-9";
}
static int jump_group(Sys *s, int sel) {      // next entry whose group differs; wraps to the top
    if (s->n < 2) return sel; const char *g = group_of(s->title[sel]);
    for (int i = sel + 1; i < s->n; i++) if (strcmp(group_of(s->title[i]), g)) return i;
    return 0;
}

// virtual systems: recent games / favourites (library games only)
static int vi_fav = -1, vi_rec = -1;
static void make_virtual(const char *folder, const char *label, int *vi) {
    if (nsys >= MAXSYS) return; Sys *v = &sys[nsys]; *vi = nsys++; memset(v, 0, sizeof *v); v->lib = 1;
    snprintf(v->folder, sizeof v->folder, "%s", folder); snprintf(v->label, sizeof v->label, "%s", label);
    v->file = calloc(MAXFAV, sizeof(char *)); v->title = calloc(MAXFAV, sizeof(char *)); v->gcore = calloc(MAXFAV, sizeof(char *)); v->fold = calloc(MAXFAV, sizeof(char *));
}
static void fill_virtual(int vi, char **names, int cnt) {
    if (vi < 0) return; Sys *v = &sys[vi]; v->n = 0;
    for (int k = 0; k < cnt; k++)
        for (int si = 0; si < nsys; si++) {
            Sys *s = &sys[si]; if (!s->lib || s->folder[0] == '_') continue; int f = -1;
            for (int i = 0; i < s->n; i++) if (!strcmp(s->file[i], names[k])) { f = i; break; }
            if (f >= 0) { int j = v->n++; v->file[j] = s->file[f]; v->title[j] = s->title[f]; v->gcore[j] = s->gcore[f]; v->fold[j] = s->folder; break; }
        }
}
static void refill_virtual(void) { fill_virtual(vi_fav, favs, nfav); fill_virtual(vi_rec, recent, nrecent); char *tn[40]; int tc = plays_top(tn, 40); fill_virtual(vi_top, tn, tc); }
static void rebuild_show(int *show, int *nshow, int *cur) {
    int keep = *nshow ? show[*cur] : -1; *nshow = 0;
    for (int i = 0; i < nsys; i++) if (sys[i].n > 0 || !strcmp(sys[i].folder, "_settings") || !strcmp(sys[i].folder, "_prefs") || !strcmp(sys[i].folder, "_genre") || !strcmp(sys[i].folder, "_keytest") || !strcmp(sys[i].folder, "_orig")) show[(*nshow)++] = i;
    *cur = 0; for (int j = 0; j < *nshow; j++) if (show[j] == keep) *cur = j;
}

// ---------- waiting for RetroArch, with a safety exit ----------
// Holding Start alone for quit_hold seconds (front.cfg: quit_hold=4, 0 = off) ends RetroArch (SIGTERM), also from its menu or any
// text screen it may be stuck in. The keys are read straight from /dev/input (read-only, RetroArch keeps working normally).
#include <signal.h>
#include <errno.h>
#include <time.h>
static int quit_hold = 4;
static double now_s(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec / 1e9; }
static void wait_ra(pid_t pid) {
    int fd[8], nfd = 0; char dp[40];
    for (int i = 0; i < 8; i++) { snprintf(dp, sizeof dp, "/dev/input/event%d", i); int f = open(dp, O_RDONLY | O_NONBLOCK); if (f >= 0) fd[nfd++] = f; }
    static unsigned char down[768]; memset(down, 0, sizeof down); int ndown = 0; double t_start = 0, t_term = 0; int termed = 0;
    for (;;) {
        int st; pid_t r = waitpid(pid, &st, WNOHANG);
        if (r == pid) { LOG("ra exited status=%d", st); break; } if (r < 0 && errno != EINTR) break;
        for (int k = 0; k < nfd; k++) {
            struct { int32_t sec, usec; uint16_t type, code; int32_t value; } ev;
            while (read(fd[k], &ev, sizeof ev) == (ssize_t)sizeof ev) {
                if (ev.type != 1 || ev.code >= 768 || ev.value == 2) continue;
                if (ev.value == 1 && !down[ev.code]) { down[ev.code] = 1; ndown++; } else if (ev.value == 0 && down[ev.code]) { down[ev.code] = 0; ndown--; }
                t_start = (ndown == 1 && down[2]) ? now_s() : 0;                  // KEY_1 = Start, alone
            }
        }
        if (quit_hold > 0 && t_start > 0 && !termed && now_s() - t_start >= quit_hold) { LOG("Start held %ds -> ending RetroArch", quit_hold); kill(pid, SIGTERM); termed = 1; t_term = now_s(); }
        if (termed && now_s() - t_term > 6) { LOG("RetroArch did not end -> SIGKILL"); kill(pid, SIGKILL); t_term = now_s() + 1000; }
        usleep(40000);
    }
    for (int k = 0; k < nfd; k++) close(fd[k]);
}

// RetroArch rewrites its whole ra.cfg every time it ends. A copy of the last good one is kept (ra.cfg.good); if ra.cfg ever looks broken
// (cut short by a power loss) it is restored from that copy at the next start.
static long file_size(const char *p) { struct stat st; return stat(p, &st) == 0 ? (long)st.st_size : -1; }
static int cfg_sane(const char *p) {
    long n = file_size(p); if (n < 20000 || n > 1000000) return 0;
    FILE *f = fopen(p, "rb"); if (!f) return 0; char *b = malloc((size_t)n + 1); size_t r = fread(b, 1, (size_t)n, f); fclose(f); b[r] = 0;
    int ok = strstr(b, "video_driver") && strstr(b, "input_player1_b") && strstr(b, "audio_driver") && b[r > 0 ? r - 1 : 0] == '\n'; free(b); return ok;
}
static int copy_file(const char *from, const char *to) {
    FILE *i = fopen(from, "rb"); if (!i) return 0; char t[420]; snprintf(t, sizeof t, "%s.tmp", to); FILE *o = fopen(t, "wb"); if (!o) { fclose(i); return 0; }
    char buf[8192]; size_t n; int ok = 1; while ((n = fread(buf, 1, sizeof buf, i)) > 0) if (fwrite(buf, 1, n, o) != n) ok = 0; fclose(i); fflush(o); fclose(o);
    if (!ok) { remove(t); return 0; } return rename(t, to) == 0;
}
// One-generation backup of the user files: copied at every start; a file that is missing or empty is restored from the copy.
static void copy_raw(const char *from, const char *to) {
    FILE *a = fopen(from, "rb"); if (!a) return; FILE *b = fopen(to, "wb"); if (!b) { fclose(a); return; }
    char buf[4096]; size_t n; while ((n = fread(buf, 1, sizeof buf, a)) > 0) fwrite(buf, 1, n, b); fclose(a); fclose(b);
}
static void backup_user(void) {
    if (test_mode()) return;
    static const char *names[] = { "favorites.txt", "recent.txt", "last.cfg", "game_settings.tsv", "keymaps.tsv", "lang.txt", "front.cfg", "plays.tsv" };
    char dir[400]; upath(dir, sizeof dir, "backup"); mkdir(dir, 0755);
    for (unsigned i = 0; i < sizeof names / sizeof *names; i++) {
        char src[400], bak[420]; upath(src, sizeof src, names[i]); snprintf(bak, sizeof bak, "%s/%s", dir, names[i]);
        struct stat s, b;
        if (stat(src, &s) == 0 && s.st_size > 0) copy_raw(src, bak);
        else if (stat(bak, &b) == 0 && b.st_size > 0) { LOG("restoring %s from backup", names[i]); copy_raw(bak, src); }
    }
}
static void crash_exit(int sig) { (void)sig; _exit(70); }

// Game info (year / maker / genre) from pandory/meta.tsv, made by tools/build_meta.py.
typedef struct { char *file, *year, *maker, *genre; } Meta;
static Meta *metas; static int nmeta;
static void meta_load(void) {
    char p[400]; snprintf(p, sizeof p, "%s/pandory/meta.tsv", card); FILE *f = fopen(p, "r"); if (!f) return;
    fseek(f, 0, SEEK_END); long sz = ftell(f); fseek(f, 0, SEEK_SET); if (sz <= 0 || sz > 4 * 1024 * 1024) { fclose(f); return; }
    char *buf = malloc((size_t)sz + 1); size_t r = fread(buf, 1, (size_t)sz, f); fclose(f); buf[r] = 0;
    int cap = 0; for (char *q = buf; *q; q++) if (*q == '\n') cap++;
    metas = calloc((size_t)cap + 1, sizeof(Meta));
    for (char *q = buf; *q; ) {
        char *nl = strchr(q, '\n'); if (nl) *nl = 0;
        char *c[4] = {q, "", "", ""}; int nc = 1;
        for (char *t2 = q; *t2 && nc < 4; t2++) if (*t2 == '\t') { *t2 = 0; c[nc++] = t2 + 1; }
        if (nc >= 2) { Meta *m = &metas[nmeta++]; m->file = strdup(c[0]); m->year = strdup(c[1]); m->maker = strdup(c[2]); m->genre = strdup(c[3]); }
        if (!nl) break; q = nl + 1;
    }
    free(buf); LOG("meta: %d games", nmeta);
}
static Meta *meta_find(const char *file) { for (int i = 0; i < nmeta; i++) if (!strcmp(metas[i].file, file)) return &metas[i]; return NULL; }
// "1990 · Capcom · 슈팅" (genre in Korean while the UI is Korean)
static const char *genre_ko(const char *g) {
    static const char *tb[][2] = { {"Shooter", "슈팅"}, {"Fighter", "대전 격투"}, {"Fighting", "대전 격투"}, {"Platform", "플랫폼 액션"}, {"Action", "액션"}, {"Beat'em Up", "벨트스크롤 액션"}, {"Puzzle", "퍼즐"},
        {"Driving", "레이싱"}, {"Racing", "레이싱"}, {"Sports", "스포츠"}, {"Maze", "미로"}, {"Ball & Paddle", "벽돌깨기"}, {"Climbing", "클라이밍"}, {"Mahjong", "마작"}, {"Quiz", "퀴즈"},
        {"RPG", "롤플레잉"}, {"Role-Playing", "롤플레잉"}, {"Adventure", "어드벤처"}, {"Strategy", "전략"}, {"Simulation", "시뮬레이션"}, {"Compilation", "모음집"}, {"Casino", "카지노"},
        {"Board Game", "보드 게임"}, {"Tabletop", "테이블"}, {"Rhythm", "리듬"}, {"Misc.", "기타"}, {"Educational", "교육"}, {"Fishing", "낚시"} };
    for (unsigned i = 0; i < sizeof tb / sizeof *tb; i++) if (!strcasecmp(g, tb[i][0])) return tb[i][1];
    return g;
}
static void meta_line(const char *file, char *out, size_t n) {
    out[0] = 0; Meta *m = meta_find(file); if (!m) return;
    const char *g = (m->genre[0] && !lang_en) ? genre_ko(m->genre) : m->genre;
    snprintf(out, n, "%s%s%s%s%s", m->year, (m->year[0] && (m->maker[0] || g[0])) ? "  ·  " : "", m->maker, (m->maker[0] && g[0]) ? "  ·  " : "", g);
}

static void protect_cfg(void) {
    if (test_mode()) return;
    char c[320], g[330]; snprintf(c, sizeof c, "%s/pandory/ra/ra.cfg", card); snprintf(g, sizeof g, "%s.good", c);
    if (cfg_sane(c)) { if (file_size(g) != file_size(c) || !cfg_sane(g)) { if (copy_file(c, g)) LOG("ra.cfg: good copy updated"); } else {
            /* same size: compare content, rewrite only if different */
            FILE *a = fopen(c, "rb"), *b = fopen(g, "rb"); int same = 1; if (a && b) { int x, y; while ((x = fgetc(a)) == (y = fgetc(b))) if (x == EOF) break; same = (x == y); } if (a) fclose(a); if (b) fclose(b);
            if (!same && copy_file(c, g)) LOG("ra.cfg: good copy updated"); } }
    else if (cfg_sane(g)) { copy_file(g, c); LOG("ra.cfg looked broken -> restored from ra.cfg.good"); }
    else LOG("ra.cfg: no good copy to restore from");
}

// ---------- language (Korean / English) ----------
// English game names for the arcade list come from fba2012.txt / mame2003.txt on the card; the other lists keep their Korean names.
typedef struct { char *name, *title; } EnName;
static EnName *enm; static int nenm;
static int en_cmp(const void *a, const void *b) { return strcmp(((const EnName *)a)->name, ((const EnName *)b)->name); }
static void en_read(const char *fn) {
    char p[300]; snprintf(p, sizeof p, "%s/%s", card, fn); FILE *f = fopen(p, "r"); if (!f) return; char l[600];
    while (fgets(l, sizeof l, f)) {
        char *s = l; while (*s == ' ' || *s == '\t') s++; char *e = s; while (*e && *e != ' ' && *e != '\t' && *e != '\n') e++; if (e == s) continue;
        char nm[80]; size_t nl = (size_t)(e - s); if (nl >= sizeof nm) continue; memcpy(nm, s, nl); nm[nl] = 0;
        s = e; while (*s == ' ' || *s == '\t') s++; size_t tl = strlen(s); while (tl && (s[tl - 1] == '\n' || s[tl - 1] == '\r' || s[tl - 1] == ' ')) s[--tl] = 0;
        if (tl >= 2 && s[0] == '"' && s[tl - 1] == '"') { s[--tl] = 0; s++; }
        if (!*s) continue; for (char *c = nm; *c; c++) if (*c >= 'A' && *c <= 'Z') *c += 32;
        if (nenm % 4096 == 0) enm = realloc(enm, (size_t)(nenm + 4096) * sizeof *enm);
        enm[nenm].name = strdup(nm); enm[nenm].title = strdup(s); nenm++;
    }
    fclose(f);
}
static void en_read_tsv(const char *fn) {           // names_en.tsv: file <TAB> english title (made by tools/build_en_names.py)
    char p[300]; snprintf(p, sizeof p, "%s/pandory/%s", card, fn); FILE *f = fopen(p, "r"); if (!f) return; char l[600];
    while (fgets(l, sizeof l, f)) {
        char *t = strchr(l, '\t'); if (!t) continue; *t++ = 0; size_t tl = strlen(t); while (tl && (t[tl - 1] == '\n' || t[tl - 1] == '\r')) t[--tl] = 0; if (!tl) continue;
        char *dot = strrchr(l, '.'); if (dot) *dot = 0; for (char *c = l; *c; c++) if (*c >= 'A' && *c <= 'Z') *c += 32;
        if (nenm % 4096 == 0) enm = realloc(enm, (size_t)(nenm + 4096) * sizeof *enm);
        enm[nenm].name = strdup(l); enm[nenm].title = strdup(t); nenm++;
    }
    fclose(f);
}
// Revised Romanization of Korean (simplified), used when no English name is known, so that no Hangul is left in English mode.
static char *romanize(const char *ko) {
    static const char *L[] = {"g", "kk", "n", "d", "tt", "r", "m", "b", "pp", "s", "ss", "", "j", "jj", "ch", "k", "t", "p", "h"};
    static const char *V[] = {"a", "ae", "ya", "yae", "eo", "e", "yeo", "ye", "o", "wa", "wae", "oe", "yo", "u", "wo", "we", "wi", "yu", "eu", "ui", "i"};
    static const char *T[] = {"", "k", "k", "ks", "n", "nj", "nh", "t", "l", "lk", "lm", "lb", "ls", "lt", "lp", "lh", "m", "p", "ps", "t", "t", "ng", "t", "t", "k", "t", "p", "t"};
    char *o = malloc(strlen(ko) * 4 + 8); size_t n = 0; int newword = 1; const char *p = ko;
    while (*p) {
        int cp = utf8(&p);
        if (cp >= 0xAC00 && cp <= 0xD7A3) { int s = cp - 0xAC00; const char *a = L[s / 588], *b = V[(s % 588) / 28], *c = T[s % 28]; char syl[16]; snprintf(syl, sizeof syl, "%s%s%s", a, b, c);
            if (newword && syl[0] >= 'a' && syl[0] <= 'z') syl[0] -= 32; n += (size_t)snprintf(o + n, 16, "%s", syl); newword = 0; }
        else if (cp < 0x80) { o[n++] = (char)cp; newword = (cp == ' ' || cp == '-' || cp == '(' ); }
        else { o[n++] = '?'; }
    }
    o[n] = 0; return o;
}
static const char *en_title(const char *file) {
    char b[120]; snprintf(b, sizeof b, "%s", file); char *dot = strrchr(b, '.'); if (dot) *dot = 0; for (char *c = b; *c; c++) if (*c >= 'A' && *c <= 'Z') *c += 32;
    EnName key = {b, NULL}; EnName *r = bsearch(&key, enm, (size_t)nenm, sizeof *enm, en_cmp); return r ? r->title : NULL;
}
static int ci_cmp(const char *a, const char *b) { return strcasecmp(a, b); }
static Sys *sort_s; static char **sort_t;
static int idx_cmp(const void *a, const void *b) { return ci_cmp(sort_t[*(const int *)a], sort_t[*(const int *)b]); }
static void set_lang(int en) {
    if (en && !enm) { en_read("fba2012.txt"); en_read("mame2003.txt"); en_read_tsv("names_en.tsv"); qsort(enm, (size_t)nenm, sizeof *enm, en_cmp); LOG("english names: %d", nenm); }
    lang_en = en;
    for (int si = 0; si < nsys; si++) {
        Sys *s = &sys[si]; if (!s->lib || s->folder[0] == '_' || s->n < 1) continue;
        if (!s->ofile) { s->ofile = malloc((size_t)s->n * sizeof(char *)); s->otitle = malloc((size_t)s->n * sizeof(char *)); s->ogcore = malloc((size_t)s->n * sizeof(char *));
            memcpy(s->ofile, s->file, (size_t)s->n * sizeof(char *)); memcpy(s->otitle, s->title, (size_t)s->n * sizeof(char *)); memcpy(s->ogcore, s->gcore, (size_t)s->n * sizeof(char *)); }
        if (!en) { memcpy(s->file, s->ofile, (size_t)s->n * sizeof(char *)); memcpy(s->title, s->otitle, (size_t)s->n * sizeof(char *)); memcpy(s->gcore, s->ogcore, (size_t)s->n * sizeof(char *)); continue; }
        char **et = malloc((size_t)s->n * sizeof(char *)); int *ix = malloc((size_t)s->n * sizeof(int));
        for (int i = 0; i < s->n; i++) { const char *t = en_title(s->ofile[i]); if (!t) { if (!strcmp(s->folder, "arcade")) { char *b = strdup(s->ofile[i]); char *d = strrchr(b, '.'); if (d) *d = 0; t = b; } else t = romanize(s->otitle[i]); } et[i] = (char *)t; ix[i] = i; }
        sort_t = et; qsort(ix, (size_t)s->n, sizeof(int), idx_cmp);
        for (int i = 0; i < s->n; i++) { s->file[i] = s->ofile[ix[i]]; s->title[i] = et[ix[i]]; s->gcore[i] = s->ogcore[ix[i]]; }
        free(et); free(ix);
    }
    refill_virtual();
}
static void lang_save(void) { char t[420]; FILE *f = tmp_open("lang.txt", t, sizeof t); if (!f) return; fprintf(f, "%s\n", lang_en ? "en" : "ko"); tmp_done(f, "lang.txt", t); }
static int lang_load(void) { char *a[2]; int n = ld_lines("lang.txt", a, 2); int en = n > 0 && !strncmp(a[0], "en", 2); for (int i = 0; i < n; i++) free(a[i]); return en; }
