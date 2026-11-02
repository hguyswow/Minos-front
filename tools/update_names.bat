@echo off
rem Double-click after adding or removing games in E:\roms_pandory (card in the PC).
rem Optional: pass another drive letter, e.g. update_names.bat F:
set D=%1
if "%D%"=="" set D=E:
python "%~dp0pandora_names.py" %D%
echo.
echo Done. Eject the card, put it in the console and turn it on.
pause
