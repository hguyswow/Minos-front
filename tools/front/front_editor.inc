// front_editor.inc - the button layout editor screen (see front_keys.inc). Included at the end of front_ui.inc.
typedef struct { char file[160], title[200], gkey[320], folder[40]; Logi L; int m[6]; int cur, sub, subcur, scope, preset; } Ed;
static Ed ed;
static void km_status(const char *file, const char *folder) {
    BtnInfo *b = bi_find(file); char gk[320]; group_key(b, folder, gk, sizeof gk); char w = 0; km_resolve(file, gk, &w);
    snprintf(g_keystat, sizeof g_keystat, "%s", w == 'G' ? "내 배치 (이 게임)" : w == 'R' ? "내 배치 (같은 종류)" : "순정");
}
static void ed_stock(int m[6]) { spec_to_masks(STOCK_SPEC, &ed.L, m); }
static void ed_open(const char *file, const char *title, const char *folder) {
    memset(&ed, 0, sizeof ed); snprintf(ed.file, sizeof ed.file, "%s", file); snprintf(ed.title, sizeof ed.title, "%s", title); snprintf(ed.folder, sizeof ed.folder, "%s", folder);
    BtnInfo *b = bi_find(file); logi_parse(b ? b->desc : "", &ed.L); group_key(b, folder, ed.gkey, sizeof ed.gkey);
    char w = 0; const char *sp = km_resolve(file, ed.gkey, &w); if (sp) { spec_to_masks(sp, &ed.L, ed.m); ed.scope = w == 'R'; } else ed_stock(ed.m);
}
static const char *ED_PRESETS[] = {"순정 (기기 기본 배치)", "순서대로 (윗줄 1·2·3 / 아랫줄 4·5·6)", "네오지오식 (1·2·1+2 / 3·4·3+4)", "2버튼 위아래 (윗줄=2번, 아랫줄=1번)"};
static void ed_preset(int pi) {
    int n = ed.L.n; int *m = ed.m; for (int i = 0; i < 6; i++) m[i] = 0;
    if (pi == 0) ed_stock(m);
    else if (pi == 1) { for (int i = 0; i < 6 && i < n; i++) m[i] = 1 << i; }
    else if (pi == 2) { if (n >= 4) { m[0] = 1; m[1] = 2; m[2] = 3; m[3] = 4; m[4] = 8; m[5] = 12; } else { for (int i = 0; i < 6 && i < n; i++) m[i] = 1 << i; } }
    else { int a = n > 1 ? 2 : 1, b = 1; m[0] = m[1] = m[2] = a; m[3] = m[4] = m[5] = b; }
}
static int ed_save(void) {
    char spec[120]; masks_to_spec(ed.m, &ed.L, spec, sizeof spec); int st[6]; ed_stock(st); int same = 1; for (int i = 0; i < 6; i++) if (st[i] != ed.m[i]) same = 0;
    if (ed.scope == 0) km_set('G', ed.file, same ? NULL : spec);
    else { km_set('R', ed.gkey, same ? NULL : spec); km_set('G', ed.file, NULL); }
    km_status(ed.file, ed.folder); return 1;
}
static int ed_key(int k) {                // returns 1 = close the editor
    if (ed.sub) {
        if (k == SDL_SCANCODE_UP) ed.subcur = (ed.subcur + ed.L.n - 1) % ed.L.n; else if (k == SDL_SCANCODE_DOWN) ed.subcur = (ed.subcur + 1) % ed.L.n;
        else if (k == SDL_SCANCODE_A) ed.m[ed.cur] ^= 1 << ed.subcur; else if (k == SDL_SCANCODE_B) ed.sub = 0;
        return 0; }
    if (k == SDL_SCANCODE_LEFT) ed.cur = ed.cur / 3 * 3 + (ed.cur % 3 + 2) % 3; else if (k == SDL_SCANCODE_RIGHT) ed.cur = ed.cur / 3 * 3 + (ed.cur % 3 + 1) % 3;
    else if (k == SDL_SCANCODE_UP || k == SDL_SCANCODE_DOWN) ed.cur = (ed.cur + 3) % 6;
    else if (k == SDL_SCANCODE_A) { ed.sub = 1; ed.subcur = 0; }
    else if (k == SDL_SCANCODE_D) { ed.preset = (ed.preset + 1) % 4; ed_preset(ed.preset); }
    else if (k == SDL_SCANCODE_I) ed.scope ^= 1;
    else if (k == SDL_SCANCODE_1) return ed_save();
    else if (k == SDL_SCANCODE_B) return 1;
    return 0;
}
static void ed_cell_text(int p, char *out, size_t n) {
    out[0] = 0; size_t l = 0; for (int j = 0; j < ed.L.n; j++) if (ed.m[p] & (1 << j)) l += (size_t)snprintf(out + l, n - l, "%s%s", l ? "+" : "", kname(ed.L.name[j]));
    if (!out[0]) snprintf(out, n, "(없음)");
}
static void draw_editor(void) {
    draw_background(); draw_topbar("버튼 배치");
    text_fit(ed.title, 40, 84, 28, C_YL, 1200);
    for (int p = 0; p < 6; p++) {
        int col = p % 3, row = p / 3; int x = 40 + col * 240, y = 140 + row * 150, w = 224, h = 134; int on = p == ed.cur;
        outline(x, y, w, h, 16, on ? 4 : 2, on ? C_YL : alpha(C_LINE, 200), C_PANEL);
        disc(x + 40, y + 40, 26, on ? C_YL : (Col){120, 70, 190, 255}); char l[4] = {(char)(PK[p][0] - 32), 0}; text_c(l, x + 40, y + 20, 32, (Col){30, 12, 50, 255}, 40);
        text(row ? "아랫줄" : "윗줄", x + 82, y + 14, 18, C_DIM, 0);
        char t[160]; ed_cell_text(p, t, sizeof t); text_wrap(t, x + 14, y + 76, 24, on ? C_TXT : C_DIM, w - 28, 2, 28);
    }
    outline(40, 452, 704, 196, 14, 3, alpha(C_CY, 170), C_PANEL);
    char sc[120]; snprintf(sc, sizeof sc, "저장 범위:  %s", ed.scope ? "같은 종류 게임 전체" : "이 게임만"); neon(sc, 60, 462, 26, C_CY, 0);
    text(ed.scope ? "(같은 코어, 같은 버튼 이름을 쓰는 모든 게임. 예: 네오지오 전체)" : "(코인 버튼으로 바꿈)", 60, 502, 18, C_DIM, 0);
    text("예시 배치 (D 로 넘기기):", 60, 540, 20, C_DIM, 0); text_fit(ED_PRESETS[ed.preset], 60, 568, 24, C_YL, 660);
    text("Start 로 저장하면 다음 실행부터 적용됩니다.", 60, 612, 18, C_DIM, 0);
    outline(764, 140, 476, 508, 16, 3, alpha(C_PK, 190), C_PANEL);
    text(ed.sub ? "누를 게임 버튼 고르기 (A 선택/해제, B 완료)" : "이 게임의 버튼", 784, 152, 20, ed.sub ? C_YL : C_DIM, 0);
    for (int j = 0; j < ed.L.n; j++) {
        int y = 192 + j * 44; int hl = ed.sub && j == ed.subcur; if (hl) rbox(776, y - 2, 452, 40, 8, C_ROW);
        char t[96]; snprintf(t, sizeof t, "%d  %s", j + 1, kname(ed.L.name[j])); text(t, 796, y + 4, 24, hl ? C_TXT : C_DIM, 0);
        if (ed.sub) text((ed.m[ed.cur] & (1 << j)) ? "[ ■ ]" : "[    ]", 1130, y + 4, 24, (ed.m[ed.cur] & (1 << j)) ? C_YL : C_DIM, 0);
        else { char ph[24] = ""; size_t l = 0; for (int p = 0; p < 6; p++) if (ed.m[p] & (1 << j)) { char one[2] = {(char)(PK[p][0] - 32), 0}; l += (size_t)snprintf(ph + l, sizeof ph - l, "%s", one); } text(ph, 1130, y + 4, 22, C_CY, 0); }
    }
    rect(0, 664, W, 56, alpha(C_BLACK, 140)); rect(0, 664, W, 2, alpha(C_CY, 140));
    int x = 30; if (ed.sub) { pill(&x, 676, "A", "선택/해제"); pill(&x, 676, "B", "완료"); } else { pill(&x, 676, "A", "칸 편집"); pill(&x, 676, "D", "예시"); pill(&x, 676, "코인", "저장 범위"); pill(&x, 676, "Start", "저장"); pill(&x, 676, "B", "취소"); }
    draw_crt();
}
