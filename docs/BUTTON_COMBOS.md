# 판도라 사가 버튼 조합표 (직접 만든 RetroArch 1.22.2용)

적용 파일: 카드의 `pandory/ra/ra.cfg` (원본 `ra.cfg.bak`). 순정 `retroarch.cfg` 의 버튼 배치를 그대로 쓰고, 특수 기능은 **코인을 누른 채** 다른 버튼을 눌러 사용한다.

## 기기 버튼 배치 (형님이 알려 준 표기)
```
 윗줄:  B   C   D        RetroArch 버튼:  Y   X   A
 아랫줄: A   E   F        RetroArch 버튼:  B   L   R
 그 밖:  Start (키 1)   Coin (키 I — 버튼 시험 기록에서 확인, 게임에서는 Select 로도 쓴다)   방향키
```
순정 매핑(키 → 버튼): D→A, A→B, C→X, B→Y, E→L, F→R, 1→Start, 5→Select. 2P: 방향 PageUp/PageDown/Home/End, A=N, B=K, X=M, Y=L, L=O, R=P, Start=2, Select=6.

## 특수 기능 (Start 를 누른 채 — 2026-11-02 변경)
코인(셀렉트)은 연사 전용으로 쓰기 때문에, 단축키 기준 키를 코인에서 **Start** 로 옮겼다.
| 조합 | 기능 |
|---|---|
| Start + 코인 | 게임 끝내기 |
| Start + A | 지금 상태 저장 |
| Start + E | 저장한 상태 불러오기 |
| Start + F | 일시정지 |
| Start + B | 게임 리셋 |
| Start + D | 빨리감기 켜기/끄기 |
| Start + 위 / 아래 | 저장 칸 번호 올리기 / 내리기 |
| Start + 오른쪽 | 슬로모션 (누르고 있는 동안) |
| Start + 왼쪽 | 화면 캡처 |
| Start + C | RetroArch 메뉴 (확인 필요). 코인 2초 누르기(RetroArch 설정)도 가능 |
| 코인 + 버튼 | 그 버튼 연사 켜기/끄기 (RetroArch Turbo "Classic Toggle", 기기에서 확인됨) |
| Start 만 4초 | MinosFront 에서 실행한 RetroArch 강제 종료 (메뉴에 갇혔을 때) |

기본 화질은 "부드럽게"(video_smooth=true, GPU 가 처리하므로 CPU 부하 없음). 화면 비율 기본은 가득 채움. 게임별로는 MinosFront 의 게임 목록에서 코인 버튼으로 바꾼다.

## 확인 필요
- 코인 버튼은 키 `I` 를 내보내는 것으로 보인다(이전 버튼 시험 기록: Start=`1`, 그 다음 눌린 버튼=`I`). `08_KeyTest` 로 확정한다. 순정의 Select(`5`)에 해당하는 물리 버튼은 이 기기에 없다.
- 코인만 단독으로 누르면 게임에서는 Select 로 동작해야 한다(시험 필요).
- 메뉴 안에서는 D = 확인, A = 뒤로.

## 되돌리기
`pandory/ra/ra.cfg.bak` 를 `ra.cfg` 로 복사하면 조합 이전(RetroArch 기본 키)으로 돌아간다.

## 메가드라이브 / 32X 전용 배치 (카드의 `pandory/ra/layouts/genesis.cfg`)
기기의 2x3 버튼이 실제 메가드라이브 6버튼 패드 모양과 같다.
```
 윗줄:   B → X     C → Y     D → Z
 아랫줄:  A → A     E → B     F → C
```
(순정 배치에서는 메가드라이브 A·B·C 가 윗줄 B, 아랫줄 A, 윗줄 D 로 흩어져 있었다.)
다른 기종은 순정 배치 그대로. 이 파일은 텍스트라서 다시 빌드하지 않고 바꿀 수 있다.

## 게임별 버튼 배치 (MinosFront, 2026-11-02)
게임 목록에서 **코인** → "이 게임 설정" → **버튼 배치** → A. 윗줄 B C D / 아랫줄 A E F 여섯 버튼 각각에 그 게임의 버튼을 하나 또는 **여러 개 동시에** 지정한다
(예: 네오지오 "강" = A+B). D = 예시 배치(순정 / 순서대로 / 네오지오식 / 2버튼 위아래), 코인 = 저장 범위(이 게임만 / 같은 종류 전체), Start = 저장, B = 취소.
- 게임의 버튼 이름은 코어가 알려 준 것(`pandory/buttons.tsv`, `tools/desc_batch.sh` 로 만듦): 네오지오 = 버튼A~D, 캡콤 = 약/중/강 손·발 등.
- 저장: `pandory/front/keymaps.tsv`. 순정으로 되돌리려면 예시 "순정"으로 저장하거나 그 줄을 지운다.
- 동작 원리: 키를 RetroArch 버튼에 직접 연결하고, 한 키로 두 버튼은 남는 버튼(L3 R3 L2 R2)을 같은 키에 묶은 뒤 remap 파일(/tmp)로 옮긴다. `tools/test_keys.sh` 로 PC에서 검증.
- 이어하기: 같은 설정창의 "이어하기"(기본 켬). 끝낼 때 자동 저장, 다시 실행하면 그 자리부터.
