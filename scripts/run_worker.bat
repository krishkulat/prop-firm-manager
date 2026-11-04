@echo off
REM Starts the PFM job worker and restarts it if it stops. Output goes to logs\worker.log.
REM scripts\install_autostart.ps1 runs this at every Windows sign-in, minimized. Only one worker can run at a time.
title PFM worker
cd /d %~dp0..
if not exist logs mkdir logs
:loop
.venv\Scripts\python -m pfm.worker >> logs\worker.log 2>&1
echo Worker stopped, restarting in 30 seconds...
timeout /t 30 /nobreak >nul
goto loop
