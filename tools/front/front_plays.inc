// front_plays.inc - play counts (pandory/front/plays.tsv, "file <TAB> count") for the "most played" list.
// Included from front_user.inc just before recent_push(), which counts every launch.

#define MAXPL 1500
static char *pl_file[MAXPL]; static int pl_cnt[MAXPL], npl;
static int vi_top = -1;                                    // the virtual "most played" system

static void plays_save(void) {
    char t[420]; FILE *f = tmp_open("plays.tsv", t, sizeof t); if (!f) return;
    for (int i = 0; i < npl; i++) fprintf(f, "%s\t%d\n", pl_file[i], pl_cnt[i]);
    tmp_done(f, "plays.tsv", t);
}
static void plays_load(void) {
    char p[400]; upath(p, sizeof p, "plays.tsv"); FILE *f = fopen(p, "r"); if (!f) return;
    char l[300];
    while (npl < MAXPL && fgets(l, sizeof l, f)) {
        char *t = strchr(l, '\t'); if (!t) continue; *t++ = 0;
        pl_file[npl] = strdup(l); pl_cnt[npl] = atoi(t); npl++;
    }
    fclose(f);
}
static void plays_inc(const char *file) {
    for (int i = 0; i < npl; i++) if (!strcmp(pl_file[i], file)) { pl_cnt[i]++; plays_save(); return; }
    if (npl < MAXPL) { pl_file[npl] = strdup(file); pl_cnt[npl] = 1; npl++; }
    plays_save();
}
// the most played games (played 2 times or more), most played first
static int plays_top(char **out, int max) {
    static int idx[MAXPL]; int n = 0;
    for (int i = 0; i < npl; i++) if (pl_cnt[i] >= 2) {
        int j = n++; while (j > 0 && pl_cnt[idx[j - 1]] < pl_cnt[i]) { idx[j] = idx[j - 1]; j--; } idx[j] = i;
    }
    if (n > max) n = max;
    for (int i = 0; i < n; i++) out[i] = pl_file[idx[i]];
    return n;
}
