// front_health.inc - card check at start-up (free space, write/read test) and the saved clock (the device has no battery clock:
// the last known time is kept in pandory/front/clock.txt and restored when the system time is older).
#include <sys/statvfs.h>
static char warn_msg[160];

static void card_check(void) {
    if (test_mode()) return;
    struct statvfs sv;
    if (statvfs(card, &sv) == 0) {
        double mb = (double)sv.f_bavail * (double)sv.f_frsize / 1048576.0;
        if (mb < 100) snprintf(warn_msg, sizeof warn_msg, lang_en ? "Card has only %d MB free (saving may fail)" : "카드 여유 공간이 %d MB 남았습니다 (저장이 실패할 수 있어요)", (int)mb);
    }
    char p[400]; snprintf(p, sizeof p, "%s/.minos_wtest", card); char b[512], r[512]; memset(b, 0x5A, sizeof b); memset(r, 0, sizeof r);
    int ok = 0; FILE *f = fopen(p, "wb");
    if (f) {
        ok = fwrite(b, 1, sizeof b, f) == sizeof b; ok = (fflush(f) == 0) && ok; fclose(f);
        f = fopen(p, "rb"); ok = ok && f && fread(r, 1, sizeof r, f) == sizeof r && !memcmp(b, r, sizeof b); if (f) fclose(f);
        remove(p);
    }
    if (!ok) snprintf(warn_msg, sizeof warn_msg, "%s", lang_en ? "Card write/read test failed (read-only or a bad card)" : "카드 쓰기/읽기 확인 실패 (읽기 전용이거나 카드 이상)");
    LOG("card check: %s", warn_msg[0] ? warn_msg : "ok");
}

static void clock_save(void) {
    if (test_mode()) return;
    time_t t = time(NULL); struct tm *l = localtime(&t); if (l->tm_year < 124) return;                // never store a clock that was not set
    char p[400]; upath(p, sizeof p, "clock.txt"); FILE *f = fopen(p, "w"); if (f) { fprintf(f, "%ld\n", (long)t); fclose(f); }
}
static void clock_restore(void) {
    if (test_mode()) return;
    char p[400]; upath(p, sizeof p, "clock.txt"); FILE *f = fopen(p, "r"); if (!f) return;
    long saved = 0; if (fscanf(f, "%ld", &saved) != 1) saved = 0; fclose(f);
    if (saved > 0 && (long)time(NULL) < saved) {
        time_t t = (time_t)saved; struct tm *g = gmtime(&t); char c[120];
        snprintf(c, sizeof c, "date -u -s \"%04d-%02d-%02d %02d:%02d:%02d\" >/dev/null 2>&1", g->tm_year + 1900, g->tm_mon + 1, g->tm_mday, g->tm_hour, g->tm_min, g->tm_sec);
        system(c); LOG("clock restored from clock.txt");
    }
}
