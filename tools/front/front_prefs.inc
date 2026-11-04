// front_prefs.inc - the "MinosFront settings" screen (language, quit-hold time, automatic resume, start-up front, volume, frame, idle screen,
// date and time, restore of a settings backup).
// Everything is stored in the card's pandory/front files (front.cfg, lang.txt, autostart); the volume is the system mixer.

static int pf_row, pf_vol = 55, pf_arm;
static int pf_sub;                                          // 0 = list, 1 = date/time editor, 2 = backup restore list
static int clk[5], clk_f;                                   // year month day hour minute, and the field being edited
static char rs_name[5][32], rs_date[5][24]; static int rs_n, rs_sel, rs_num[5], rs_arm;

// front.cfg: replace "key=value" (or append it); the other lines stay as they are.
static void cfg_set(const char *key, const char *val) {
    if (test_mode()) return;
    char p[400], t[420]; upath(p, sizeof p, "front.cfg"); snprintf(t, sizeof t, "%s.tmp", p);
    FILE *o = fopen(t, "w"); if (!o) return; int done = 0; size_t kl = strlen(key);
    FILE *i = fopen(p, "r");
    if (i) { char l[300]; while (fgets(l, sizeof l, i)) { if (!strncmp(l, key, kl) && l[kl] == '=') { if (!done) fprintf(o, "%s=%s\n", key, val); done = 1; } else fputs(l, o); } fclose(i); }
    if (!done) fprintf(o, "%s=%s\n", key, val);
    fflush(o); fclose(o); rename(t, p);
}
static int autostart_on(void) { char p[400]; struct stat s; upath(p, sizeof p, "autostart"); return stat(p, &s) == 0; }
static void autostart_set(int on) {
    if (test_mode()) return;
    char p[400], q[400]; upath(p, sizeof p, "autostart");
    if (on) { FILE *f = fopen(p, "w"); if (f) { fputs("on\n", f); fclose(f); } upath(q, sizeof q, "autostart_failed"); remove(q); upath(q, sizeof q, "autostart_fails"); remove(q); }
    else remove(p);
}
static int vol_get(void) {
    if (test_mode()) return 55;
    FILE *p = popen("amixer sget Master 2>/dev/null", "r"); int v = -1; if (!p) return 55;
    char l[200]; while (fgets(l, sizeof l, p)) { char *b = strchr(l, '['); if (b && strchr(b, '%')) { v = atoi(b + 1); break; } }
    pclose(p); return v < 0 ? 55 : v;
}
static void vol_set(int v) { if (test_mode()) return; char c[80]; snprintf(c, sizeof c, "amixer sset Master %d%% >/dev/null 2>&1", v); system(c); }

// ---------- date and time ----------
static void clk_load(void) { time_t t = time(NULL); struct tm *l = localtime(&t); clk[0] = l->tm_year + 1900; clk[1] = l->tm_mon + 1; clk[2] = l->tm_mday; clk[3] = l->tm_hour; clk[4] = l->tm_min; clk_f = 0; }
static int clk_dim(void) { static const int d[] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31}; int y = clk[0], m = clk[1]; return (m == 2 && ((y % 4 == 0 && y % 100) || y % 400 == 0)) ? 29 : d[m - 1]; }
static void clk_apply(void) {
    if (test_mode()) return;
    char c[160]; snprintf(c, sizeof c, "date -s \"%04d-%02d-%02d %02d:%02d:00\" >/dev/null 2>&1; hwclock -w >/dev/null 2>&1", clk[0], clk[1], clk[2], clk[3], clk[4]); system(c);
    clock_save();
}
static void clk_key(int k) {
    if (k == SDL_SCANCODE_B || k == SDL_SCANCODE_1) { pf_sub = 0; return; }
    if (k == SDL_SCANCODE_A) { clk_apply(); pf_sub = 0; return; }
    if (k == SDL_SCANCODE_LEFT) clk_f = (clk_f + 4) % 5; else if (k == SDL_SCANCODE_RIGHT) clk_f = (clk_f + 1) % 5;
    else if (k == SDL_SCANCODE_UP || k == SDL_SCANCODE_DOWN) {
        int d = k == SDL_SCANCODE_UP ? 1 : -1; static const int lo[] = {2020, 1, 1, 0, 0}, hi[] = {2099, 12, 31, 23, 59};
        int mx = clk_f == 2 ? clk_dim() : hi[clk_f]; clk[clk_f] += d; if (clk[clk_f] > mx) clk[clk_f] = lo[clk_f]; if (clk[clk_f] < lo[clk_f]) clk[clk_f] = mx;
        if (clk[2] > clk_dim()) clk[2] = clk_dim();
    }
}
static void draw_clock(void) {
    rect(0, 0, W, H, alpha(C_BLACK, 200)); rbox(300, 210, 680, 300, 22, (Col){24, 32, 62, 255}); rbox(300, 210, 680, 6, 3, C_ACC);
    text_c("날짜 · 시간 설정", 640, 232, 34, C_TXT, 620);
    char b[5][8]; snprintf(b[0], 8, "%04d", clk[0]); for (int i = 1; i < 5; i++) snprintf(b[i], 8, "%02d", clk[i]);
    const char *sep[] = {"", "-", "-", "   ", ":"}; int x = 640 - 190, sz = 52;
    for (int i = 0; i < 5; i++) {
        if (sep[i][0]) { x += 8; text(sep[i], x, 322, sz, C_DIM, 0); x += text_w(sep[i], sz) + 12; }
        int w = text_w(b[i], sz); if (i == clk_f) { rbox(x - 8, 312, w + 16, 76, 10, C_ROW); rect(x - 4, 384, w + 8, 4, C_YL); }
        text(b[i], x, 322, sz, i == clk_f ? C_YL : C_TXT, 0); x += w + 4;
    }
    text_c("← → 칸 이동    ↑ ↓ 바꾸기", 640, 420, 22, C_DIM, 620); text_c("A 저장    B 취소", 640, 458, 22, C_DIM, 620);
}

// ---------- restore a settings backup (made by menu 9850 into pandory_backups/minos_N) ----------
static void rs_scan(void) {
    rs_n = 0; rs_sel = 0; rs_arm = 0; char p[400]; snprintf(p, sizeof p, "%s/pandory_backups", card); DIR *d = opendir(p); if (!d) return;
    struct dirent *e; int num[40], nn = 0;
    while ((e = readdir(d)) != NULL && nn < 40) if (!strncmp(e->d_name, "minos_", 6) && atoi(e->d_name + 6) > 0) num[nn++] = atoi(e->d_name + 6);
    closedir(d);
    for (int i = 1; i < nn; i++) { int t = num[i], j = i; while (j > 0 && num[j - 1] < t) { num[j] = num[j - 1]; j--; } num[j] = t; }     // newest first
    for (int i = 0; i < nn && i < 5; i++) {
        rs_num[rs_n] = num[i]; snprintf(rs_name[rs_n], 32, "minos_%d", num[i]); rs_date[rs_n][0] = 0;
        char q[420]; snprintf(q, sizeof q, "%s/minos_%d", p, num[i]); struct stat st; if (stat(q, &st) == 0) { time_t t = st.st_mtime; struct tm *l = localtime(&t); strftime(rs_date[rs_n], 24, "%Y-%m-%d %H:%M", l); }
        rs_n++;
    }
}
static void rs_do(int n) {
    if (test_mode()) return;
    char c[1700];
    snprintf(c, sizeof c, "B='%s/pandory_backups'; D=\"$B/minos_%d\"; P='%s/pandory'; mkdir -p \"$B/before_restore/front\"; "
        "cp \"$P\"/front/*.txt \"$P\"/front/*.tsv \"$P\"/front/*.cfg \"$B/before_restore/front/\" 2>/dev/null; "
        "cp \"$D\"/front/*.txt \"$D\"/front/*.tsv \"$D\"/front/*.cfg \"$P/front/\" 2>/dev/null; "
        "cp \"$D\"/ra/ra.cfg* \"$P/ra/\" 2>/dev/null; [ -d \"$D/ra/layouts\" ] && cp -r \"$D/ra/layouts\" \"$P/ra/\"; "
        "cp \"$D\"/*.tsv \"$D\"/names_map.txt \"$P/\" 2>/dev/null; sync", card, n, card);
    system(c); LOG("restored backup minos_%d", n); sync(); system("reboot");
}
static void rs_key(int k) {
    if (k == SDL_SCANCODE_B || k == SDL_SCANCODE_1) { pf_sub = 0; return; }
    if (k == SDL_SCANCODE_UP && rs_n) { rs_sel = (rs_sel + rs_n - 1) % rs_n; rs_arm = 0; } else if (k == SDL_SCANCODE_DOWN && rs_n) { rs_sel = (rs_sel + 1) % rs_n; rs_arm = 0; }
    else if (k == SDL_SCANCODE_A && rs_n) { if (rs_arm != rs_sel + 1) rs_arm = rs_sel + 1; else rs_do(rs_num[rs_sel]); }
}
static void draw_restore(void) {
    rect(0, 0, W, H, alpha(C_BLACK, 200)); rbox(250, 150, 780, 420, 22, (Col){24, 32, 62, 255}); rbox(250, 150, 780, 6, 3, C_ACC);
    text_c("설정 복원", 640, 170, 34, C_TXT, 700);
    if (!rs_n) text_c("백업이 없습니다 (메뉴 9850 으로 먼저 백업)", 640, 330, 26, C_DIM, 720);
    for (int i = 0; i < rs_n; i++) {
        int y = 228 + i * 56, on = i == rs_sel; rbox(290, y, 700, 48, 10, on ? C_ROW : alpha(C_ROW, 80));
        text(rs_name[i], 320, y + 9, 26, on ? C_YL : C_TXT, 0); text(rs_date[i], 520, y + 12, 22, C_DIM, 0);
        if (on) { const char *a = rs_arm == i + 1 ? "한 번 더 A (복원하고 재시작)" : "A 복원"; int w = text_w(tr(a), 22); text(a, 960 - w, y + 12, 22, rs_arm == i + 1 ? C_PK : C_CY, 0); }
    }
    text_c("↑ ↓ 고르기    B 취소    복원 전 지금 설정은 pandory_backups/before_restore 에 남습니다", 640, 520, 18, C_DIM, 740);
}

#define NP 14
static void prefs_open(void) { pf_row = 0; pf_vol = vol_get(); pf_arm = 0; pf_sub = 0; }
// returns 0 = stay, 1 = close, 2 = RetroArch menu, 3 = button test
static int prefs_key(int k) {
    if (pf_sub == 1) { clk_key(k); return 0; }
    if (pf_sub == 2) { rs_key(k); return 0; }
    int d = k == SDL_SCANCODE_RIGHT ? 1 : k == SDL_SCANCODE_LEFT ? -1 : 0;
    if (k == SDL_SCANCODE_B || k == SDL_SCANCODE_1) return 1;
    if (k == SDL_SCANCODE_UP) { pf_row = (pf_row + NP - 1) % NP; pf_arm = 0; } else if (k == SDL_SCANCODE_DOWN) { pf_row = (pf_row + 1) % NP; pf_arm = 0; }
    else if (k == SDL_SCANCODE_A) d = 1;
    if (!d) return 0;
    if (pf_row == 0) { set_lang(!lang_en); lang_save(); }
    else if (pf_row == 1) { quit_hold += d; if (quit_hold > 8) quit_hold = 2; if (quit_hold < 2) quit_hold = 8; char b[16]; snprintf(b, sizeof b, "%d", quit_hold); cfg_set("quit_hold", b); }
    else if (pf_row == 2) { resume_def = !resume_def; cfg_set("resume", resume_def ? "1" : "0"); }
    else if (pf_row == 3) autostart_set(!autostart_on());
    else if (pf_row == 4) { pf_vol += d * 5; if (pf_vol > 100) pf_vol = 100; if (pf_vol < 0) pf_vol = 0; vol_set(pf_vol); }
    else if (pf_row == 5) { game_vol += d * 3; if (game_vol > 12) game_vol = -30; if (game_vol < -30) game_vol = 12; char b[16]; snprintf(b, sizeof b, "%d", game_vol); cfg_set("game_vol", b); }
    else if (pf_row == 6) { bezel_on = (bezel_on + 8 + d) % 8; char b[8]; snprintf(b, sizeof b, "%d", bezel_on); cfg_set("bezel", b); }
    else if (pf_row == 7) { static const int iv[] = {0, 60, 120, 300}; int c = 0; for (int q = 0; q < 4; q++) if (iv[q] == idle_sec) c = q; c = (c + 4 + d) % 4; idle_sec = iv[c]; char b[8]; snprintf(b, sizeof b, "%d", idle_sec); cfg_set("idle", b); }
    else if (pf_row == 8 && k == SDL_SCANCODE_A) { clk_load(); pf_sub = 1; }
    else if (pf_row == 9 && k == SDL_SCANCODE_A) { rs_scan(); pf_sub = 2; }
    else if (pf_row == 10 && k == SDL_SCANCODE_A) return 2;
    else if (pf_row == 11 && k == SDL_SCANCODE_A) return 3;
    else if ((pf_row == 12 || pf_row == 13) && k == SDL_SCANCODE_A) {          // reboot / power off: press A twice
        if (!pf_arm) pf_arm = pf_row; else if (!test_mode()) { sync(); system(pf_row == 12 ? "reboot" : "poweroff"); }
    }
    return 0;
}
static void draw_prefs(void) {
    draw_background(); draw_topbar("프론트 설정");
    char vb[24], qh[24], gv[24], ck[24]; snprintf(vb, sizeof vb, "%d %%", pf_vol); snprintf(gv, sizeof gv, game_vol == 0 ? "기본" : "%+d dB", game_vol); snprintf(qh, sizeof qh, "%d 초", quit_hold);
    { time_t t = time(NULL); struct tm *l = localtime(&t); strftime(ck, sizeof ck, "%Y-%m-%d %H:%M", l); }
    const char *lab[NP] = {"언어", "게임 종료 (Start 길게)", "게임 이어하기", "시작할 때 MinosFront", "소리 크기 (메뉴)", "게임 소리", "화면 테두리", "대기 화면", "날짜 · 시간", "설정 복원", "RetroArch 설정", "버튼 테스트", "재부팅", "전원 끄기"};
    const char *val[NP] = { lang_en ? "English" : "한국어", qh, resume_def ? "켜짐" : "꺼짐", autostart_on() ? "켜짐" : "꺼짐", vb, gv, bezel_name[bezel_on], idle_sec == 0 ? "끔" : idle_sec == 60 ? "1분" : idle_sec == 120 ? "2분" : "5분", ck, "열기", "열기", "열기",
                            pf_arm == 12 ? "한 번 더 A" : "실행", pf_arm == 13 ? "한 번 더 A" : "실행" };
    const char *hint[NP] = {"코인 키로 기종 선택 화면에서도 바뀝니다", "게임 도중 Start 를 이 시간 동안 누르면 종료", "게임을 다시 열면 마지막 상태에서 시작", "켜면 부팅 후 판도라 메뉴 대신 이 화면이 먼저 뜹니다",
                            "← → 로 조절 (프론트 메뉴 소리)", "게임 안에서는 Start + ← → 로도 조절", "원래 비율로 보는 게임에 화면 틀을 씌웁니다 (섞어서 = 게임마다 다르게)", "일정 시간 입력이 없으면 어두운 데모 화면 (번인 방지)",
                            "기기 시계를 직접 맞춥니다 (저장 시간 표시용)", "백업해 둔 설정으로 되돌립니다 (백업은 메뉴 9850)", "레트로아크 자체 메뉴 (화면 · 입력 · 오디오 상세 설정)", "버튼 신호가 살아 있는지 확인", "기기를 다시 시작합니다", "기기 전원을 끕니다"};
    for (int i = 0; i < NP; i++) {
        int y = 84 + i * 40, on = i == pf_row; rbox(120, y, 1040, 37, 10, on ? alpha(C_ROW, 255) : C_PANEL);
        if (on) rect(124, y + 4, 5, 30, C_YL);
        text(lab[i], 150, y - 2, 19, on ? C_YL : C_TXT, 0); text(hint[i], 150, y + 20, 12, C_DIM, 0);
        char v[48]; snprintf(v, sizeof v, i >= 8 ? "%s" : "◀  %s  ▶", tr(val[i])); int w = text_w(v, 19); text(v, 1138 - w, y + 7, 19, on ? C_CY : C_DIM, 0);
        if (i == 4) { rbox(790, y + 31, 340, 4, 2, alpha(C_LINE, 160)); rbox(790, y + 31, (int)(340 * pf_vol / 100.0f), 4, 2, C_PK); }
    }
    draw_footer("바꾸기", "뒤로", NULL); draw_noise(); draw_crt();
    if (pf_sub == 1) draw_clock(); else if (pf_sub == 2) draw_restore();
}
