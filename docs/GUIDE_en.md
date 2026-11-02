# MinosFront guide (English)

A launcher for the Pandora Saga DX2 Plus. All files live on the **SD card**.

## 1. Install
1. Copy the contents of `card/` to the root of the SD card. Keep your own `roms/` and `movies/`.
2. Put a RetroArch 1.22.2 ARM build at `pandory/ra/retroarch` (build it with `tools/build_retroarch.sh`).
3. In the stock menu open scripts → **MinosFront test** (`06_MinosFront`).
4. Optional preview pictures: on the PC run `python tools/build_previews.py F:` — it extracts three frames per game from `movies/*.avi` into `pandory/snap/`.

## 2. Screens and controls
| Screen | Controls |
|---|---|
| Systems | ←→ choose, A open, B or Start leave (to the original menu), **Coin** = Korean / English |
| Game list | ↑↓ move, ←→ 10 at a time, E/F 100 at a time, A play, B back, **C favorite**, **D next letter**, **Coin = game settings**, **Start = in-game hotkey help** |
| Game settings | screen ratio, quality, resume, button layout (←→ change, A save / edit) |

Special system cards: **Recent**, **Favorites**, **RetroArch Settings** (RetroArch menu without a game), **Button Test**, **Original Menu** (the stock Pandora screen).

## 3. In-game hotkeys (hold Start)
| Combo | Action |
|---|---|
| Start + Coin | quit game |
| Start + A / E | save / load state |
| Start + F | pause |
| Start + B | reset |
| Start + D | fast-forward on/off |
| Start + ↑ / ↓ | state slot |
| Start + → | slow motion (while held) |
| Start + ← | screenshot |
| **Coin + button** | toggle **turbo fire** for that button |
| Start alone for 4 s | force quit (when stuck in a menu) |

Device buttons: top row B C D, bottom row A E F, plus Start, Coin (= Select) and the D-pad.

## 4. Per-game button layouts
Game list → Coin → **Button layout** → A.
- Each of the six buttons can press **one or several game buttons at once**, e.g. Neo Geo "strong" = Button A + Button B.
- **D** cycles presets (stock / in order / Neo Geo style / 2 buttons up-down), **Coin** switches the scope (this game / all games of the same kind), **Start** saves, **B** cancels.
- Stored in `pandory/front/keymaps.tsv`. Save the "stock" preset to go back.
- Button names come from `pandory/buttons.tsv` (names reported by the cores; rebuild with `tools/desc_batch.sh`).
- How it works: keys are bound to RetroArch buttons directly; "one key, two buttons" binds spare buttons (L3 R3 L2 R2) to the same key and remaps them with a `.rmp` file written to `/tmp` (verified under QEMU: RetroArch loads the remap file).

## 5. Resume
When a game ends its state is saved automatically and loaded at the next start. Per game switch: Game settings → Resume. Global default: `resume=0/1` in `pandory/front/front.cfg`.

## 6. Files in `pandory/front/`
`front.cfg` (`quit_hold`, `resume`, `player`, `ratio`), `favorites.txt`, `recent.txt`, `last.cfg`, `game_settings.tsv`, `keymaps.tsv`, `lang.txt`. They are written only when something changes, to spare the card. `ra.cfg` is copied to `ra.cfg.good` and restored automatically if it ever looks broken.

## 7. MinosFront at start-up (experimental)
Switch scripts "MinosFront at start-up on / off" create / remove `pandory/front/autostart`. When the stock menu starts, `auto.sh` pauses it, runs MinosFront, and when MinosFront ends it kills the menu so Pandory starts a fresh one. Two quick failures in a row (< 6 s) switch the feature off by itself; if Pandory does not restart the menu within 12 s `auto.sh` starts `gamemenu` itself. Needs the Pandory hook (a patched string that runs `auto.sh`), see `docs/HACKING_NOTES_ko.md`.

## 8. Troubleshooting
| Problem | Check |
|---|---|
| Game does not start | `ra_run.log`, `front.log` on the card |
| Menu numbers / names shifted | run `python tools/pandora_names.py F:` after adding or removing scripts |
| Broken screen | copy an older `pandory/bin/minosfront.vN` over `minosfront` |
| Slow / noisy sound | check `pandory/ra/.asoundrc` and `audio_device="ra16hw"` in `ra.cfg` |

## 9. Testing without the device
WSL + QEMU user mode renders screens to images: `tools/front_test.sh` (key injection, screenshots), `tools/test_keys.sh` (layout generator), `tools/test_autostart.sh` (mock of the start-up hook). In test mode (`MINOS_KEYS`, `MINOS_SNAP`) nothing is written to the card and no game is started.
