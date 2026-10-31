with open(r'C:\Users\tamersaad\Desktop\vetmind-ai\app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if '/clinic' in l and ('@app.get' in l or '@app.post' in l):
        print(f'{i+1}: {l.strip()}')
