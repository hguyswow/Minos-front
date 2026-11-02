@echo off
chcp 65001 >nul
python run_editor.py
if errorlevel 1 pause

