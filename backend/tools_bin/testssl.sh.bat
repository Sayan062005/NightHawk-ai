@echo off
set PYTHON_BIN="%~dp0..\.venv\Scripts\python.exe"
if exist %PYTHON_BIN% (
    %PYTHON_BIN% "%~dp0testssl_shim.py" %*
) else (
    python "%~dp0testssl_shim.py" %*
)
