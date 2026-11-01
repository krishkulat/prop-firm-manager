@echo off
REM Starts the PFM job worker. Keep this window open (or add it to Task Scheduler "At log on").
cd /d %~dp0..
:loop
.venv\Scripts\python -m pfm.worker
echo Worker stopped, restarting in 30 seconds...
timeout /t 30 /nobreak >nul
goto loop
