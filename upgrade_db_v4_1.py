# -*- coding: utf-8 -*-
import sqlite3
import os
from datetime import datetime, timedelta

BASE_DIR = r"C:\Users\tamersaad\Desktop\vetmind-ai"
DB_PATH = os.path.join(BASE_DIR, "vetmind.db")

def upgrade():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Add columns to users table if missing
    c.execute("PRAGMA table_info(users)")
    cols = [r[1] for r in c.fetchall()]

    new_cols = [
        ("phone", "TEXT DEFAULT '+201000000000'"),
        ("avatar_image", "TEXT DEFAULT ''"),
        ("is_premium", "INTEGER DEFAULT 0"),
        ("is_email_verified", "INTEGER DEFAULT 1"),  # existing users verified by default
        ("otp_code", "TEXT DEFAULT ''"),
        ("otp_expiry", "TEXT DEFAULT ''"),
        ("last_active_at", "TEXT")
    ]

    for col_name, col_def in new_cols:
        if col_name not in cols:
            c.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}")
            print(f"Added column {col_name} to users")

    # Set director and admin as premium and verified
    c.execute("UPDATE users SET is_premium = 1, is_email_verified = 1, last_active_at = ? WHERE is_admin = 1", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
    c.execute("UPDATE users SET last_active_at = ? WHERE last_active_at IS NULL", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))

    # Create client_operations table for Time Demand analytics
    c.execute("""
    CREATE TABLE IF NOT EXISTS client_operations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        client_name TEXT NOT NULL,
        client_phone TEXT,
        client_avatar TEXT,
        animal_name TEXT NOT NULL,
        species TEXT NOT NULL,
        operation_type TEXT NOT NULL,
        operation_details TEXT,
        fee_collected REAL DEFAULT 0,
        performed_at TEXT NOT NULL,
        status TEXT DEFAULT 'completed'
    )
    """)

    # Create support_tickets table
    c.execute("""
    CREATE TABLE IF NOT EXISTS support_tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        doctor_name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT,
        country TEXT,
        subject TEXT NOT NULL,
        message TEXT NOT NULL,
        priority TEXT DEFAULT 'medium',
        status TEXT DEFAULT 'open',
        created_at TEXT NOT NULL
    )
    """)

    # Seed demo operations in the last 3 days if empty
    c.execute("SELECT count(*) FROM client_operations")
    if c.fetchone()[0] == 0:
        now = datetime.now()
        demo_ops = [
            (4, "مزرعة الهدى والتقوى", "01011223344", "avatar_client1.png", "بقرة حلوب #108", "أبقار", "فحص بالموجات فوق الصوتية (سونار تناسلي)", "تأكيد حمل في الشهر الثالث ومتابعة صحة الجنين", 450.0, (now - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")),
            (4, "المهندس خالد العتيبي", "0502233445", "avatar_client2.png", "شاهين أصيل (صقر)", "طيور", "فحص تنظيري للأكياس الهوائية وصرف مضاد", "تشخيص عدوى الميكوبلازما وإعطاء جرعة التايلوزين الأولى", 300.0, (now - timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")),
            (4, "مزرعة الوادي الجديد للأغنام", "01233445566", "avatar_client3.png", "قطيع نعاج برقي (15 رأس)", "أغنام وماعز", "تحصين وقائي وتجريع طفيليات", "إعطاء لقاح التسمم المعوي وإيفرمكتين سوبر لكامل القطيع", 1200.0, (now - timedelta(days=1, hours=4)).strftime("%Y-%m-%d %H:%M:%S")),
            (4, "الكابتن شريف إبراهيم", "01144556677", "avatar_client4.png", "كحيلان (حصان عربي)", "خيول", "علاج مغص تشنجي حاد وإعطاء مسكنات", "حقن وريدي لفلونيكسين ميغلومين ورينجر لاكتات مع تخفيف الألم", 650.0, (now - timedelta(days=1, hours=14)).strftime("%Y-%m-%d %H:%M:%S")),
            (4, "الأستاذة سارة المنصور", "0556677889", "avatar_client5.png", "بيلا (قطة شيرازي)", "قطط", "جراحة استئصال ورم سطحي حميد", "تخدير عام آمن واستئصال كيس دهني مع خياطة تجميلية", 800.0, (now - timedelta(days=2, hours=6)).strftime("%Y-%m-%d %H:%M:%S")),
            (4, "مزرعة التوفيق للألبان", "01099887766", "avatar_client6.png", "عجول تسمين (5 رؤوس)", "أبقار", "علاج متلازمة الالتهاب الرئوي الحاد", "حقن أوكسيتتراسيكلين طويل المفعول مع خافض حرارة", 950.0, (now - timedelta(days=2, hours=18)).strftime("%Y-%m-%d %H:%M:%S")),
        ]
        for op in demo_ops:
            c.execute("""
            INSERT INTO client_operations 
            (user_id, client_name, client_phone, client_avatar, animal_name, species, operation_type, operation_details, fee_collected, performed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, op)

    conn.commit()
    conn.close()
    print("Database schema successfully upgraded to v4.1 with 2FA, Premium, Support, and Time Demand!")

if __name__ == "__main__":
    upgrade()
