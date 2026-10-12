@echo off
if exist "%~dp0..\.venv\Scripts\semgrep.exe" (
    "%~dp0..\.venv\Scripts\semgrep.exe" %*
) else (
    semgrep %*
)
