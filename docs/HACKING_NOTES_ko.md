# Hacking notes — Pandora Saga DX2 Plus (menu hook, name patch, collections)
목표: **"Minos 판도라사가 에디터"**(Windows PC 프로그램)를 만든다. 기능: 게임 추가, 메뉴 이름(한글) 관리,
기종별 모음(필터), 화면 비율/화질 설정, 게임별 설정, 배경/영상 교체, 백업/복구.
이 문서는 지금까지의 조사 결과 전체와 안전 수칙, 남은 일을 담았다. 먼저 §0, §9를 읽을 것.

---
## 0. 작업 수칙 (필독)
- **기기 내부 플래시는 한 번도 쓰지 않았다(읽기만).** 절대 쓰지 말 것(펌웨어 업데이트/`update` 도구/플래시 쓰기 금지).
  `/userdata/gamemenu.cfg`(내부 ext2)만 모음 기능에서 쓴다(§6). 그 외 내부 변경 금지.
- 모든 변경은 **카드의 파일**이다. 복구 = 카드 파일을 원래대로 되돌리기(§8).
- PC 쪽 Python 주의: **명령줄/heredoc에 `\0`을 쓰면 하네스가 실제 NUL로 바꿔서 파일이 깨진다**(이번 세션에서 겪음). 파일에 쓸 때는
  `chr(92)` 등으로 백슬래시를 조립할 것. 도구 파일 저장 후 `s.count(b'\x00')==0` 확인.

## 1. 하드웨어/펌웨어 사실
- SoC **Rockchip RK3128**, ARMv7, Linux 4.4.159, glibc 2.26, busybox 1.27.2. 내부 플래시 `rkflash0` 223MB:
  p1 1MB, p2 2MB, p3 4.2MB, **p4 92MB = 루트(squashfs, 읽기전용)**, p5 1MB, p6 6MB = userdata(ext2, 쓰기 가능, `/userdata`).
  `/oem`(squashfs 128KB). 카드는 `/dev/mmcblk0p1` → `/mnt/sdcard`(vfat, uid 1000). 메뉴는 이를 `/udisk`, `/sdcard`로도 부름.
- 이 기기는 **구형 Pandora Box DX 계열 신형판(9800 games model)**. Pandory(TeamPandory의 해킹, DX용 `PandoryDX`)가 카드에 설치되어 있다.
  Pandory 도구는 PC에서 `pandory stick dx E:`로 설치했고 카드 파일만 바꾼다(`pandory_backups/`에 원본 보관).
- 부팅 체인: init → `/etc/init.d/S50ui` → `start_menu.sh` → `/usr/bin/emulotar`(코인 데몬, /tmp/loader2 우선) → `/usr/bin/loader2`
  (/tmp/gamemenu 우선) → 메뉴 `/usr/bin/gamemenu`. 순정 메뉴는 `/tmp/fba`, `/tmp/retroarch`, `/tmp/xmame.SDL`이 있으면 그걸 우선 실행한다.
  Pandory가 어디서 처음 실행되는지는 **미확인**(루트FS 스크립트/udev에는 훅 없음). 우리는 Pandory 바이너리의 문자열을 바꿔 훅으로 쓴다(§4).
- 에뮬레이터: 닫힌 RetroArch 1.7.4(`/usr/bin/retroarch`) + 코어(`/usr/lib/libretro/`: fbalpha2012, mame2003/2010, genesisplusgx, snes9x, pcsx_rearmed…).
  Pandory 카드에는 `E:\pandory\cores\`에 picodrive, genesis_plus_gx, snes9x, mednafen_pce_fast, mgba, gambatte, stella2014, puae 등.
- 순정 게임 롬은 `E:\roms\*.zip`(번호 `0000.zip`=NES, `md_*.zip`=FBA 메가드라이브 …) 및 제작사 비공개 로더(`hhh`)가 읽는다.
  **순정 칸의 zip을 바꿔도 실행 내용은 안 바뀐다**(시험: 모탈컴뱃이 나옴) → 순정 칸 바꿔치기 불가. 추가 게임은 Pandory `roms_pandory/`로.
- `/usr/bin/update` = Rockchip 업데이트 도구(`/sdcard/update.img` 지원). **쓰지 않음**(브릭 위험).

## 2. 카드(E:) 구성과 백업
```
E:\roms\ (순정 롬 5000+개, zip)         E:\roms_pandory\<기종폴더>\  ← 추가 게임(Pandory)
E:\movies\<romname>.avi  (미리보기)      E:\roms_pandory\scripts\  ← 메뉴에서 실행하는 .sh
E:\music\bg.mp3 · E:\user_bg.bmp(배경)   E:\roms_pandory\scripts_off\ (메뉴에 안 뜨는 보관 스크립트)
E:\pandory\ pandory(실행파일, 패치됨) pandory.xml cores\ auto.sh patch.txt names_map.txt collections\*.cfg …
E:\pandory_backups\  Pandory가 만든 원본(demo*.avi, user_bg.bmp, had/hadc/rade.zip)
E:\roms_md, roms_sfc, roms_fc, roms_playstation, roms_fba2012, roms_mame2003  ← 순정 USB 추가 방식(비어 있음, 사실상 미사용)
```
기종 폴더(`roms_pandory`): 32x, amiga, amiga1200, atari2600, atarist, bios, gb, gba, gbc, gblink, **genesis**(=메가드라이브), pce, ports, scripts.
허용 확장자는 `SUPPORTED_ROMS.txt`(Pandory): megadrive MD/SMD/GEN/BIN, snes SMC/SFC…, 코어는 `pandory.xml`의 `<emulator folder=… core=…>`.
- **백업 위치(PC)**: `D:\Backup\PandoraSaga_E.img`(카드 FAT32 파티션 28.9GB raw, 관리자 권한으로 생성; 카드 58GB는 **가짜 용량**이라 뒤쪽 29GB는 쓰레기),
  `D:\Backup\firmware_dump\rkflash0p1..p6.img`(내부 플래시 6개 파티션, 읽기 전용 덤프, 총 106MB), `D:\Backup\firmware_extract\`(p4 squashfs 풀어낸 루트FS),
  `D:\Backup\orig_md_swaptest\`, `D:\Backup\pandory_orig\pandory.orig`(패치 전 Pandory 원본), `D:\Backup\working_state_2026-11-01\`(성공 시점 파일),
  `D:\Backup\pandorytool_v114\`(PandoryTool 1.14 freeware, Windows), `D:\Backup\tools\`(분석/생성 도구 원본).
- **플래시 전체의 약 117MB는 아직 못 읽음**(리눅스에 안 보이는 영역). 내부를 바꿀 일이 생기면 그 전에 전체 백업을 다시 할 것.

## 3. 핵심 발견 — 메뉴(gamemenu)가 추가 게임 이름을 못 그리는 이유와 우회
- `/usr/bin/gamemenu`(ARM, 비PIE, Qt, 심볼 없음)는 `/tmp/addgame_list`(Pandory가 생성, 4바이트 개수+150바이트 항목, 이름은 항목+22)를 읽지만,
  줄 그리기 함수(0x31240)가 추가 게임(모드 5)을 **영어 ASCII 이름 칸(0x8e33d6+0x96*k, 메모리상 항상 0)** 경로로 보내서 번호만 그려진다.
  게다가 ASCII 외 글자는 `swprintf("%s")`가 C 로케일(로케일 파일 없음)이라 사라진다.
- 순정 게임 이름은 `/lib/name.bin`(9800 레코드 × 0x580 바이트, UTF-32LE; 슬롯 64B×22: 0 간체, 2 병음키, 3 번체, 5-8 주음, 13 영어(ASCII),
  **14-17 한국어(UTF-32LE, 64자)**, 18-21 한글자모)와 `/lib/gl.bin`(224B 헤더+9800×112B; +4 rom명, +0x64 종류)에서 온다. `hook.so`가 시작할 때
  이 두 파일을 gamemenu의 고정 주소(gl 0x80e4c, name 0xBB9A3C)로 통째로 읽어 들인다. 언어 바이트(S+0x451)=3이 한국어.
- **우회(작동 확인됨)**: 메뉴가 켜진 뒤 실행 중인 gamemenu 프로세스의 메모리를 `/proc/PID/mem`에 쓴다(루트, dd bs=1 seek=주소, 코드 영역 쓰기도 됨):
  1. 이름 테이블 레코드 `NAME_BASE + 0x580*idx`의 슬롯 0/3/13/14에 UTF-32LE 한글·ASCII 영어 이름을 쓴다. idx는 **줄→게임 번호 배열**에서 읽는다:
     배열 `0x8cf6d8 + 4*position`; 순정 위치 0..STOCK-1은 gl 인덱스, **추가 게임 k번째 = position STOCK+k, 값 = STOCK+2k**(2씩 건너뜀).
     `STOCK`=`*(u32*)0x8e33bc`(보이는 순정 게임 수, 기본 9882; **숨김 설정을 바꾸면 변한다** → 반드시 실행 시 읽을 것).
  2. 코드 패치: 줄 그리기 함수(0x31240)에서 "모드==5면 별도 경로" 분기 `beq`(주소 0x31330)를 NOP(`00 00 a0 e1`)으로 → 추가 줄도 순정 이름 경로(한국어 슬롯)로 그려진다.
     보조로 0x2f618/0x2f728/0x2fa68의 `movge r3,#1`→`#0`(첫 바이트 0x01→0x00)도 쓴다(필수 아님, 무해).
- 메모리 지도: 이름 버퍼 0xBB9A3C..(순정 13.8MB) 뒤 약 800KB 여유 → **추가 게임 약 240개**까지 안전(MAX_GAMES=240). 항목 배열은 4990개까지.
- 데이터/주소 요약(모두 gamemenu 가상주소): 총 게임 수 0x8e33b8(S2+0x5e0), 순정 수 0x8e33bc(S2+0x5e4, S2=0x8e2dd8), 줄 배열 0x8cf6d8,
  언어 0x8cf279, 현재 페이지 변수 0x800e48, addgame 원본 버퍼 0x9e33c0(4바이트 개수 0x99cea0), 이름 포인터 변수 0x99ceb8(=0xBB9A3C).

## 4. 자동 적용 훅 (Pandory 바이너리 패치) — `E:\pandory\auto.sh`
- 문제: 부팅/메뉴 재시작마다 위 메모리 패치를 다시 써야 한다(재시작하면 새 프로세스).
- 해결: `E:\pandory\pandory`(Pandory 실행파일, 1,263,028B)에서 **메뉴 시작 때마다 system()으로 실행되는 쓸모없는 명령 문자열**
  `find /tmp -name "*.zip.dat" -exec bash -c ...`(오프셋 0xe9c24, 81바이트)를 `sh /mnt/sdcard/pandory/auto.sh >/dev/null 2>&1 &` + NUL 패딩으로 바꿨다.
  원본은 `D:\Backup\pandory_orig\pandory.orig`. 바이트 차이 78개. **Pandory 업데이트/재설치하면 훅이 사라진다 → 다시 패치.**
- `auto.sh`: lock(`/tmp/auto.lock`) → 새 gamemenu PID를 기다림(이전 PID와 다른 것) → 8초 → `STOCK` 읽기 → `patch.txt`를 줄 단위로 적용.
  `patch.txt` 형식: 정적 줄 `주소(10진) 8진escape` / 동적 줄 `D k 슬롯오프셋 8진escape`(주소 = 0xBB9A3C + 1408*array[STOCK+k] + 슬롯오프셋).
  로그는 `E:\auto_patch.log`.
- 기기 쉘 함정(busybox/Pandory 환경): `cp`는 Pandory 래퍼라 인자 두 개가 한 덩어리로 깨짐 → **`cat a > b`** 사용. `printf '\xHH'` 미지원 → **8진 `\ooo`**.
  `od -A` 미지원(`od -b` 사용). `read`는 **`-r`**. `ps|grep gamemenu`는 busybox 껍데기가 잡힘 → `/proc/*/exe` 링크가 `*/gamemenu`인 것으로 찾는다.
  메뉴에서 실행한 스크립트가 도는 동안 gamemenu 프로세스는 없다(끝나면 Pandory가 새로 띄움). `/tmp`는 tmpfs.
- 메뉴에서 스크립트 항목을 실행하면 게임처럼 `Pandory`가 `shell` 코어로 실행한다. 다른 사용자 보고(RA2Pandora): "스크립트 실행 후 재부팅 전엔 다음 게임 대신 그 스크립트가 다시 실행되는 경우가 있다" — **우리 환경에서는 미검증**.

## 5. 이름 생성 도구 — `tools/pandora_names.py`, `update_names.bat`
- 입력: `E:\roms_pandory\<폴더>\파일`(Pandory가 메뉴에 올리는 순서 = **폴더 알파벳순, 파일은 바이트순(대문자가 소문자보다 앞)**; 순서 검증됨),
  `E:\pandory\names_map.txt`(`파일명 | 메뉴 제목`, 없으면 파일명으로 자동 추가), `pandory.xml`의 `<emulator folder=...>` 목록.
- 출력: `E:\pandory\patch.txt`, `names_map.txt` 갱신, `game_list_added.md/csv`(번호 9801+k). 제목 앞에 기종 태그(`[MD]`,`[GBA]`…, `--no-tags`로 끔).
- 메뉴 번호: 첫 추가 게임 = **9801**, k번째 = 9801+k. 순서가 어긋나면 이름이 엉뚱한 게임에 붙는다(→ 에디터는 반드시 이 순서 규칙을 따를 것).
- 스크립트(.sh)도 항목 하나로 번호를 차지한다(폴더 `scripts`).

## 6. 모음(기종별 필터) — `tools/make_collections.py`
- 순정 메뉴의 숨기기 기능을 이용: `/userdata/gamemenu.cfg`(6228B)의 **오프셋 0x830부터 1225바이트 = 보임 비트맵**(게임 i의 비트 = 바이트[i//8]의 비트 i%8, LSB 먼저,
  파일 앞 8바이트와 0x1000~ 영역은 난수/상태(저장 시마다 바뀜) — 우리는 `gamemenu_baseline.cfg`(원래 상태) 기반으로 비트맵과 CRC만 바꾼 cfg를 만든다.
- 분류: `gl_class.json`(gl 인덱스→시스템; `game_list.csv`의 파일명 매칭). 수: 전체 9800 / 아케이드 5065 / 메가드라이브 1738 / SNES 1767 / NES 1202 / PS1 36.
  gl.bin에는 같은 게임이 여러 목록에 중복 등록되어 있고 `END_OF_THE_LIST` 구분 항목이 있다(항상 보임으로 둠).
- 모음 스크립트(`10_Col_All.sh`…`15_Col_PS1.sh`): 최초 1회 `original.cfg`로 현재 설정 백업 → `cat 모음.cfg > /userdata/gamemenu.cfg` → sync.
  추가 게임(9801+)은 숨김 대상이 아니라 항상 목록 끝에 남는다(스크립트 접근 보장).
- 한계/주의: cfg 복사로 다른 설정(볼륨 등)이 baseline 값으로 돌아간다. 메뉴 안에서 즉시 전환(재시작 없이)하려면 줄 배열/총개수/페이지를 메모리에서 바꿔야 함(미착수).

## 7. 화면/기타 설정 단서 (아직 에디터에 미구현)
- `E:\pandory\pandory.xml`(주석에 옵션 설명): `<setting name=…>` 전역 — `stretchDisplay`(false=원래 비율, true=전체 늘림; 순정은 늘림), `smoothPixels`,
  `scanlineOpacity`, `useBetterScanlines`, `forceSmoothCGA`, `disableDipswitches`, `disableAutomaticCredits`, `allowRotation`, `menuMusic/musicVolume`, …
  `<emulators>`: 폴더↔코어↔keymap. `<roms>`: `<rom name="xxx.zip" core= keymap= speed= rotate= forceWidth= forceHeight= customOptions= customCfg=/>`.
- 코인: 순정 게임은 코인을 넣어야 시작(시간 99초 제한). 추가(Pandory) 게임은 `disableAutomaticCredits`=true라 바로 실행.
- 메뉴 배경 `E:\user_bg.bmp`(메뉴가 `/tmp/user_bg.bmp`로 복사), 대기 영상 `demo*.avi`(해상도별), 오른쪽 "NEW GAME" 영상은 펌웨어 `/user_add.avi`.
  순정 게임 미리보기는 `E:\movies\<romname>.avi`(H.264 640x480 30fps 약 6.5초 무음). 추가 게임에는 미리보기가 안 붙는다(미해결).
- 이미 있는 참고 파일: `reference/pandory.xml`(현재 카드 설정 사본), 설명서: `D:\Backup\pandorytool_v114\x\documentation\`.

## 8. 복구 방법
- 메뉴가 이상하면: 카드를 PC에 꽂아 **`D:\Backup\pandory_orig\pandory.orig` → `E:\pandory\pandory`**(훅 제거), 필요하면 `E:\pandory\patch.txt` 삭제(이름 패치 중단).
- 모음 때문에 목록이 이상하면: 메뉴 끝의 `[모음] 전체 게임 보기` 실행 또는 `E:\pandory\collections\original.cfg`를 `/userdata/gamemenu.cfg`에 되돌림(스크립트로).
- 카드가 망가지면: `D:\Backup\PandoraSaga_E.img`로 같은 크기(≥28.9GB)의 카드에 복원(Rufus/Win32 Disk Imager), FAT32 파티션 오프셋 4MB 주의.
- 시도해 보았다가 되돌린 것: roms_md 폴더에 롬 넣기(번호 칸만 생기고 실행 불가), 순정 `md_*.zip` 바꿔치기(실행 내용 불변) — 현재 카드는 원상 복구됨.

## 9. 미검증 / 남은 일 (우선순위)
2. **에디터(PC 프로그램) 설계·구현**: Windows, 더블클릭 실행(권장 Python+Tkinter/PySide 단일 exe 또는 가벼운 로컬 웹UI). 기능 후보:
   게임 추가(드래그&드롭, 기종 폴더 자동 선택·확장자 검사·이름 입력) / 이름·기종태그 편집(`names_map.txt`) / 순서와 번호 미리보기(§5 규칙) /
   모음 생성·편집(§6; 사용자 정의 모음 가능) / 화면 설정(`pandory.xml` 안전 편집+주석 보존) / 게임별 코어·비율·속도 / 배경·영상·음악 교체(ffmpeg로 변환) /
   카드 백업·복구(이미지) / **자동 훅 설치·제거 도구**(Pandory 바이너리 패치 + auto.sh) / 점검(훅 있는지, patch.txt 최신인지).
3. 추가 게임 미리보기 영상·이미지(메뉴 오른쪽 패널) — 아직 방법 없음. `/user_add.avi`는 펌웨어 고정.
4. 즉시 전환형 모음(메모리 직접 수정) — 선택 사항, 어려움.
5. 한글 이름이 28자 넘을 때 줄임, 기종별 메뉴 분리의 더 나은 UI — 선택 사항.
6. Pandory가 업데이트되면 훅/주소가 바뀔 수 있다. 메뉴 주소(§3)는 **이 펌웨어 빌드 고정값**(`gamemenu` 9,077,912 B, 빌드 2020) — 다른 기기/펌웨어에서는 재분석 필요.

- `pandora_names.py`: 임시 폴더에 가짜 카드 구조(`pandory/pandory.xml`, `roms_pandory/…`)를 만들어 (a) 폴더 알파벳순/파일 바이트순 정렬, (b) `patch.txt`에 NUL 없음·줄 형식,
  (c) 200개 초과 경고, (d) 한글 UTF-32LE 인코딩 라운드트립을 검증. **실제 `E:`를 건드리는 시험 금지**(드라이브 인자를 항상 요구).
- `make_collections.py`: baseline cfg로 비트 수 합계(9800/5065/1738/1767/1202/36)와 **CRC32 재계산 일치**, 길이 6228 유지.
- 에디터 파일 쓰기는 항상 **백업 후 쓰기**(원본을 `*.bak`/`collections\original.cfg`로), 카드 경로는 사용자가 확인한 드라이브로 제한(시스템 드라이브/내장 디스크 거부).
- 새 매개변수가 없는 옛 스크립트가 실제 폴더에서 돌지 않게 하는 시험(relay 스킬의 "위험 노트")을 따를 것.

## 11. 도구/자료 목록
- `tools/` : `pandora_names.py`(이름 패치 생성), `make_collections.py`(모음 cfg+스크립트), `update_names.bat`(더블클릭), `unsq.py`(PySquashfsImage로 p4 풀기, 사용자 site-packages라 `python -I` 금지),
  `gm.py`/`armdis.py`/`elfdis.py`/`xref2.py`(gamemenu 분석: capstone, 가상주소↔파일오프셋 변환, 문자열 xref). **분석 도구는 PC에 capstone 필요(이미 설치됨).**
- `reference/` : 현재 카드의 `auto.sh`, `patch.txt`, `names_map.txt`, `pandory.xml`, 스크립트 사본, `gamemenu_baseline.cfg`, `collection_md_example.cfg`, `gl_class.json`,
  `game_list.csv/md`(카드 `E:\roms` 전체 목록: 기종 분류), `addgame_list_sample.bin`(실제 /tmp/addgame_list 덤프), `card_readme2_gbk.txt`(제작사 설명, GBK).
- 외부 조사: Team Pandory 사이트/GitHub(TeamPandory/pandorytool; 기기 쪽 `pandory` 바이너리는 비공개), RA2Pandora(alanlengruber; 구형 DX에서 `(RA)` 항목이 이름으로 보임 →
  DX2 Plus 펌웨어 메뉴가 더 새 것이라 이름을 안 그리는 것으로 추정), 웹에는 `name.bin/gl.bin/addgame_list` 설명 없음. 월광보합 "끝판왕" 펌웨어는 기종별 목록 필터링 방식(우리 모음과 같은 접근).

---
## 12. 추가 조사 (2026-11-01 오후): 커널/부트로더/플래시 전체 덤프, OS 교체 가능성
- **작업 카드가 바뀜**: 원본 카드 E:(58GB 표시 = **가짜 용량**, 실제 약 29GB, 일부 롬 zip이 CRC 오류)는 보관용. **주 작업 카드 = F:(진짜 32GB, 순정 이미지 `PandoraSaga_E.img`를 복구한 뒤 E:의 Pandory 환경을 복제)**.
  F:의 PS1 게임(`romsp`)은 0바이트 더미로 바꿔 여유 공간 약 16GB 확보(BIOS `scph1001.bin`/`bios.bin`, `.srm`은 유지). 원본 PS1 롬은 E: 카드와 이미지에 있음.
  **카드를 최소 구성(순정 롬 대부분 제외)으로 만들면 기기가 부팅하지 않았다**(원인 미확인; 파일 이름만 맞춘 더미(빈 zip, 작은 avi)로 채운 카드도 실패). 이유를 모르니 카드 파일 구조는 원본 그대로 유지할 것. (이름·개수만 같은 더미는 시험 안 해봄: F 복구 후 더미 추가 시험은 PS1만 함.)
- **내부 플래시 전체 덤프 완료**: `D:\Backup\flash_dump_2026-11-01\flash_full.img`(229,113,856 B = /dev/rkflash0 전체, 부트로더 영역 포함), `kerninfo\`(cmdline, dmesg, config.gz 등).
  GPT: `uboot`(LBA 8192, 1MB, 안에 U-Boot) / `trust`(2MB) / `boot`(LBA 14422, 4.1MB, **Android boot.img: 커널 3,999,680B, ramdisk 없음**) / **`rootfs`**(LBA 22870, 89.8MB, squashfs gzip) / `oem` / `userdata`(5.7MB ext2).
  LBA 64~320에 idbloader(난독화, DDR init+miniloader)가 들어 있다. 플래시는 SPI NAND(`sfc_nand id 98 cb 98`)이며 `storagemedia=nand`로 **내부에서만 부팅**.
- **커널**: 4.4.159 armv7(SMP), `CONFIG_KEXEC` 없음, `BLK_DEV_LOOP` 없음, `OVERLAY_FS` 없음. 있음: SQUASHFS(zlib/lzo), EXT4, VFAT, EXFAT, FUSE, NAMESPACES/USER_NS, CGROUPS, SECCOMP, ZRAM,
  USB_GADGET, MALI400(DT), DRM_ROCKCHIP, HIDRAW/EVDEV, 모듈 지원(`/lib/modules` 비어 있음). `FB_ROCKCHIP` 없음(framebuffer는 DRM 에뮬레이션). 도구: `chroot`, `pivot_root`, `switch_root`, `losetup`(loop 장치 없어 무용), `mkfs.ext4`, `e2fsck`, `fdisk`.
  → **카드로 다른 커널/OS 부팅은 불가**(kexec 없음, 내부 NAND 부팅). 가능: 같은 커널 위에서 `chroot`/`switch_root`로 **다른 유저랜드**(카드의 ext4 파티션 또는 tmpfs) 사용. 카드의 FAT(vfat, fmask=133)에서는 직접 exec 불가 → **`/lib/ld-linux-armhf.so.3 /path/to/binary`** 로 실행하거나 /tmp(tmpfs)에 복사. (`dlopen`은 FAT에서도 됨.)
- **메모리**: 전체 RAM **약 241MB**(여유 약 140MB), CPU 4코어(Cortex-A7), tmpfs /tmp 약 120MB. 화면 1280x720(HDMI-A-1, LVDS-1 둘 다), DRM `card0`·`renderD128`.
  GPU: libmali **utgard-400 r7p0 wayland 변형**(`libEGL/libGLESv2/libgbm`이 모두 이것에 심볼릭 링크), `libSDL2-2.0.so.0.7.0`(2.0.7), `libSDL2_image`, libdrm, libfreetype, libpng12/libjpeg/libturbojpeg, libssl/crypto 1.0.0, libstdc++ 6.0.22, libasound. 입력: `/dev/input/event0 = gpio-keys` 하나(아케이드 버튼 경로는 미확인; 메뉴는 JSIOCGNAME/gamepad 처리).
- **U-Boot 기능(`flash_full.img` uboot 파티션 문자열)**: `found IDB in SDcard`, `sdfwupdate`(SD 카드 펌웨어 업데이트), `rkusb`/`rockusb`(USB 케이블로 PC에서 플래시 쓰기; "Please connect USB cable"), 리커버리 부팅, `gpt write mmc`.
- 순정 RetroArch 1.7.4(`/usr/bin/retroarch`, 닫힌 소스)에는 메뉴 드라이버(rgui, xmb, glui 등)가 들어 있다. 순정 `retroarch.cfg`는 `input_joypad_driver="nul"`, `input_driver="udev"`, `audio_driver="alsathread"`.
  카드 코어 위치: 순정 `/usr/lib/libretro/`(fbalpha2012/fbalpha, mame2003/2010, genesisplusgx, snes9x/snes9x2002, fceumm, pcsx_rearmed, beetle pce fast/supergrafx, bluemsx, fmsx), Pandory `E:\pandory\cores\`.

## 13. 다음 계획 — 목표: EmulationStation(ES)
**원칙: 내부 플래시는 쓰지 않는다.** 모든 단계는 카드 파일로, 되돌리기 가능.
1. **(진행) RetroArch 자체 메뉴 시험**: 카드 `roms_pandory\scripts\04_RetroArchMenu.sh`(메뉴 `레트로아크 메뉴 시험`)가 순정 retroarch를 `--menu`로 2분간 띄운다(자동 종료). 로그 `ra_menu.log`. 입력(아케이드 버튼)이 메뉴를 조작하는지가 핵심.
3. **시험 바이너리**: SDL2(KMSDRM/GLES2 또는 wayland-gbm 경로 확인) + 입력 이벤트 출력 프로그램을 `ld.so`로 실행해 화면/입력/오디오가 되는지 확인.
4. **ES 선택**: 램 241MB를 고려한 가벼운 포크(예: ES-fcamod 계열, 이미지/영상 비활성 테마). 의존성: SDL2(+기기 것 재사용), FreeType, libcurl(선택), pugixml(내장), FreeImage 대체(stb/SDL_image).
5. **게임 실행 연결**: ES의 실행 명령을 `/usr/bin/retroarch --fullscreen -c <cfg> -L <core> <rom>`로(순정 `start_game.sh` 참고, 환경변수 `XDG_CONFIG_HOME=/data XDG_RUNTIME_DIR=/data`).
   코인(순정은 `/tmp/pipe1` 카운터, `emulotar`가 `/dev/mem`으로 읽음)과 순정 메뉴의 99초 시간 제한은 ES에서는 쓰지 않음(추가 게임은 이미 `disableAutomaticCredits`).
6. **순정 메뉴 대체(내부 플래시 불변)**: Pandory 바이너리의 `/usr/bin/gamemenu -qws` 명령 문자열을 우리 시작 스크립트로 교체(§4와 같은 방식; **길이 제한**: 기존 문자열 길이 안). 순정 메뉴로 돌아가는 토글(파일 존재 여부로 분기) 필수.
7. **PC 에디터**와 통합: ES 게임 목록 XML(`gamelist.xml`), 모음, 이름, 비율·화질 옵션을 에디터가 생성.

---
## 14. 현재 상태 요약 (2026-11-01 저녁, 작업 중단 시점) — 여기부터 이어서 읽을 것
### 14.1 카드/장치
- **작업 카드 = F:**(진짜 32GB, PandoraSaga 이미지 복구 + Pandory 환경 복제, PS1 롬은 0바이트 더미, 여유 약 16GB). **E:는 보관용 원본**(58GB 표시 = 가짜 용량, 일부 롬 zip CRC 오류; 쓰지 말고 가능하면 건드리지 않기).
- 이 PC: Windows 11 (빌드 26300), 호스트 `pwsh`가 **32비트**로 뜸 → `bcdedit` 등은 `C:\Windows\Sysnative\`로 호출. **가상화는 켬**(`hypervisorlaunchtype Auto`, 재부팅 완료) → WSL2(Ubuntu 24.04, 16코어, 7.5GB) 정상.
  **WSL은 인터넷(TCP)이 안 된다**(ping만 됨; mirrored 시도 `.wslconfig` 생성했으나 무효; Tailscale/방화벽 의심). 우회: **Windows에서 내려받아 `/mnt/d/...`로 전달**. (`tools/winproxy.py` 임시 프록시도 WSL→Windows loopback이 막혀 쓸모없었음.)
- 빌드 환경(WSL): `/opt/armv7-toolchain`(Bootlin armv7-eabihf glibc-stable-2018.02-2, GCC 6.4, glibc 2.26, **`arm-linux-gcc`**), cmake 3.29.6, ninja 1.12.1, make 4.4.1(.deb), 파일 원본은 `D:\Backup\toolchain_dl\`.
  SDL 2.0.7 소스: `/opt/src/SDL-release-2.0.7`(configure로 `include/SDL_config.h` 생성). 링크는 기기 라이브러리 `D:\Backup\firmware_extract\usr\lib\libSDL2-2.0.so.0.7.0`에 직접(추출본엔 심볼릭 링크가 없음).
  빌드 예: `export PATH=/opt/armv7-toolchain/bin:$PATH; arm-linux-gcc -O2 -D_GNU_SOURCE -I/opt/src/SDL-release-2.0.7/include X.c -o X $FX/usr/lib/libSDL2-2.0.so.0.7.0 -lm -ldl -lpthread`.
  주의: PowerShell 여기문자열은 CRLF → `sh`로 보내기 전 `-replace "`r",""`; WSL로 보낼 때 `wsl -e sh -c "..."`의 따옴표 중첩 주의(스크립트는 stdin으로).
### 14.2 시험 결과 (기기에서 확인됨)
- **SDL2(KMSDRM+GLES2) 직접 구동 성공**: 1280x720@60, `opengles2` 렌더러 200fps대. 아케이드 조이스틱·버튼은 **키보드 이벤트**로 들어온다(방향키, `A~F`(scancode 4~9), `1`(1P시작) 등; 조이스틱 장치 0개). 코인 버튼 키는 미확인(`5`로 가정). `ld-linux-armhf.so.3 --library-path /usr/lib:/lib`로 FAT 카드의 ELF를 실행.
- **순정 RetroArch(`hhh` 개조판)는 롬 경로를 argv로 받으면 SIGSEGV, `--menu`는 즉시 종료(검은 화면+Pandory 스캔라인 줄)** → 순정 RetroArch를 직접 쓰는 길은 막힘(Pandory가 `/tmp/retro_tmp`에 경로를 넣어 `hhhh…` 자리표시자로 실행하는 구조).
### 14.3 만든 소프트웨어 (모두 `tools/`, `bin/`)
- `tools/front/minosfront.c` + `libretro_host.inc` + `NanumGothic.ttf`: SDL2 + stb_truetype(헤더는 `D:\Backup\tools\front\stb_*.h`, 저장소엔 미포함 — 다시 내려받을 것), 빌드 결과 `bin/minosfront_armv7`(92KB).
  기능: `roms_pandory/<폴더>` 스캔(폴더→기종 표, 코어 `pandory/cores/*.so`), 제목은 `pandory/names_map.txt`, 목록 UI, **libretro 호스트**(환경 콜백 최소 구현: 픽셀형식·시스템/저장 폴더·로그·변수 NULL, 비디오 SDL 텍스처, 오디오 SDL 큐, 입력 키보드→RetroPad(A→B, B→A, C→R, D→Y, E→X, F→L, `1` Start, `5` Select), SRAM `.srm` 저장/불러오기, 프레임 페이싱).
  종료: `1+E+F` 1초 누름 또는 `Q`. 미구현: 인게임 메뉴, 저장 상태, 코어 옵션(변수), 스캔라인/필터, 정수 배율, 버튼 매핑 설정, 코인/시간 제한, 비디오 영상/이미지, 컬렉션 연동, 순정 메뉴 대체(자동 시작).
- `tools/sdltest/sdltest.c`(화면·입력 시험), `bin/sdltest_armv7`.
- 카드 스크립트 `card_scripts/`: 00_Names(이름 수동 적용), 01_SaveCfg, 02_KernelInfo, 03_FlashDump, 04_RetroArchMenu(실패 확인된 시험, 삭제 가능), 05_SDLTest, 06_MinosFront, 10~15_Col_*(모음), Reboot, scripts_off 보관본.
### 14.4 결정 대기 / 다음 할 일
3. MinosFront를 **부팅 때 자동 시작**: Pandory 바이너리의 `/usr/bin/gamemenu -qws` 명령 문자열을 시작 스크립트로 교체(길이 제한), 순정 메뉴로 돌아가는 파일 토글 필수. 코인/99초 제한 처리 방침 필요.
4. 모음(컬렉션) 시험 결과 미수신(재부팅 없는 새 스크립트 포함).
5. 무선 랜: 커널에 WLAN/USB_NET 드라이버 **없음**(`CONFIG_WLAN`, `USB_NET_DRIVERS` 꺼짐, 모듈 사용 가능하나 4.4.159용 소스 없음) → 지금은 불가, 필요하면 별도 과제(칩 종류 확인).
6. PC 에디터(§9)와 통합: 에디터가 `names_map.txt`, 모음, `front.cfg`, ES형 목록 설정, 카드 백업/복구, 훅 설치를 다루도록.
### 14.5 위험·금지 (재확인)
- 내부 플래시/uboot/idbloader **쓰기 금지**(전체 덤프는 `D:\Backup\flash_dump_2026-11-01\flash_full.img`). 카드 파티션/포맷은 반드시 대상 디스크 검증 후. 삭제는 휴지통. WSL 내 설치는 Windows에 영향 없음.

## §15. 2026-11-01 — Direction B (real RetroArch) decided + built
- User chose cross-building real RetroArch. Built v1.22.2 (RA2Pandora drm patch, DRM/KMS+GLES2+ALSA, no network/cheevos/freetype) via `D:\Backup\tools\ra_build\{setup_sysroot.sh,build_retroarch.sh}` in WSL distro `Ubuntu` (use Sysnative wsl.exe). Output `ra_build\out\retroarch` (8.8MB, ARMv7 hf).
- Deployed to F: `pandory/ra/{retroarch,ra.cfg}` + test menu script `07_RetroArchReal.sh` (picodrive, first genesis ROM; log `F:\ra_run.log`). NOT yet tested on device.
- Next: test result → if "drm" video driver shows no menu text, try `gl`+`kms` context; add Korean font (freetype build) ; integrate launch into MinosFront.

### §15 update — device test result (2026-11-01)
- 07_RetroArchReal (menu 9827) **works**: real RetroArch 1.22.2 + picodrive ran a Mega Drive game (DRM plane, ALSA, udev input OK). Log: F:\ra_run.log.
- Menu numbers: 9827 진짜 레트로아크 시험, 9828–9833 collections, 9834 재부팅 (names_map is keyed by file name; run tools\pandora_names.py F: after adding scripts).
- TODO (in order): (1) set RetroArch menu hotkey in pandory\ra\ra.cfg (e.g. input_menu_toggle_gamepad_combo / keyboard key) and test rgui; (2) rebuild with freetype for Korean menu font; (3) MinosFront launches games via `retroarch -L core rom` (replace built-in player or keep as fallback); (4) fix playlist write error (playlists dir); (5) coin key, aspect option, collections test still unreported.
- Build: `D:\Backup\tools\ra_build\build_retroarch.sh` (run in WSL distro `Ubuntu` via Sysnative wsl.exe, as root). Source /opt/src/RetroArch.
