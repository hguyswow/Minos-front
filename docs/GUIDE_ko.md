# MinosFront 사용 가이드 (한국어)

판도라 사가 DX2 Plus 용 런처입니다. 모든 파일은 **SD 카드**에만 들어갑니다.

## 1. 설치
1. 저장소의 `card/` 안 내용을 SD 카드 맨 위(루트)에 복사합니다. 기존 `roms/`, `movies/` 는 그대로 둡니다.
2. RetroArch 1.22.2 ARM 빌드를 `pandory/ra/retroarch` 로 넣습니다. (`tools/build_retroarch.sh` 로 직접 빌드)
3. 기기 메뉴 → 스크립트 → **MinosFront 시험** 을 실행합니다.
4. (선택) 미리보기 사진: PC 에서 `python tools/build_previews.py F:` 를 실행하면 카드의 `movies/*.avi` 에서 3장씩 뽑아 `pandory/snap/` 에 저장합니다.

## 2. 화면과 조작
| 화면 | 조작 |
|---|---|
| 기종 선택 | ←→ 기종 고르기, A 열기, B 또는 Start 종료(원래 메뉴), **코인** = 한국어/English |
| 게임 목록 | ↑↓ 이동, ←→ 10개씩, E/F 100개씩, A 실행, B 뒤로, **C 즐겨찾기**, **D 다음 글자(ㄱ→ㄴ→…)**, **코인 = 이 게임 설정**, **Start = 게임 중 단축키 도움말** |
| 이 게임 설정 | 화면 비율, 화질, 이어하기, 버튼 배치 (←→ 바꾸기, A 저장/편집) |

기종 칸 중 **최근 한 게임**, **즐겨찾기**, **RetroArch 설정**(게임 없이 RetroArch 메뉴), **버튼 테스트**, **원래 메뉴**(판도라 기본 화면)가 있습니다.

## 3. 게임 중 단축키 (Start 를 누른 채)
| 조합 | 기능 |
|---|---|
| Start + 코인 | 게임 끝내기 |
| Start + A / E | 상태 저장 / 불러오기 |
| Start + F | 일시정지 |
| Start + B | 리셋 |
| Start + D | 빨리감기 켜기/끄기 |
| Start + ↑ / ↓ | 저장 칸 번호 |
| Start + → | 소리 크게 |
| Start + ← | 소리 작게 |
| **코인 + 버튼** | 그 버튼 **연사** 켜기/끄기 |
| Start 만 4초 | 강제 종료 (메뉴에 갇혔을 때) |

기기 버튼: 윗줄 B C D, 아랫줄 A E F, 그 밖에 Start, 코인(=Select), 방향키.

## 4. 게임별 버튼 배치
게임 목록 → 코인 → **버튼 배치** → A.
- 윗줄/아랫줄 6칸에 그 게임의 버튼을 **하나 또는 여러 개 동시에** 지정할 수 있습니다. 예) 네오지오 "강" = 버튼A+버튼B.
- **D** 로 예시(순정 / 순서대로 / 네오지오식 / 2버튼 위아래), **코인** 으로 저장 범위(이 게임만 / 같은 종류 전체), **Start** 저장, **B** 취소.
- 저장 위치: `pandory/front/keymaps.tsv`. 순정으로 되돌리려면 "순정"으로 저장합니다.
- 게임의 버튼 이름은 `pandory/buttons.tsv` (코어가 알려 준 이름) 에서 옵니다. `tools/desc_batch.sh` 로 다시 만들 수 있습니다.

## 5. 이어하기
게임을 끝낼 때 자동으로 저장하고, 다시 실행하면 그 자리에서 시작합니다. 게임별로 끌 수 있고(이 게임 설정 → 이어하기), 전체 기본값은 `pandory/front/front.cfg` 의 `resume=0/1` 입니다.

## 6. 설정 파일 (카드 `pandory/front/`)
| 파일 | 내용 |
|---|---|
| `front.cfg` | `quit_hold=4`(강제 종료 초), `resume=1`, `player=builtin`(RetroArch 대신 내장 플레이어), `ratio=off` |
| `favorites.txt`, `recent.txt`, `last.cfg` | 즐겨찾기, 최근 게임, 마지막 위치 |
| `game_settings.tsv` | 게임별 화면 비율/화질/이어하기 |
| `keymaps.tsv` | 게임별/종류별 버튼 배치 |
| `lang.txt` | `ko` / `en` |

카드 쓰기를 줄이려고 위 파일은 **바뀔 때만**(즐겨찾기 누름, 게임 시작, 목록 나갈 때, 설정창 닫을 때) 저장합니다. `ra.cfg` 는 깨질 때를 대비해 `ra.cfg.good` 사본을 자동으로 만들고, 깨졌으면 시작할 때 복구합니다.

## 7. 시작할 때 MinosFront 자동 실행 (실험 기능)
- 켜기: 스크립트 "시작시 미노스프론트 켜기", 끄기: "시작시 미노스프론트 끄기". 스위치 파일은 `pandory/front/autostart`.
- 판도라 메뉴가 뜰 때 `auto.sh` 가 메뉴를 잠시 멈추고 MinosFront 를 띄웁니다. 끝나면 메뉴를 종료해 판도라가 새로 띄우게 합니다.
- 6초 안에 끝나는 실패가 2번 연속이면 스스로 꺼지고(`autostart_failed`), 판도라가 새 메뉴를 안 띄우면 12초 뒤 직접 `gamemenu` 를 실행합니다.
- 이 기능은 판도라 실행파일의 훅(`auto.sh` 를 부르는 문자열 패치)이 있어야 합니다. 자세한 내용은 `docs/HACKING_NOTES_ko.md`.

## 8. 문제 해결
| 증상 | 확인 |
|---|---|
| 게임이 실행 안 됨 | 카드의 `ra_run.log`, `front.log` |
| 메뉴 번호와 이름이 어긋남 | `python tools/pandora_names.py F:` 를 다시 실행 (스크립트를 추가/삭제했을 때) |
| 화면이 이상함 | `pandory/bin/` 에 있는 이전 버전(`minosfront.vN`)을 `minosfront` 로 덮어쓰기 |
| 소리가 느리고 지직거림 | `pandory/ra/.asoundrc`(16비트 ALSA 설정)와 `ra.cfg` 의 `audio_device="ra16hw"` 확인 |

## 9. PC 에서 시험하기 (기기 없이)
WSL + QEMU(user mode) 로 화면을 그려 이미지로 볼 수 있습니다. `tools/front_test.sh` (키 입력 시뮬레이션, 스크린샷), `tools/test_keys.sh` (버튼 배치 생성), `tools/test_autostart.sh` (자동 실행 훅 모의 시험). 시험 모드(`MINOS_KEYS`, `MINOS_SNAP`)에서는 카드에 아무것도 쓰지 않고 게임도 실행하지 않습니다.
