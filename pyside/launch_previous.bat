@echo off
setlocal
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\run-previous.ps1"
if errorlevel 1 pause
endlocal
