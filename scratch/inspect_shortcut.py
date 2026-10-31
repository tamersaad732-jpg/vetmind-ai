import sys
try:
    import win32com.client
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortcut(r"C:\Users\tamersaad\Desktop\VetMind AI.lnk")
    print("TargetPath:", shortcut.TargetPath)
    print("Arguments:", shortcut.Arguments)
    print("WindowStyle:", shortcut.WindowStyle)
    print("WorkingDirectory:", shortcut.WorkingDirectory)
except Exception as e:
    print("Error:", e)
