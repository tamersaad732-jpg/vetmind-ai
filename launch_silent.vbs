Set WshShell = CreateObject("WScript.Shell")
' Run batch file completely hidden in background (0 = hide window, False = don't wait)
WshShell.Run "cmd.exe /c ""C:\Users\tamersaad\Desktop\vetmind-ai\run_server.bat""", 0, False
