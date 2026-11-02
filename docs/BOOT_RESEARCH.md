# Boot chain research — where can MinosFront step in? (DX2 Plus + Pandory)

Findings from the extracted firmware and the Pandory executable on the card. Nothing here writes to the internal flash.

## 1. Boot chain
```
kernel -> /etc/init.d/S50ui -> /usr/bin/start_menu.sh -> emulotar (coin daemon) -> loader2 -> the card's loader files (roms/had.zip, hadc.zip, rade.zip:
        encrypted containers; Pandory's installer replaced them) -> pandory (ELF on the card, 1.26 MB) -> /usr/bin/gamemenu (stock menu)
```
* The stock root file system is read-only squashfs; `/tmp` is tmpfs; the card is mounted by udev at `/mnt/sdcard` (vfat, **no exec bit**, run scripts with `sh file`).
* `init`, `rcS`, `S*` scripts and the udev rules contain **no card hooks**. The only card-controlled code at boot is the Pandory executable (started by the encrypted loader).

## 2. What the Pandory executable does (strings + QEMU trace of a copy)
It is a supervisor loop. Every command is run through `system()` / `popen()` with a debug print `EXECUTING SHELL: ...`:
1. `killall mplayer`, starts menu music (`mplayer -slave ... /tmp/pandory_tracks`), prepares `/tmp/pandory_root`, `/tmp/udisk` (`mount -o bind`), `/tmp/overlays`.
2. `find /tmp -name "*.zip" -exec umount {} \;` ... then **`sh /mnt/sdcard/pandory/auto.sh >/dev/null 2>&1 &`** (this is the string we patched earlier; it was a useless `find ... -exec bash` command). It runs **before** the menu process exists.
3. `STARTING GAMEMENU` -> **`/usr/bin/gamemenu ` + args + ` 2>&1`** (popen; the output is parsed: `GAMEMENU CMD:` then `retroarch` / `fbalpha2012` / `xmame` / `shell`).
4. For a chosen game it builds `/tmp/retroarch.cfg` + `/tmp/pandory-options.cfg` from `pandory.xml` and runs RetroArch; for a script entry it runs `bash "<script>"` (`Running SHELL:`). Then the loop starts again at 1, so the hook in step 2 runs at **every** menu start.

## 3. Intervention points
| # | Point | Control | Verdict |
|---|---|---|---|
| A | `auto.sh` hook (step 2) | card file, already working | runs before the menu; can only start/stop things around it. Used for the name patch and the first autostart attempt (pause the menu with SIGSTOP, run MinosFront, kill the menu). Works in a mock; **did not work when tried on the device** (cause unknown; the menu names were also shifted at that time, so it was not a clean test). |
| B | **menu command string** (step 3), 20 bytes at file offset `0xE9F2C` | patch of a *copy* of the Pandory ELF | **best candidate**: replace `/usr/bin/gamemenu ` by `sh /mnt/sdcard/m `. The wrapper `m` runs MinosFront first and then `exec`s the stock menu **in the same process** — no SIGSTOP, no kill, no ghost key presses, and the output stream Pandory parses stays intact. When a stock game ends, Pandory restarts the menu and the wrapper runs again, so MinosFront comes back by itself. |
| C | script entries ("shell" core) | card files | already used (menu numbers 98xx); this is how MinosFront is started by hand today. |
| D | `pandory.xml` per-rom/-core options | card file | used for screen ratio/quality; no command hook found. |
| E | `/usr/bin/start_menu.sh`, `emulotar`, `loader2`, `had.zip` | firmware / encrypted | not reachable from the card without writing the internal flash (not done). |

## 4. Tools and the safe way to try B
* `reference/m` — the wrapper (tested with mocks: `tools/test_wrapper.sh ok|crash|off`): MinosFront only when `pandory/front/autostart` exists; two quick failures (< 6 s) switch it off; otherwise it just `exec`s the stock menu.
* `tools/patch_pandory.py F:` — writes `pandory/pandory.wrapper` (a patched **copy**; 18 bytes differ from the current file). The running `pandory` is not touched.
* To try (card in the PC): copy `m` to the card root, rename `pandory` -> `pandory.hook_only` and `pandory.wrapper` -> `pandory`. To undo: rename back. If the guess about the string is wrong nothing happens (the string is simply unused); `wrapper.log` on the card shows whether the wrapper ran.
* `tools/pandory_trace.sh` / `pandory_trace2.sh` run the Pandory ELF under QEMU on a copy with a system-call trace. **Careful:** the commands are executed on the host shell, and Pandory rewrites `pandory.xml` in its folder — always use the scripts (they work on a copy in `/tmp`), never run it inside the card folder.

## 5. Open questions (need the device)
* Does `popen("sh /mnt/sdcard/m ...")` really replace the menu start? (`wrapper.log` answers it.)
* Does Pandory accept the menu process running longer before the menu appears (MinosFront takes the screen first)? The wrapper is only a shell script until `exec`, so Pandory's pipe stays open the whole time.
