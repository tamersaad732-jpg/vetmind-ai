# -*- coding: utf-8 -*-
import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')

def test_query():
    conn = sqlite3.connect(r"C:\Users\tamersaad\Desktop\vetmind-ai\vetmind.db")
    c = conn.cursor()
    search_term = "%ضرع%"
    c.execute("""
    SELECT trade_name, category, indication FROM local_products 
    WHERE (country = 'مصر' OR country = 'دول أخرى')
    ORDER BY CASE WHEN indication LIKE ? OR trade_name LIKE ? THEN 0 ELSE 1 END, id ASC
    LIMIT 4
    """, (search_term, search_term))
    for r in c.fetchall():
        print(r[0], "-->", r[1])
    conn.close()

if __name__ == "__main__":
    test_query()
