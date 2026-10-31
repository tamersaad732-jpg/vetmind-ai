@echo off
title VetMind AI - Disable Auto-Start
color 0C
echo =================================================================
echo         VetMind AI Enterprise - Remove Auto-Start Shortcut
echo =================================================================
echo.

powershell -Command "$p = [System.IO.Path]::Combine($env:APPDATA, 'Microsoft\Windows\Start Menu\Programs\Startup', 'VetMind_AI.lnk'); if (Test-Path $p) { Remove-Item $p -Force; Write-Host '[SUCCESS] Auto-start shortcut removed successfully.' } else { Write-Host '[INFO] No auto-start shortcut found.' }"

echo.
pause
