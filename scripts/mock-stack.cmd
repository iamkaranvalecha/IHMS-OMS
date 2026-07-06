@echo off
REM Wrapper for mock-stack.ps1 (Windows cmd.exe / double-click)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0mock-stack.ps1" %*
exit /b %ERRORLEVEL%
