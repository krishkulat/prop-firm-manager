# Run once in PowerShell from the repo folder. Needs no admin rights.
#   powershell -ExecutionPolicy Bypass -File scripts\install_autostart.ps1
# At every Windows sign-in, this starts the worker minimized and opens MT5 minimized. It also starts both now.
# Options: -NoMt5 (worker only)  -AllowNonDemoMt5 (open MT5 even if its last login is not a demo server)
#          -Uninstall (remove the sign-in shortcuts)
param([switch]$NoMt5, [switch]$AllowNonDemoMt5, [switch]$Uninstall)
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$startup = [Environment]::GetFolderPath("Startup")
$workerLnk = Join-Path $startup "PFM Worker.lnk"
$mt5Lnk = Join-Path $startup "PFM MT5.lnk"

function New-Shortcut($path, $target, $workDir) {
  $s = (New-Object -ComObject WScript.Shell).CreateShortcut($path)
  $s.TargetPath = $target
  $s.WorkingDirectory = $workDir
  $s.WindowStyle = 7          # minimized
  $s.Save()
}

# The last login MT5 used, read from its own config. A firm login here matters: MT5 reopens its saved charts,
# so an EA left on a chart with Algo Trading on would trade that account alongside the VPS bot.
function Get-Mt5LastServer($terminalPath) {
  $base = Join-Path $env:APPDATA "MetaQuotes\Terminal"
  $installDir = (Split-Path -Parent $terminalPath).TrimEnd("\")
  foreach ($d in Get-ChildItem $base -Directory -ErrorAction SilentlyContinue) {
    $origin = Join-Path $d.FullName "origin.txt"
    if ((Test-Path $origin) -and (Get-Content $origin -Raw).Trim().TrimEnd("\") -ieq $installDir) {
      $ini = Join-Path $d.FullName "config\common.ini"
      if (Test-Path $ini) {
        $line = Get-Content $ini | Where-Object { $_ -match '^\s*Server\s*=' } | Select-Object -First 1
        if ($line) { return ($line -split '=', 2)[1].Trim() }
      }
    }
  }
  return $null
}

if ($Uninstall) {
  Remove-Item $workerLnk, $mt5Lnk -ErrorAction SilentlyContinue
  Write-Host "Removed. Nothing starts at sign-in now. Close the 'PFM worker' window to stop the worker."
  exit 0
}

$bat = Join-Path $root "scripts\run_worker.bat"
if (-not (Test-Path (Join-Path $root ".venv\Scripts\python.exe"))) { throw ".venv not found. Run scripts\setup_windows.ps1 first." }
New-Shortcut $workerLnk $bat $root
Write-Host "OK  worker will start at sign-in"

$mt5Ok = $false
$terminal = $null
if (-not $NoMt5) {
  $envLine = Get-Content (Join-Path $root ".env") -ErrorAction SilentlyContinue | Where-Object { $_ -match '^\s*MT5_TERMINAL_PATH\s*=' } | Select-Object -First 1
  if ($envLine) { $terminal = ($envLine -split '=', 2)[1].Trim().Trim('"') }
  if (-not $terminal -or -not (Test-Path $terminal)) {
    Write-Host "SKIP MT5: MT5_TERMINAL_PATH in .env is missing or wrong"
  } else {
    $server = Get-Mt5LastServer $terminal
    if ($AllowNonDemoMt5 -or ($server -match 'demo')) {
      New-Shortcut $mt5Lnk $terminal (Split-Path -Parent $terminal)
      $mt5Ok = $true
      Write-Host "OK  MT5 will open at sign-in (last server: $server)"
    } else {
      Remove-Item $mt5Lnk -ErrorAction SilentlyContinue
      Write-Host "SKIP MT5: its last login is on '$server', not a demo server."
      Write-Host "     Log MT5 in to your demo account, close it, and run this script again."
      Write-Host "     If that login has no EA on any chart, add -AllowNonDemoMt5 instead."
    }
  }
}

Start-Process -FilePath $bat -WorkingDirectory $root -WindowStyle Minimized
Write-Host "OK  worker started now (minimized as 'PFM worker'; log: logs\worker.log)"
if ($mt5Ok) { Start-Process -FilePath $terminal -WindowStyle Minimized; Write-Host "OK  MT5 started now" }
