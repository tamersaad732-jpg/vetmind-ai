$sh = New-Object -ComObject WScript.Shell
$desktopLnk = $sh.CreateShortcut("C:\Users\tamersaad\Desktop\VetMind AI.lnk")
Write-Output "Desktop Shortcut Target: $($desktopLnk.TargetPath)"
Write-Output "Desktop Shortcut Arguments: $($desktopLnk.Arguments)"

$startupLnk = $sh.CreateShortcut("$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\VetMindAI_AutoStart.lnk")
Write-Output "Startup Shortcut Target: $($startupLnk.TargetPath)"
Write-Output "Startup Shortcut Arguments: $($startupLnk.Arguments)"
