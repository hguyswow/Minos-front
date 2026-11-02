// Host test for front/front_keys.inc: builds the RetroArch settings of a layout.  usage: test_keys CORE.so ROMFILE "spec" OUTCFG
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
static char card[256] = "/mnt/f";
#define LOG(...) do { fprintf(stderr, __VA_ARGS__); fputc('\n', stderr); } while (0)
static int ld_lines(const char *name, char **a, int max) { (void)name; (void)a; (void)max; return 0; }
static FILE *tmp_open(const char *name, char *t, size_t tn) { (void)name; (void)t; (void)tn; return NULL; }
static void tmp_done(FILE *f, const char *name, const char *t) { (void)f; (void)name; (void)t; }
#include "front/front_keys.inc"
int main(int c, char **v) {
    if (c < 5) return 1;
    remove(v[4]);
    int r = km_apply(v[4], v[3], v[1], v[2]);
    printf("applied=%d\n", r);
    Logi L; logi_parse("B:Button A|Y:Button B|X:Button C|A:Button D|", &L); int m[6]; spec_to_masks(v[3], &L, m); char out[120]; masks_to_spec(m, &L, out, sizeof out);
    printf("roundtrip: %s\n", out);
    return 0;
}
