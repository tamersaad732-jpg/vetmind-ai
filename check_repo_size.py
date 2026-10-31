# -*- coding: utf-8 -*-
import subprocess
import os

git_exe = r"C:\Users\tamersaad\Desktop\vetmind-ai\bin\git\cmd\git.exe"
cwd = r"C:\Users\tamersaad\Desktop\vetmind-ai"

# Add all
subprocess.run([git_exe, "add", "."], cwd=cwd)

# Check tracked files sizes
res = subprocess.run([git_exe, "ls-files"], cwd=cwd, capture_output=True, text=True)
files = res.stdout.strip().split("\n")

large_files = []
total_bytes = 0
for f in files:
    f_path = os.path.join(cwd, f)
    if os.path.exists(f_path):
        sz = os.path.getsize(f_path)
        total_bytes += sz
        if sz > 25 * 1024 * 1024: # > 25 MB
            large_files.append((f, sz / 1024 / 1024))

print(f"Total tracked files: {len(files)}, Total size: {total_bytes / 1024 / 1024:.2f} MB")
if large_files:
    print("WARNING: Large files tracked:", large_files)
else:
    print("SUCCESS: Zero large files! Completely safe for GitHub and Render!")
