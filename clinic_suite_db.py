# -*- coding: utf-8 -*-
"""
Database Migration for Clinic Custom Logo, International Rx Prescriptions & Enterprise Suite
"""
import sqlite3
import random
import uuid
import json
from datetime import datetime

DB_PATH = r"C:\Users\tamersaad\Desktop\vetmind-ai\vetmind.db"

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# 1. Upgrade clinic_profiles table columns
c.execute("PRAGMA table_info(clinic_profiles)")
existing_cols = [r[1] for r in c.fetchall()]

new_cols = [
    ("logo_filename", "TEXT"),
    ("doctor_title", "TEXT"),
    ("license_no", "TEXT"),
    ("tagline", "TEXT"),
    ("header_color", "TEXT DEFAULT '#047857'"),
    ("watermark_enabled", "INTEGER DEFAULT 1")
]

for col_name, col_type in new_cols:
    if col_name not in existing_cols:
        try:
            c.execute(f"ALTER TABLE clinic_profiles ADD COLUMN {col_name} {col_type}")
            print(f"Added column {col_name} to clinic_profiles")
        except Exception as e:
            print(f"Error adding {col_name}: {e}")

# 2. Update default profile for user_id = 4 and user_id = 1
c.execute("""
UPDATE clinic_profiles 
SET 
    doctor_title = 'استشاري ورئيس قسم الطب البيطري والتشخيص السريري',
    license_no = 'EGY-VET-2026-98421',
    tagline = 'الرعاية البيطرية المتقدمة وفق المعايير العالمية Merck & WSAVA',
    header_color = '#047857'
WHERE user_id IN (1, 4)
""")

# 3. Create clinic_prescriptions table
c.execute("""
CREATE TABLE IF NOT EXISTS clinic_prescriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    serial_no TEXT UNIQUE NOT NULL,
    user_id INTEGER NOT NULL,
    animal_name TEXT NOT NULL,
    species TEXT NOT NULL,
    breed TEXT,
    age TEXT,
    weight REAL NOT NULL,
    owner_name TEXT NOT NULL,
    owner_phone TEXT,
    diagnosis TEXT NOT NULL,
    rx_items_json TEXT NOT NULL,
    withdrawal_warning TEXT,
    doctor_instructions TEXT,
    created_at TEXT NOT NULL
)
""")

# 4. Seed demo unique prescriptions if empty
c.execute("SELECT COUNT(*) FROM clinic_prescriptions")
if c.fetchone()[0] == 0:
    demo_prescriptions = [
        (
            f"VET-RX-2026-EG-{random.randint(10000, 99999)}-{uuid.uuid4().hex[:4].upper()}",
            4,
            "بقرة هولشتاين #204",
            "أبقار",
            "هولشتاين فريزيان",
            "3 سنوات",
            520.0,
            "الحاج محمود السعيد (مزرعة البركة)",
            "+201012345678",
            "التهاب رئوي بكتيري حاد (Bovine Respiratory Disease) مصحوب بارتفاع حرارة 40.5 مئوية وسعال رطب",
            json.dumps([
                {
                    "trade_name": "ماربوفلوكساسين 10% (Marbocyl Vet)",
                    "active": "ماربوفلوكساسين 100 ملجم/مل",
                    "function": "الوظيفة: علاج النزلات الرئوية الحادة والباستريلا",
                    "dose": "20.8 مل (1 مل / 25 كجم)",
                    "route": "حقناً في العضل العميق (IM)",
                    "freq": "مرة واحدة يومياً كل 24 ساعة",
                    "duration": "لمدة 3 أيام متتالية",
                    "notes": "تقسيم الجرعة على موضعين مختلفين في عضلات الرقبة"
                },
                {
                    "trade_name": "فلونيكسين ميغلومين 5% (Finadyne)",
                    "active": "فلونيكسين ميغلومين 50 ملجم/مل",
                    "function": "الوظيفة: خافض حرارة قوي ومسكن للالتهاب الرئوي",
                    "dose": "11.5 مل (2.2 ملجم / كجم)",
                    "route": "حقناً في الوريد البطيء (IV Slow)",
                    "freq": "مرة واحدة يومياً",
                    "duration": "لمدة يومين فقط",
                    "notes": "يمنع خلطه في نفس السرنجة مع أي مضاد حيوي"
                }
            ], ensure_ascii=False),
            "تحذير فترات الأمان الدوائي (Withdrawal Periods): اللحم 6 أيام من آخر جرعة، الحليب 36 ساعة.",
            "عزل الحيوان في حظيرة جافة جيدة التهوية بعيداً عن التيارات الهوائية مع توفير مياه شرب نظيفة ودريس حجازي عالي الجودة.",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ),
        (
            f"VET-RX-2026-EG-{random.randint(10000, 99999)}-{uuid.uuid4().hex[:4].upper()}",
            4,
            "جواد عربي أصيل (صقر الجزيرة)",
            "خيول",
            "عربي أصيل (كحيلان)",
            "5 سنوات",
            460.0,
            "الكابتن أحمد البدري (مربط الفرسان)",
            "+201198765432",
            "مغص تشنجي حاد بالأمعاء الدقيقة (Spasmodic Colic) مع انتفاخ خفيف بالأعور",
            json.dumps([
                {
                    "trade_name": "بسكوبان كومبوزيتم (Buscopan Compositum)",
                    "active": "هيوسين بوتيل بروميد 4 ملجم + ميتاميزول 500 ملجم/مل",
                    "function": "الوظيفة: إرخاء عضلات الأمعاء وتسكين نوبات المغص الحاد",
                    "dose": "25.0 مل بالوريد البطيء",
                    "route": "حقناً في الوريد الوداجي البطيء (IV)",
                    "freq": "جرعة إسعافية واحدة وتكرر بعد ساعتين إذا لزم",
                    "duration": "جرعة واحدة",
                    "notes": "مراقبة معدل ضربات القلب وحركة الأمعاء كل 30 دقيقة"
                }
            ], ensure_ascii=False),
            "خيول رياضية - لا يستهلك لحمها.",
            "منع العلف المركز لمدة 12 ساعة، المشي الهادئ لمدة 15 دقيقة، وإعطاء كميات صغيرة من الماء الفاتر فقط بعد توقف علامات الألم.",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    ]

    c.executemany("""
    INSERT INTO clinic_prescriptions (
        serial_no, user_id, animal_name, species, breed, age, weight,
        owner_name, owner_phone, diagnosis, rx_items_json, withdrawal_warning,
        doctor_instructions, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, demo_prescriptions)
    print("Seeded 2 demo professional prescriptions with unique serial numbers!")

conn.commit()
conn.close()
print("SUCCESS: Database upgraded for Clinic Logo, Branding, and Rx Prescriptions!")
