// front_prefs.inc - the "MinosFront settings" screen (language, quit-hold time, automatic resume, start-up front, volume).
// Everything is stored in the card's pandory/front files (front.cfg, lang.txt, autostart); the volume is the system mixer.

static int pf_row, pf_vol = 55, pf_arm;

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

#define NP 12
static void prefs_open(void) { pf_row = 0; pf_vol = vol_get(); pf_arm = 0; }
// returns 0 = stay, 1 = close, 2 = RetroArch menu, 3 = button test
static int prefs_key(int k) {
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
    else if (pf_row == 6) { bezel_on = (bezel_on + 3 + d) % 3; char b[8]; snprintf(b, sizeof b, "%d", bezel_on); cfg_set("bezel", b); }
    else if (pf_row == 7) { static const int iv[] = {0, 60, 120, 300}; int c = 0; for (int q = 0; q < 4; q++) if (iv[q] == idle_sec) c = q; c = (c + 4 + d) % 4; idle_sec = iv[c]; char b[8]; snprintf(b, sizeof b, "%d", idle_sec); cfg_set("idle", b); }
    else if (pf_row == 8 && k == SDL_SCANCODE_A) return 2;
    else if (pf_row == 9 && k == SDL_SCANCODE_A) return 3;
    else if ((pf_row == 10 || pf_row == 11) && k == SDL_SCANCODE_A) {          // reboot / power off: press A twice
        if (!pf_arm) pf_arm = pf_row; else if (!test_mode()) { sync(); system(pf_row == 10 ? "reboot" : "poweroff"); }
    }
    return 0;
}
static void draw_prefs(void) {
    draw_background(); draw_topbar("프론트 설정");
    char vb[24], qh[24], gv[24]; snprintf(vb, sizeof vb, "%d %%", pf_vol); snprintf(gv, sizeof gv, game_vol == 0 ? "기본" : "%+d dB", game_vol); snprintf(qh, sizeof qh, "%d 초", quit_hold);
    const char *lab[NP] = {"언어", "게임 종료 (Start 길게)", "게임 이어하기", "시작할 때 MinosFront", "소리 크기 (메뉴)", "게임 소리", "화면 테두리", "대기 화면", "RetroArch 설정", "버튼 테스트", "재부팅", "전원 끄기"};
    const char *val[NP] = { lang_en ? "English" : "한국어", qh, resume_def ? "켜짐" : "꺼짐", autostart_on() ? "켜짐" : "꺼짐", vb, gv, bezel_on == 0 ? "꺼짐" : bezel_on == 1 ? "네온" : "단순", idle_sec == 0 ? "끔" : idle_sec == 60 ? "1분" : idle_sec == 120 ? "2분" : "5분", "열기", "열기",
                            pf_arm == 10 ? "한 번 더 A" : "실행", pf_arm == 11 ? "한 번 더 A" : "실행" };
    const char *hint[NP] = {"코인 키로 기종 선택 화면에서도 바뀝니다", "게임 도중 Start 를 이 시간 동안 누르면 종료", "게임을 다시 열면 마지막 상태에서 시작", "켜면 부팅 후 판도라 메뉴 대신 이 화면이 먼저 뜹니다",
                            "← → 로 조절 (프론트 메뉴 소리)", "게임 안에서는 Start + ← → 로도 조절", "원래 비율로 보는 게임에 오락실 화면 틀을 씌웁니다", "일정 시간 입력이 없으면 어두운 데모 화면 (번인 방지)", "레트로아크 자체 메뉴 (화면 · 입력 · 오디오 상세 설정)", "버튼 신호가 살아 있는지 확인", "기기를 다시 시작합니다", "기기 전원을 끕니다"};
    for (int i = 0; i < NP; i++) {
        int y = 84 + i * 46, on = i == pf_row; rbox(120, y, 1040, 42, 10, on ? alpha(C_ROW, 255) : C_PANEL);
        if (on) rect(124, y + 5, 5, 32, C_YL);
        text(lab[i], 150, y - 1, 20, on ? C_YL : C_TXT, 0); text(hint[i], 150, y + 23, 13, C_DIM, 0);
        char v[48]; snprintf(v, sizeof v, i >= 8 ? "%s" : "◀  %s  ▶", tr(val[i])); int w = text_w(v, 20); text(v, 1138 - w, y + 8, 20, on ? C_CY : C_DIM, 0);
        if (i == 4) { rbox(790, y + 34, 340, 4, 2, alpha(C_LINE, 160)); rbox(790, y + 34, (int)(340 * pf_vol / 100.0f), 4, 2, C_PK); }
    }
    draw_footer("바꾸기", "뒤로", NULL); draw_noise(); draw_crt();
}
