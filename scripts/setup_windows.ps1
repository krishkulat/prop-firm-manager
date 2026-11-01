# Research PC / research VPS setup (run in PowerShell from the repo folder).
# Prereqs: Git for Windows, Python 3.11+ (tick "Add to PATH"), MetaTrader 5 with a DEMO account logged in.
$ErrorActionPreference = "Stop"

python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\pip install -r requirements.txt

if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host "Created .env - fill in TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID" }

# Install the PFM include + EA into the MT5 data folder (for Strategy Tester and demo)
$mt5 = Get-ChildItem "$env:APPDATA\MetaQuotes\Terminal" -Directory | Where-Object { Test-Path "$($_.FullName)\MQL5" } | Select-Object -First 1
if ($mt5) {
  New-Item -ItemType Directory -Force "$($mt5.FullName)\MQL5\Include\PFM" | Out-Null
  Copy-Item mql5\Include\PFM\RiskEngine.mqh "$($mt5.FullName)\MQL5\Include\PFM\" -Force
  Copy-Item mql5\Experts\*.mq5 "$($mt5.FullName)\MQL5\Experts\" -Force
  Write-Host "Copied EA files to $($mt5.FullName)\MQL5"
} else { Write-Host "MT5 data folder not found - open MT5 once, then re-run" }

.\.venv\Scripts\python -m pytest -q
Write-Host "`nNext: export data with  .\.venv\Scripts\python -m pfm.data export --symbol XAUUSD --timeframe M15 --start 2019-01-01"
Write-Host "Then start the worker with scripts\run_worker.bat"
