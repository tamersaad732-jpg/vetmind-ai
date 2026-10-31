# -*- coding: utf-8 -*-
import sqlite3
import os

BASE_DIR = r"C:\Users\tamersaad\Desktop\vetmind-ai"
DB_PATH = os.path.join(BASE_DIR, "vetmind.db")

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

def add_col_if_missing(table, col, defn):
    c.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in c.fetchall()]
    if col not in cols:
        c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {defn}")
        print(f"Added {col} to {table}")

add_col_if_missing("drug_inventory", "user_id", "INTEGER DEFAULT 0")
add_col_if_missing("drug_inventory", "min_threshold", "INTEGER DEFAULT 10")
add_col_if_missing("appointments", "owner_name", "TEXT")
add_col_if_missing("appointments", "owner_phone", "TEXT")
add_col_if_missing("vaccinations", "species", "TEXT DEFAULT 'أبقار'")

# Seed some appointments if 0
c.execute("SELECT count(*) FROM appointments")
if c.fetchone()[0] == 0:
    c.execute("""
    INSERT INTO appointments (user_id, pet_name, species, appointment_date, appointment_time, reason, status, owner_name, owner_phone, created_at)
    VALUES (4, 'بفرة (بقرة فريزيان)', 'أبقار', '2026-10-30', '10:00', 'فحص دوري بعد الولادة ومتابعة إنتاج الحليب', 'scheduled', 'مزرعة الخير والبركة', '01012345678', '2026-10-29 12:00:00')
    """)
    c.execute("""
    INSERT INTO appointments (user_id, pet_name, species, appointment_date, appointment_time, reason, status, owner_name, owner_phone, created_at)
    VALUES (4, 'صقر شاهين', 'طيور', '2026-10-31', '14:00', 'فحص التهاب الأكياس الهوائية والميكوبلازما', 'scheduled', 'الشيخ فهد العتيبي', '0501234567', '2026-10-29 12:00:00')
    """)

# Seed some vaccinations if 0
c.execute("SELECT count(*) FROM vaccinations")
if c.fetchone()[0] == 0:
    c.execute("""
    INSERT INTO vaccinations (user_id, animal_name, species, vaccine_name, dose_number, administered_date, next_due_date, notes, created_at)
    VALUES (4, 'بفرة (بقرة فريزيان)', 'أبقار', 'لقاح الحمى القلاعية السباعي الميت', 1, '2026-10-15', '2027-04-15', 'تحصين موسمي وقائي معتمد', '2026-10-29 12:00:00')
    """)
    c.execute("""
    INSERT INTO vaccinations (user_id, animal_name, species, vaccine_name, dose_number, administered_date, next_due_date, notes, created_at)
    VALUES (4, 'شارد (فحل خيل عربي)', 'خيول', 'لقاح إنفلونزا الخيل وتيتانوس', 2, '2026-09-01', '2027-09-01', 'تم إعطاء الجرعة التنشيطية السنوية بنجاح', '2026-10-29 12:00:00')
    """)

conn.commit()
conn.close()
print("Migration completed smoothly!")
