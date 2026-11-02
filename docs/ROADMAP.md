# MinosFront — 로드맵 / 계획 (2026-11-02 작성)

현재: 오락실 테마 런처(MinosFront v8), 게임별 설정, 게임별 버튼 배치(한 키 = 여러 버튼), 이어하기, 영/한 UI, 단축키(Start), 연사(코인), 시작 화면.
카드 안에서만 동작. 기기에서 확인된 것: 기본 UI·게임 실행·단축키·연사·게임별 화면 설정. **미확인**: 버튼 배치 매크로(한 키=두 버튼), 이어하기, 영문 모드, 시작 화면, 부팅 개입(`m` 래퍼).

## 0. 내일 기기 시험 체크리스트 (순서대로)
1. 9826 MinosFront: 시작 화면 → 기종 선택 → 코인으로 English/한국어 → 아케이드 목록·미리보기·★·D 점프
2. 게임 실행 → Start+코인 종료 → 목록 복귀 → 같은 게임 재실행(이어하기) → "최근 한 게임"
3. 코인(게임별 설정) 4줄 → 버튼 배치: 네오지오 게임(samsho2 등)에서 윗줄 D가 두 버튼을 동시에 누르는지
4. 영문 모드에서 패미컴 목록(영어 이름/로마자)
5. 9848 USB 장치 기록(동글 꽂고) → `usb_probe.log`
6. 마지막: 부팅 개입(`pandory.wrapper`) — `docs/BOOT_RESEARCH.md` 4절 순서, `wrapper.log` 확인

## 1. 안정화 백로그 (효과 큰 순)
| # | 항목 | 내용 | 비고 |
|---|---|---|---|
| S1 | 크래시 보호 | MinosFront에 SIGSEGV/SIGABRT 핸들러: 로그(`front_crash.log`) 남기고 종료 코드 반환 → `m` 래퍼의 빠른 실패 카운터와 연동 | 부팅 개입의 안전망 |
| S2 | 안전 모드 | 시작할 때 B(또는 Start)를 누르고 있으면 MinosFront를 건너뛰고 순정 메뉴 (카드를 안 빼고 탈출) | `m` 래퍼에서 /dev/input 확인 또는 MinosFront 스플래시에서 B 2초 |
| S3 | 사용자 데이터 보호 | favorites/recent/keymaps/game_settings를 쓸 때 `.bak` 1세대 유지, 시작할 때 깨진 파일 복구 | ra.cfg.good 방식 확장 |
| S4 | 해상도 대응 | 기기 화면(1024x600 / 640x480 / 384x224 / HDMI 720p)별 레터박스·글자 크기 확인 | 지금은 1280x720 논리 해상도 고정 |
| S5 | 로그 정리 | front.log, ra_run.log, wrapper.log 크기 제한(마지막 N줄) | 카드 쓰기 절감 |
| S6 | 성능 모드 | 효과(스캔라인, 노이즈, 전구 애니메이션) 끄는 "가벼운 모드" 토글; 목록 스크롤 프레임 측정 | 오락실 테마가 느리면 즉시 필요 |
| S7 | 게임 전환 안정화 | RetroArch 종료 후 화면 재생성 실패 시 재시도, 오디오 장치 재오픈 | 장시간 사용 시험 |
| S8 | 시험 자동화 | `front_test.sh` 시나리오를 파일로 모아 회귀 시험(스크린샷 비교) | 지금은 수동 |

## 2. 기능 백로그 (가치/난이도)
| # | 기능 | 설명 | 난이도 |
|---|---|---|---|
| F1 | **게임 정보 패널** | 연도·제조사·장르·인원: libretro-database(`metadat`)의 MAME/FBNeo/No-Intro 자료를 CRC·이름으로 연결 (영어 이름 만든 방식 그대로) | 중 |
| F2 | **장르/제조사 필터** | F1 위에서 "슈팅 / 격투 / 액션…" 칸 (기종 선택에 가상 칸 추가) | 중 |
| F3 | **스캔라인 화질 옵션** | 화질에 "스캔라인"(GLES2 간단 GLSL 쉐이더) 추가. Mali-400에서 가벼운 것만 | 중 (성능 시험 필요) |
| F4 | 마지막 게임 바로 이어하기 | 기종 선택 첫 칸 "▶ 마지막: 사무라이쇼다운2", A 한 번 | 하 |
| F5 | 랜덤 게임 | 칸 하나로 현재 기종/즐겨찾기에서 무작위 | 하 |
| F6 | 플레이 기록 | 횟수·시간(날짜가 1970이라 시계 대신 가동 시간), "많이 한 게임" 순위 | 하~중 |
| F7 | 설정 화면 | MinosFront 안에서 `front.cfg` 항목(강제 종료 시간, 이어하기 기본, 테마 효과, 언어) 바꾸기 | 하 |
| F8 | 기종 단위 설정 | 화면 비율/화질을 기종 전체에 적용(게임 > 기종 > 전체 순) | 하 |
| F9 | 상태 저장 관리 | 저장 칸 목록(스크린샷 썸네일), 삭제 | 중 |
| F10 | 대기 화면 | 몇 분 입력이 없으면 미리보기 사진 슬라이드쇼(오락실 어트랙트 모드), 화면 보호 | 하 |
| F11 | 볼륨/밝기 | `amixer`로 볼륨, 밝기는 sysfs 확인 후 | 중 |
| F12 | 배경음악 | `music/bg.mp3`를 mplayer로 재생(끄기 옵션) | 하 |
| F13 | 오락실 테마 확장 | "CONTINUE? 9 8 7…" 종료 확인, 조이스틱 그림, 테마 2개 이상 선택 | 하 |
| F14 | 치트/오버레이 | RetroArch 치트 파일, 세로 게임 베젤 오버레이 | 중 |
| F15 | 외부 USB 패드 | USB HID 패드(커널에 HID 있음) 자동 인식 시험, 2P | 중 (기기 필요) |
| F16 | 에디터 연동 | PC 에디터가 `library.tsv`, `buttons.tsv`, `keymaps.tsv`, 영문 이름을 읽고 쓰기, 에디터 영어 UI (i18n 작업 #6) | 중 |
| F17 | 열리지 않는 아케이드 331개 | FBNeo 등 최신 코어를 RK3128용으로 빌드해 카드에 설치(코어 독립) | 상 |

## 3. 부팅 개입 계획
상세: `docs/BOOT_RESEARCH.md`. 요약: Pandory 실행파일의 메뉴 명령 문자열(`/usr/bin/gamemenu `, 오프셋 0xE9F2C)을 `sh /mnt/sdcard/m `으로 바꾼 복사본(`pandory.wrapper`)을 쓰고, `m`이 MinosFront → 순정 메뉴 순서로 실행.
1. 시험(기기): `wrapper.log` 생성 여부 → 문자열이 실제로 쓰이는지
2. 성공하면: 안전 모드(S2)와 크래시 보호(S1) 추가 → 기본값을 "켬"으로
3. 실패하면: 다른 문자열(`killall mplayer` 등 5개 system 문자열)을 같은 방식으로 시도하거나, `auto.sh` 방식을 다듬음
4. 판도라 재설치 후에도 `tools/patch_pandory.py`로 쉽게 다시 만들 수 있게 유지

## 4. 무선랜(RTL8188CU) 이식 계획
**기기 사실** (`kerninfo`): 커널 4.4.159 (2020-07, GCC 6.3 Linaro), `MODULES=y`, `MODVERSIONS` 꺼짐, `MODULE_FORCE_LOAD=y`, `NET/INET` 켜짐, `WIRELESS/CFG80211/RFKILL/USB_NET/PHYLIB/BT` 꺼짐, USB `EHCI/OHCI/HID/STORAGE/SERIAL` 켜짐, `/lib/modules`·`/lib/firmware` 없음(읽기 전용 루트), 루트 `udhcpc` 스크립트 있음(`/usr/share/udhcpc`). 동글: PC에서 확인한 `0BDA:8176` Realtek RTL8188CU.

### 단계
| 단계 | 내용 | 위험 | 산출물 |
|---|---|---|---|
| W0 | **USB 확인**(기기): 9848 → 포트가 호스트로 동작? 동글이 `lsusb`/dmesg에 보이는가, 전원 | 없음(읽기 전용) | `usb_probe.log` |
| W1 | 커널 소스 준비(PC): rockchip-linux/kernel `develop-4.4`와 kernel.org 4.4.159 둘 다 받아 기기 `config.gz`로 `olddefconfig` | 없음 | `/opt/wifi/` |
| W2 | **구조체 호환 검사**: 기기 설정 그대로와 "무선 켠 설정"에서 `struct net_device`, `sk_buff`, `usb_device` 등의 크기·오프셋이 같은지 작은 모듈로 확인. 다르면 영향이 없는 옵션만 켬(`WIRELESS_EXT` 끔) | 없음 | 설정 파일 |
| W3 | 모듈 빌드: `cfg80211.ko mac80211.ko rtlwifi.ko rtl_usb.ko rtl8192c-common.ko rtl8192cu.ko` (+ 필요한 `lib80211`/`rfkill` 의존 확인) | 없음 | `.ko` 6개 |
| W4 | 사용자 공간(PC에서 ARM 정적 빌드): `libnl-3` + `wpa_supplicant`(`nl80211`, 내장 TLS), 선택: `iw`, `dropbear`, `busybox`(ntpd/httpd) | 없음 | 실행파일 |
| W5 | 펌웨어: `rtlwifi/rtl8192cufw.bin`(linux-firmware)을 카드에, 기기에서 `echo /mnt/sdcard/pandory/wifi/fw > /sys/module/firmware_class/parameters/path` | 낮음 | 카드 파일 |
| W6 | `wifi_on.sh` 스크립트(`insmod -f` 순서, wpa_supplicant, `udhcpc -i wlan0`), 시험용 메뉴 스크립트 | 낮음(실패하면 재부팅) | 카드 스크립트 |
| W7 | 통합: MinosFront 설정 화면(F7)에 "와이파이 켜기/끄기, 상태 표시" | 낮음 | |
| W8 | 활용: 시간 동기화(`ntpd`), 파일 전송(`httpd`/`dropbear`)로 PC·폰에서 ROM·저장 파일 넣고 빼기, RetroArch 네트워크 기능 재빌드(`--enable-networking`, ssl 없이) | 낮음 | |

### 진행 상황 (2026-11-02 밤, PC에서만 진행, 기기/카드는 건드리지 않음)
| 단계 | 상태 | 결과 |
|---|---|---|
| W1 소스 | 완료 | kernel.org 4.4.159 (`D:\Backup\wifi\linux-4.4.159.tar.xz`), 기기 `config.gz`(`F:\kerninfo`)로 빌드 트리 2개(`o_base`, `o_wifi`) 준비. 네이티브 gcc가 없어서 커널 호스트 도구를 ARM 정적 빌드 + QEMU(binfmt)로 실행하는 방식으로 해결(`tools/wifi_binfmt.sh`, `wifi_prepare.sh`) |
| W2 구조체 호환 | 완료(1차) | 기기 설정 vs 무선 켠 설정에서 `net_device`(1344B), `sk_buff`(176B), `device`, `usb_device`, `module` 등 **156개 크기·오프셋이 모두 동일**. 단, 비교 대상은 같은 4.4.159 메인라인 소스이고 **제조사 커널(Rockchip 수정분)과의 차이는 기기에서만 확인 가능** → `insmod` 시험은 안전하지만 오동작 가능성은 남음 |
| W3 모듈 | 완료 | 6개 빌드 성공(8.5초). `vermagic=4.4.159 SMP mod_unload ARMv7 p2v8`, 의존: cfg80211 → mac80211 → rtlwifi → rtl_usb / rtl8192c-common → rtl8192cu. 정리본(디버그 제거, 총 약 0.8 MB): `D:\Backup\wifi\modules\` |
| W5 펌웨어 | 완료 | `rtl8192cufw*.bin` 4개 받음 (`D:\Backup\wifiw\`) |
| W4 사용자 공간 | **대기** | libnl-3 / wpa_supplicant 소스(`D:\Backup\wifi\src\`)를 빌드하려면 내려받은 소스의 `configure`를 실행해야 해서, 자동 실행이 차단됨 → 형님 허락 후 진행 (`tools/wifi_userland.sh` 준비됨) |
| W0 USB 확인 | 준비 | 카드의 9848(`28_USB_Probe.sh`), 동글을 꽂고 기기에서 실행 |

### 위험과 대비
* 잘못된 모듈 → `insmod` 실패 또는 커널 패닉(재부팅). **내부 플래시는 쓰지 않으므로 벽돌 위험 없음.**
* 구조체 불일치가 가장 큰 위험(W2에서 걸러냄). 조용한 오동작 방지를 위해 W2 통과 전에는 기기에서 시도하지 않음.
* USB 전원: 동글 소비 전류(약 100~200 mA)로 전압 강하 가능 → 배터리 상태 확인, 필요하면 외부 전원.
* 와이파이 암호는 카드의 `pandory/wifi/wpa.conf`에만 사용자가 직접 적음(저장소에 올리지 않음, `.gitignore`).
* 되돌리기: 스크립트를 안 돌리면 아무 변화 없음, 카드에서 `wifi/` 폴더만 지우면 끝.

## 5. 공개 저장소 운영 규칙
* GitHub `hguyswow/Minos-front`: `tools/make_public.py`로 만든 깨끗한 트리를 새 커밋으로 올림(작성자 hguyswow, 공동저자 문구 없음, 작업 지시서·내부 문서 제외).
* 올리기 전 자동 검사: AI 도구 이름이 포함된 텍스트 파일 경고.
* 금지: ROM/BIOS/펌웨어/순정 코어/미리보기 영상/판도라 실행파일, 와이파이 암호·개인 설정.
