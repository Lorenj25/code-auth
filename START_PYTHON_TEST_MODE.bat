@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title CodeAuthentic - Experimental Python CodeBERT

echo.
echo ==========================================================
echo      CodeAuthentic - LOCAL PYTHON TEST MODE
echo ==========================================================
echo Python reads ml\candidates\python.joblib only in this mode.
echo Java and C remain unchanged (and untrained until ready).
echo Results are for research/testing, NOT proof of authorship.
echo Do not use this mode for a real examination.
echo.

if not exist "ml\candidates\python.joblib" goto :missing_candidate
if not exist "ml\candidates\python.json" goto :missing_candidate
if not exist "START_SYSTEM.bat" goto :missing_launcher

rem This environment variable is inherited by the FastAPI window launched
rem by START_SYSTEM.bat, not written to .env or your Windows settings.
set "CODEAUTHENTIC_PYTHON_TEST_MODE=1"
call "%~dp0START_SYSTEM.bat"
exit /b %errorlevel%

:missing_candidate
echo [ERROR] Missing Python classifier candidate or report.
echo Copy the trusted ml\candidates\python.joblib and python.json first.
pause
exit /b 1
:missing_launcher
echo [ERROR] START_SYSTEM.bat was not found beside this script.
pause
exit /b 1
