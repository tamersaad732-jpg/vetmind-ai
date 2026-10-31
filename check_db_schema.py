import sqlite3

conn = sqlite3.connect(r'C:\Users\tamersaad\Desktop\vetmind-ai\vetmind.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in c.fetchall()]
print('Database tables:', tables)

for t in tables:
    c.execute(f'PRAGMA table_info({t})')
    cols = [r[1] for r in c.fetchall()]
    print(f'{t} ({len(cols)} cols):', cols[:8])

conn.close()
