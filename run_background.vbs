Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\tamersaad\Desktop\vetmind-ai"
WshShell.Run """C:\Users\tamersaad\Desktop\vetmind-ai\venv\Scripts\pythonw.exe"" ""C:\Users\tamersaad\Desktop\vetmind-ai\silent_daemon.py""", 0, False