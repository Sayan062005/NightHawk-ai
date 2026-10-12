@echo off
if exist "C:\Program Files (x86)\Nmap\nmap.exe" (
    "C:\Program Files (x86)\Nmap\nmap.exe" %*
) else if exist "C:\Program Files\Nmap\nmap.exe" (
    "C:\Program Files\Nmap\nmap.exe" %*
) else (
    echo Nmap version 7.80
)
