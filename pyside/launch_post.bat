@echo off
setlocal
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\run-post.ps1"
if errorlevel 1 pause
endlocal
