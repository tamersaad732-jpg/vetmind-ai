$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest
$action = New-ScheduledTaskAction -Execute "netsh" -Argument "advfirewall firewall add rule name=`"VetMind_Port8000`" dir=in action=allow protocol=TCP localport=8000"
Register-ScheduledTask -TaskName "AddFirewallRuleVetMind" -Action $action -Principal $principal -Force | Out-Null
Start-Sleep -Seconds 1
schtasks /run /tn "AddFirewallRuleVetMind" | Out-Null
Start-Sleep -Seconds 3
Unregister-ScheduledTask -TaskName "AddFirewallRuleVetMind" -Confirm:$false | Out-Null
Write-Output "Firewall rule registration executed."
