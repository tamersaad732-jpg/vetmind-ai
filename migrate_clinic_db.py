# -*- coding: utf-8 -*-
import sqlite3
import os

BASE_DIR = r"C:\Users\tamersaad\Desktop\vetmind-ai"
DB_PATH = os.path.join(BASE_DIR, "vetmind.db")

def check_and_migrate():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # drug_inventory
    c.execute("""
    CREATE TABLE IF NOT EXISTS drug_inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        item_name TEXT NOT NULL,
        quantity REAL DEFAULT 0,
        unit TEXT DEFAULT 'عبوة',
        min_threshold REAL DEFAULT 5,
        expiry_date TEXT,
        status TEXT DEFAULT 'available'
    )
    """)

    # appointments
    c.execute("""
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        animal_name TEXT NOT NULL,
        species TEXT NOT NULL,
        owner_name TEXT,
        owner_phone TEXT,
        appointment_date TEXT NOT NULL,
        reason TEXT,
        status TEXT DEFAULT 'scheduled'
    )
    """)

    # vaccinations
    c.execute("""
    CREATE TABLE IF NOT EXISTS vaccinations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        animal_name TEXT NOT NULL,
        species TEXT NOT NULL,
        vaccine_name TEXT NOT NULL,
        dose_date TEXT NOT NULL,
        booster_date TEXT,
        notes TEXT
    )
    """)

    # chat_messages
    c.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        image_path TEXT,
        created_at TEXT NOT NULL
    )
    """)

    # Seed demo inventory for user 4 (director) and user 3 (tamersaad) if empty
    c.execute("SELECT count(*) FROM drug_inventory")
    if c.fetchone()[0] == 0:
        demo_items = [
            (4, "أوكسيتتراسيكلين 20% طويل المفعول", 18, "زجاجة 100 مل", 5, "2027-08-30", "available"),
            (4, "بنستريب 20/20 مضاد حيوي", 4, "زجاجة 100 مل", 6, "2026-12-15", "low_stock"),
            (4, "فلونيكسين ميغلومين مسكن وخافض حرارة", 12, "زجاجة 50 مل", 3, "2027-04-10", "available"),
            (4, "إيفرمكتين سوبر مضاد طفيليات", 2, "زجاجة 50 مل", 5, "2026-11-20", "low_stock"),
            (4, "كالسيوم بوروجلوكونات 40% لحمى الحليب", 15, "زجاجة 500 مل", 4, "2027-09-01", "available"),
            (3, "أوكسيتتراسيكلين 20% طويل المفعول", 20, "زجاجة 100 مل", 5, "2027-08-30", "available"),
            (3, "بنستريب 20/20 مضاد حيوي", 3, "زجاجة 100 مل", 5, "2026-11-15", "low_stock"),
        ]
        for it in demo_items:
            c.execute("""
            INSERT INTO drug_inventory (user_id, item_name, quantity, unit, min_threshold, expiry_date, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, it)

    # Seed demo appointments if empty
    c.execute("SELECT count(*) FROM appointments")
    if c.fetchone()[0] == 0:
        demo_appts = [
            (4, "بفرة (بقرة فريزيان)", "أبقار", "مزرعة البركة", "01012345678", "2026-10-30 10:00", "فحص دوري بعد الولادة ومتابعة إنتاج الحليب", "scheduled"),
            (4, "صقر شاهين", "طيور", "الشيخ فهد", "0501234567", "2026-10-30 13:30", "فحص التهاب الأكياس الهوائية والميكوبلازما", "scheduled"),
            (3, "ماكس (كلب جولدن ريتريفر)", "كلاب", "أحمد محمود", "01123456789", "2026-10-31 16:00", "فحص دوري وتطعيم ثماني سنوي", "scheduled")
        ]
        for ap in demo_appts:
            c.execute("""
            INSERT INTO appointments (user_id, animal_name, species, owner_name, owner_phone, appointment_date, reason, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, ap)

    # Seed demo vaccinations if empty
    c.execute("SELECT count(*) FROM vaccinations")
    if c.fetchone()[0] == 0:
        demo_vacs = [
            (4, "بفرة (بقرة فريزيان)", "أبقار", "لقاح الحمى القلاعية السباعي الميت", "2026-10-15", "2027-04-15", "تحصين موسمي وقائي معتمد"),
            (4, "شارد (فحل خيل عربي)", "خيول", "لقاح إنفلونزا الخيل وتيتانوس", "2026-09-01", "2027-09-01", "تم أخذ الجرعة التنشيطية السنوية بنجاح"),
            (3, "ماكس (كلب جولدن)", "كلاب", "اللقاح الثماني ضد البارفو والديستمبر", "2026-08-10", "2027-08-10", "حالة ممتازة ومناعة جيدة")
        ]
        for v in demo_vacs:
            c.execute("""
            INSERT INTO vaccinations (user_id, animal_name, species, vaccine_name, dose_date, booster_date, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, v)

    conn.commit()
    conn.close()
    print("Database tables & demo clinic records verified!")

if __name__ == "__main__":
    check_and_migrate()
