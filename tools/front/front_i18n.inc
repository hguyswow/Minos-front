// front_i18n.inc - English texts for MinosFront (Korean is the default). Every text that is drawn goes through tr().
// EXACT: whole string must match (short words that could appear inside other words).  PHRASE: replaced wherever they occur, longest first.
// Language is stored in pandory/front/lang.txt ("en" or "ko"); the Coin button on the system screen switches it.
typedef struct { const char *ko, *en; } Tr;
static int lang_en;
static const Tr EXACT[] = {
    {"예", "Yes"}, {"끔", "Off"}, {"켬", "On"}, {"발", "Kick"}, {"샷", "Shot"}, {"순정", "Stock"}, {"원래", "Orig."}, {"가득", "Fill"}, {"선명", "Sharp"}, {"버튼", "Keys"},
    {"비율", "Ratio"}, {"화질", "Quality"}, {"열기", "Open"}, {"실행", "Play"}, {"뒤로", "Back"}, {"저장", "Save"}, {"취소", "Cancel"}, {"닫기", "Close"}, {"완료", "Done"},
    {"예시", "Presets"}, {"아니오", "No"}, {"종료", "Quit"}, {"포트", "Ports"}, {"스타트", "Start"}, {"공격", "Attack"}, {"점프", "Jump"}, {"발사", "Fire"}, {"폭탄", "Bomb"}, {"주먹", "Punch"}, {"특수", "Special"},
};
static const Tr PHRASE[] = {
    {"메가드라이브 (순정 목록)", "Mega Drive (original list)"}, {"메가드라이브", "Mega Drive"}, {"세가 32X", "Sega 32X"}, {"PC엔진", "PC Engine"}, {"게임보이 어드밴스", "Game Boy Advance"},
    {"게임보이 컬러", "Game Boy Color"}, {"게임보이", "Game Boy"}, {"아타리 2600", "Atari 2600"}, {"아미가", "Amiga"}, {"아타리 ST", "Atari ST"}, {"아케이드", "Arcade"}, {"포트", "Ports"},
    {"슈퍼패미컴", "Super Famicom"}, {"패미컴", "Famicom"}, {"플레이스테이션", "PlayStation"}, {"최근 한 게임", "Recent"}, {"즐겨찾기", "Favorites"}, {"RetroArch 설정", "RetroArch Settings"},
    {"버튼 테스트", "Button Test"}, {"원래 메뉴", "Original Menu"}, {"게임이 없습니다 (roms_pandory 폴더를 확인하세요)", "No games found (check the roms_pandory folder)"},
    {"오락실", "ARCADE"}, {"1회 100원", "1 play = 100 won"}, {"문의:", "Contact:"}, {"판도라 기본 화면", "Pandora home screen"}, {"상세 설정", "Detailed settings"},
    {"버튼 신호 확인", "Check button signals"}, {"개 게임", " games"}, {"기종 선택", "Choose system"}, {"동전을 넣어 주세요", "INSERT COIN"}, {"미리보기 없음", "No preview"},
    {"가득 채움", "Fill screen"}, {"원래 비율", "Original ratio"}, {"부드럽게", "Smooth"}, {"선명하게", "Sharp"}, {"내 배치", "Custom"}, {"기본", "Default"}, {"(켬)", "(On)"},
    {"다음 글자", "Next letter"}, {"코인 게임별 설정", "Coin: game settings"}, {"개씩", " at a time"}, {"게임 중 단축키", "In-game hotkeys"}, {"이 게임 설정", "Game settings"},
    {"화면 비율", "Screen ratio"}, {"이어하기: 끝낼 때 자동 저장, 다시 실행하면 그 자리에서 시작", "Resume: saves when you quit, continues from there next time"}, {"이어하기", "Resume"},
    {"버튼 배치", "Button layout"}, {"(A 눌러 편집)", "(press A to edit)"}, {"항목", "item"}, {"바꾸기", "change"}, {"저장하고 닫기", "save and close"}, {"편집", "edit"},
    {"종료할까요?", "Quit?"}, {"게임 끝내기 (MinosFront로 돌아옴)", "Quit game (back to MinosFront)"}, {"지금 상태 저장", "Save state"}, {"저장한 상태 불러오기", "Load state"},
    {"일시정지", "Pause"}, {"게임 리셋", "Reset game"}, {"빨리감기 켜기 / 끄기", "Fast-forward on / off"}, {"저장 칸 번호 바꾸기", "Change save slot"},
    {"슬로모션 (누르고 있는 동안)", "Slow motion (while held)"}, {"화면 캡처", "Screenshot"}, {"RetroArch 메뉴 (코인 2초 누르기도 가능)", "RetroArch menu (or hold Coin 2 s)"},
    {"그 버튼 연사 켜기 / 끄기 (한 번 더 하면 끔)", "Turbo on / off for that button (again = off)"},
    {"를 누른 채로 다른 버튼을 누릅니다", " held, then press another button"}, {"만 4초 누르면 강제 종료", " alone for 4 s = force quit"},
    {"키  ", "Key  "}, {"(번호", "(code"}, {"조이스틱", "Joystick"}, {"방향패드", "D-pad"}, {"버튼을 아무거나 눌러 보세요. 신호가 오면 아래에 나타납니다.", "Press any button. Signals appear below."},
    {"개 인식", " found"}, {" 번 눌림", " presses"}, {"아직 눌린 버튼이 없습니다", "No button pressed yet"}, {"최근 신호", "Recent signals"},
    {"를 계속 누르는 중... 나가기", " held... leaving"}, {"나가기: Start 를 1.5초 누르고 있기", "Leave: hold Start for 1.5 s"},
    {"약손", "LP"}, {"중손", "MP"}, {"강손", "HP"}, {"약발", "LK"}, {"중발", "MK"}, {"강발", "HK"},
    {"내 배치 (이 게임)", "Custom (this game)"}, {"내 배치 (같은 종류)", "Custom (same kind)"}, {"순정 (기기 기본 배치)", "Stock (device default)"},
    {"순서대로 (윗줄 1·2·3 / 아랫줄 4·5·6)", "In order (top 1·2·3 / bottom 4·5·6)"}, {"네오지오식 (1·2·1+2 / 3·4·3+4)", "Neo Geo style (1·2·1+2 / 3·4·3+4)"},
    {"2버튼 위아래 (윗줄=2번, 아랫줄=1번)", "2 buttons up/down (top=2, bottom=1)"}, {"(없음)", "(none)"}, {"아랫줄", "Bottom"}, {"윗줄", "Top"}, {"저장 범위:", "Save for:"},
    {"같은 종류 게임 전체", "all games of this kind"}, {"이 게임만", "this game only"}, {"(같은 코어, 같은 버튼 이름을 쓰는 모든 게임. 예: 네오지오 전체)", "(every game with the same core and button names, e.g. all Neo Geo)"},
    {"(코인 버튼으로 바꿈)", "(Coin button switches)"}, {"예시 배치 (D 로 넘기기):", "Preset layouts (D = next):"}, {"로 저장하면 다음 실행부터 적용됩니다.", " saves; applies from the next start."},
    {"누를 게임 버튼 고르기", "Choose the game buttons to press"}, {"선택/해제", "toggle"}, {"이 게임의 버튼", "Buttons of this game"}, {"칸 편집", "Edit slot"}, {"저장 범위", "Save for"},
    {"버튼", "Button "}, {"코인", "Coin"}, {"뒤로", "Back"},
};
static int tr_sorted;
static int tr_cmp(const void *a, const void *b) { return (int)strlen(((const Tr *)b)->ko) - (int)strlen(((const Tr *)a)->ko); }
static Tr tr_ph[sizeof PHRASE / sizeof PHRASE[0]];
static char trbuf[8][700]; static int trn;
static const char *tr(const char *s) {
    if (!lang_en || !s) return s;
    const unsigned char *q = (const unsigned char *)s; int han = 0; for (; *q; q++) if (*q >= 0x80) { han = 1; break; }
    if (!han) return s;
    for (unsigned i = 0; i < sizeof EXACT / sizeof EXACT[0]; i++) if (!strcmp(s, EXACT[i].ko)) return EXACT[i].en;
    if (!tr_sorted) { memcpy(tr_ph, PHRASE, sizeof PHRASE); qsort(tr_ph, sizeof PHRASE / sizeof PHRASE[0], sizeof(Tr), tr_cmp); tr_sorted = 1; }
    char *o = trbuf[trn++ & 7], tmp[700]; snprintf(o, 700, "%s", s);
    for (unsigned i = 0; i < sizeof PHRASE / sizeof PHRASE[0]; i++) {
        char *p; while ((p = strstr(o, tr_ph[i].ko)) != NULL) {
            size_t kl = strlen(tr_ph[i].ko); size_t pre = (size_t)(p - o); snprintf(tmp, sizeof tmp, "%.*s%s%s", (int)pre, o, tr_ph[i].en, p + kl); snprintf(o, 700, "%s", tmp); }
    }
    return o;
}
