@echo off
cd /d "%~dp0"
title NightHawk AI - Desktop GUI
start "" powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0nighthawk_gui.ps1"
exit /b 0
