# VetMind AI - Uninstaller Script for Local Background Daemon
# Permanently cleans up any local background services since the app is 24/7 on Vercel

Unregister-ScheduledTask -TaskName "VetMindAI_BackgroundService" -Confirm:$false -ErrorAction SilentlyContinue
Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "VetMindAI_SilentBackground" -ErrorAction SilentlyContinue
$vbs = Join-Path ([System.Environment]::GetFolderPath('Startup')) 'VetMind_SilentBackground.vbs'
if (Test-Path $vbs) { Remove-Item -Path $vbs -Force }
Get-Process | Where-Object { $_.ProcessName -like "*cloudflared*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Write-Host "VetMind AI local background service has been completely removed."
