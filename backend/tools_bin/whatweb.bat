@echo off
set PYTHON_BIN="%~dp0..\.venv\Scripts\python.exe"
if exist %PYTHON_BIN% (
    %PYTHON_BIN% "%~dp0whatweb_shim.py" %*
) else (
    python "%~dp0whatweb_shim.py" %*
)
