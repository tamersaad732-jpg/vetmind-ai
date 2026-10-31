@echo off
title VetMind AI - Enable Auto-Start on Windows Boot
color 0B
echo =================================================================
echo         VetMind AI Enterprise - Windows Auto-Start Installer
echo =================================================================
echo.
echo Installing background service shortcut into Windows Startup...
echo.

powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut([System.IO.Path]::Combine($env:APPDATA, 'Microsoft\Windows\Start Menu\Programs\Startup', 'VetMind_AI.lnk')); $Shortcut.TargetPath = 'wscript.exe'; $Shortcut.Arguments = '\"C:\Users\tamersaad\Desktop\vetmind-ai\run_background.vbs\"'; $Shortcut.WorkingDirectory = 'C:\Users\tamersaad\Desktop\vetmind-ai'; $Shortcut.Save()"

if %errorlevel% equ 0 (
    echo [SUCCESS] VetMind AI is now configured to start automatically with Windows!
    echo Every time you turn on your PC, VetMind AI will run silently in the background.
    echo.
    echo You can always access your platform at: http://127.0.0.1:8000
) else (
    echo [ERROR] Failed to create shortcut.
)

echo.
pause
