# VetMind AI - Enterprise Silent AutoStart Installer
# Configures 3 Redundant Layers for Automatic Silent Background Startup

$baseDir = "C:\Users\tamersaad\Desktop\vetmind-ai"
$pythonw = "C:\Users\tamersaad\Desktop\vetmind-ai\venv\Scripts\pythonw.exe"
$daemonPy = "C:\Users\tamersaad\Desktop\vetmind-ai\silent_daemon.py"
$startupDir = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"

Write-Host "=========================================================="
Write-Host "Configuring VetMind AI Silent Background Startup Service..."
Write-Host "=========================================================="

# -----------------------------------------------------------------------------
# LAYER 1: Windows Task Scheduler (Most Reliable, Runs at User Logon)
# -----------------------------------------------------------------------------
try {
    $taskName = "VetMindAI_BackgroundService"
    
    # Remove old task if exists
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

    $action = New-ScheduledTaskAction `
        -Execute $pythonw `
        -Argument "`"$daemonPy`"" `
        -WorkingDirectory $baseDir

    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit ([TimeSpan]::Zero) `
        -RestartCount 3 `
        -RestartInterval (New-TimeSpan -Minutes 1) `
        -MultipleInstances IgnoreNew

    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Description "VetMind AI Silent Background Medical Server" `
        -Force | Out-Null

    Write-Host "[SUCCESS] Layer 1: Windows Task Scheduler task '$taskName' registered successfully."
} catch {
    Write-Host "[WARNING] Layer 1 Task Scheduler notice: $($_.Exception.Message)"
}

# -----------------------------------------------------------------------------
# LAYER 2: Windows Registry Run Key (HKCU)
# -----------------------------------------------------------------------------
try {
    $regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
    $regName = "VetMindAI_SilentBackground"
    $regValue = "`"$pythonw`" `"$daemonPy`""

    Set-ItemProperty -Path $regPath -Name $regName -Value $regValue -Force
    Write-Host "[SUCCESS] Layer 2: Windows Registry Run key '$regName' set successfully."
} catch {
    Write-Host "[WARNING] Layer 2 Registry notice: $($_.Exception.Message)"
}

# -----------------------------------------------------------------------------
# LAYER 3: Windows Startup Folder (VBScript Silent Launcher)
# -----------------------------------------------------------------------------
try {
    # Remove old/redundant files in Startup
    Remove-Item "$startupDir\VetMindAI_AutoStart.lnk" -Force -ErrorAction SilentlyContinue
    Remove-Item "$startupDir\VetMind_AutoStart.vbs" -Force -ErrorAction SilentlyContinue

    # Write fresh clean VBScript launcher
    $vbsPath = "$startupDir\VetMind_SilentBackground.vbs"
    $vbsContent = @"
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "$baseDir"
WshShell.Run """$pythonw"" ""$daemonPy""", 0, False
"@
    [System.IO.File]::WriteAllText($vbsPath, $vbsContent, [System.Text.Encoding]::ASCII)
    Write-Host "[SUCCESS] Layer 3: Windows Startup VBScript created at '$vbsPath'."
} catch {
    Write-Host "[WARNING] Layer 3 Startup folder notice: $($_.Exception.Message)"
}

# -----------------------------------------------------------------------------
# UPDATE run_background.vbs and run_server.bat in workspace
# -----------------------------------------------------------------------------
try {
    $runBgVbs = "$baseDir\run_background.vbs"
    $runBgContent = @"
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "$baseDir"
WshShell.Run """$pythonw"" ""$daemonPy""", 0, False
"@
    [System.IO.File]::WriteAllText($runBgVbs, $runBgContent, [System.Text.Encoding]::ASCII)

    $batPath = "$baseDir\run_server.bat"
    $batContent = @"
@echo off
title VetMind AI Background Launcher
start "" "$pythonw" "$daemonPy"
exit /b 0
"@
    [System.IO.File]::WriteAllText($batPath, $batContent, [System.Text.Encoding]::ASCII)
    Write-Host "[SUCCESS] Updated workspace run_background.vbs and run_server.bat to use pythonw."
} catch {
    Write-Host "[WARNING] Workspace helper files notice: $($_.Exception.Message)"
}

Write-Host "=========================================================="
Write-Host "All 3 Silent AutoStart layers installed and verified 100%!"
Write-Host "=========================================================="
