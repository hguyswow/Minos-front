// ra_settings.inc - reads the per-game / per-system / global display options from pandory.xml
// (the same file the PC editor writes) and writes a RetroArch override file for one game.
// Pure C, no SDL, so it can be tested on the PC (see test_ra_settings.c).
//
// Lookup order (matches the original Pandory binary: ROM entry -> CORE entry -> GENERIC entry):
//   <rom name="FILE">  >  <emulator folder="FOLDER">  >  <system><setting name=... value=...>
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { char stretch[8]; char smooth[8]; } Disp;   // each: "", "true" or "false"

static char *rs_slurp(const char *path, size_t *n) {
    FILE *f = fopen(path, "rb"); if (!f) return NULL;
    fseek(f, 0, SEEK_END); long sz = ftell(f); fseek(f, 0, SEEK_SET);
    if (sz < 0 || sz > 4 * 1024 * 1024) { fclose(f); return NULL; }
    char *b = malloc((size_t)sz + 1); if (!b) { fclose(f); return NULL; }
    size_t r = fread(b, 1, (size_t)sz, f); fclose(f); b[r] = 0; if (n) *n = r; return b;
}

static int rs_ws(char c) { return c == ' ' || c == '\t' || c == '\r' || c == '\n'; }

// p points at '<'. Returns the position just after the closing '>' (quoted values may contain '>').
static const char *rs_tag_end(const char *p, const char *end) {
    char q = 0;
    for (p++; p < end; p++) {
        if (q) { if (*p == q) q = 0; }
        else if (*p == '"' || *p == '\'') q = *p;
        else if (*p == '>') return p + 1;
    }
    return end;
}

// Is the tag starting at p (a '<') an opening/self-closing tag called `name`?
static int rs_is_tag(const char *p, const char *end, const char *name) {
    size_t n = strlen(name);
    if (p + 1 + n >= end || strncmp(p + 1, name, n)) return 0;
    char c = p[1 + n];
    return rs_ws(c) || c == '/' || c == '>';
}

// Reads NAME="value" (or 'value') from the tag [tag, tend). Walks the attributes one by one, so a
// value that merely contains the text of another attribute can never be mistaken for it. It also
// tolerates the missing space seen on the real card (`keymap="x"core="y"`).
static int rs_attr(const char *tag, const char *tend, const char *name, char *out, size_t cap) {
    size_t want = strlen(name);
    const char *p = tag + 1;
    while (p < tend && !rs_ws(*p) && *p != '>' && *p != '/') p++;            // skip the element name
    while (p < tend) {
        while (p < tend && rs_ws(*p)) p++;
        if (p >= tend || *p == '>') break;
        if (*p == '/') { p++; continue; }
        const char *ns = p;
        while (p < tend && (isalnum((unsigned char)*p) || *p == '_' || *p == '-' || *p == ':')) p++;
        size_t len = (size_t)(p - ns);
        if (len == 0) { p++; continue; }
        while (p < tend && rs_ws(*p)) p++;
        if (p >= tend || *p != '=') continue;
        p++;
        while (p < tend && rs_ws(*p)) p++;
        if (p >= tend || (*p != '"' && *p != '\'')) continue;
        char q = *p++; const char *vs = p;
        while (p < tend && *p != q) p++;
        if (p >= tend) return 0;                                             // unterminated value
        if (len == want && !strncmp(ns, name, len)) {
            size_t vl = (size_t)(p - vs); if (vl >= cap) vl = cap - 1;
            memcpy(out, vs, vl); out[vl] = 0; return 1;
        }
        p++;                                                                 // closing quote
    }
    return 0;
}

static void rs_val(char dst[8], const char *v) { if (!strcmp(v, "true") || !strcmp(v, "false")) snprintf(dst, 8, "%s", v); }

static void rs_pick(Disp *d, const char *tag, const char *tend) {
    char v[16];
    if (rs_attr(tag, tend, "stretchDisplay", v, sizeof v)) rs_val(d->stretch, v);
    if (rs_attr(tag, tend, "smoothPixels", v, sizeof v)) rs_val(d->smooth, v);
}

// Effective display options of one game. Comments are skipped.
static void xml_display(const char *xml_path, const char *folder, const char *file, Disp *out) {
    memset(out, 0, sizeof *out);
    size_t n = 0; char *buf = rs_slurp(xml_path, &n); if (!buf) return;
    const char *end = buf + n;
    Disp g, e, r; memset(&g, 0, sizeof g); memset(&e, 0, sizeof e); memset(&r, 0, sizeof r);
    int in_sys = 0;
    for (const char *p = buf; p < end;) {
        const char *lt = memchr(p, '<', (size_t)(end - p)); if (!lt) break;
        if (!strncmp(lt, "<!--", 4)) { const char *c = strstr(lt + 4, "-->"); p = c ? c + 3 : end; continue; }
        const char *te = rs_tag_end(lt, end);
        if (rs_is_tag(lt, end, "system")) in_sys = 1;
        else if (lt[1] == '/' && !strncmp(lt + 2, "system", 6)) in_sys = 0;
        else if (in_sys && rs_is_tag(lt, end, "setting")) {
            char nm[64], v[16];
            if (rs_attr(lt, te, "name", nm, sizeof nm) && rs_attr(lt, te, "value", v, sizeof v)) {
                if (!strcmp(nm, "stretchDisplay")) rs_val(g.stretch, v);
                else if (!strcmp(nm, "smoothPixels")) rs_val(g.smooth, v);
            }
        } else if (rs_is_tag(lt, end, "emulator")) {
            char fo[64]; if (rs_attr(lt, te, "folder", fo, sizeof fo) && !strcmp(fo, folder)) rs_pick(&e, lt, te);
        } else if (rs_is_tag(lt, end, "rom")) {
            char nm[300]; if (rs_attr(lt, te, "name", nm, sizeof nm) && !strcmp(nm, file)) rs_pick(&r, lt, te);
        }
        p = te;
    }
    snprintf(out->stretch, 8, "%s", r.stretch[0] ? r.stretch : e.stretch[0] ? e.stretch : g.stretch);
    snprintf(out->smooth, 8, "%s", r.smooth[0] ? r.smooth : e.smooth[0] ? e.smooth : g.smooth);
    free(buf);
}

// RetroArch 1.22.2: aspect_ratio_index 24 = Full (fill the screen), 22 = Core provided (the game's own ratio).
// skip_ratio != 0: leave the aspect ratio to ra.cfg (used to test whether changing it causes audio dropouts).
static int write_ra_override(const char *path, const Disp *d, int skip_ratio) {
    FILE *f = fopen(path, "w"); if (!f) return 0;
    if (skip_ratio) { /* keep ra.cfg's own aspect_ratio_index */ }
    else if (!strcmp(d->stretch, "true")) fputs("aspect_ratio_index = \"24\"\n", f);
    else if (!strcmp(d->stretch, "false")) fputs("aspect_ratio_index = \"22\"\n", f);
    if (!strcmp(d->smooth, "true")) fputs("video_smooth = \"true\"\n", f);
    else if (!strcmp(d->smooth, "false")) fputs("video_smooth = \"false\"\n", f);
    fclose(f); return 1;
}

// Appends the text file `src` (e.g. pandory/ra/layouts/genesis.cfg = per-system button layout) to `dst`. Missing file = nothing.
static void append_file(const char *dst, const char *src) {
    FILE *in = fopen(src, "rb"); if (!in) return;
    FILE *out = fopen(dst, "ab"); if (!out) { fclose(in); return; }
    char buf[1024]; size_t n; int last = '\n';
    while ((n = fread(buf, 1, sizeof buf, in)) > 0) { fwrite(buf, 1, n, out); last = buf[n - 1]; }
    if (last != '\n') fputc('\n', out);
    fclose(in); fclose(out);
}
