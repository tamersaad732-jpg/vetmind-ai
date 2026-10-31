# -*- coding: utf-8 -*-
import sqlite3
import os
from datetime import datetime, timedelta

BASE_DIR = r"C:\Users\tamersaad\Desktop\vetmind-ai"
DB_PATH = os.path.join(BASE_DIR, "vetmind.db")

def seed():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT count(*) FROM invoices")
    if c.fetchone()[0] == 0:
        now = datetime.now()
        invoices = [
            (4, "مزرعة الهدى للألبان", "كشف سريري وتشخيص فحص بالموجات فوق الصوتية (سونار) + علاج ضرع", 550.0, "paid", "فودافون كاش / إنستاباي", (now - timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S")),
            (4, "المهندس خالد العتيبي", "فحص تنفسي للصقور + جرعة تايلوزين ومنشط فيتامين", 350.0, "paid", "مدى (Mada)", (now - timedelta(hours=10)).strftime("%Y-%m-%d %H:%M:%S")),
            (4, "مزرعة البركة للإنتاج الحيواني", "تحصين وقائي جماعي ضد الحمى القلاعية + تجريع إيفرمكتين سوبر (30 رأس)", 2200.0, "paid", "نقداً (Cash)", (now - timedelta(days=1, hours=2)).strftime("%Y-%m-%d %H:%M:%S")),
            (4, "الكابتن شريف إبراهيم", "إسعاف طارئ لمغص الخيل وحقن فلونيكسين ميغلومين ورينجر لاكتات", 700.0, "paid", "بطاقة بنكية Visa", (now - timedelta(days=1, hours=15)).strftime("%Y-%m-%d %H:%M:%S")),
            (4, "الأستاذة سارة المنصور", "جراحة استئصال ورم سطحي + مضاد حيوي ومسكن", 850.0, "paid", "أبل باي (Apple Pay)", (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"))
        ]
        for inv in invoices:
            c.execute("""
            INSERT INTO invoices (user_id, client_name, service_name, amount, status, payment_method, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, inv)

    c.execute("SELECT count(*) FROM lab_tests")
    if c.fetchone()[0] == 0:
        now = datetime.now()
        lab_tests = [
            (4, "بقرة حلوب #108", "فحص ميكروسكوبي لطفيليات الدم (Blood Smear)", (now - timedelta(hours=5)).strftime("%Y-%m-%d"), "سلبية لطفيلي البابيزيا والثايليريا، مع وجود فقر دم معتدل وارتفاع كرات الدم البيضاء العدلة (Neutrophilia) المشيرة لالتهاب حاد.", "", (now - timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S")),
            (4, "شاهين أصيل (صقر)", "مسحة قصبية وفحص الميكوبلازما (PCR)", (now - timedelta(hours=12)).strftime("%Y-%m-%d"), "إيجابية لبكتيريا Mycoplasma gypis مع احتقان شديد بالأكياس الهوائية، التوصية بالاستمرار على كورس التايلوزين لمدة 5 أيام.", "", (now - timedelta(hours=12)).strftime("%Y-%m-%d %H:%M:%S")),
            (4, "كحيلان (فحل خيل عربي)", "فحص غازات الدم واللاكتات وكيمياء الدم (Blood Chem)", (now - timedelta(days=1)).strftime("%Y-%m-%d"), "اللاكتات 2.1 mmol/L (طبيعي بعد تخفيف المغص)، وظائف الكلى Urea و Creatinine ضمن المعدل الطبيعي.", "", (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")),
            (4, "عجل تسمين #45", "فحص عينة براز للديدان والكوكسيديا (Fecal Floatation)", (now - timedelta(days=2)).strftime("%Y-%m-%d"), "رصد بويضات ديدان الفاشيولا الكبدية وحويصلات الكوكسيديا (Eimeria bovis)، تم صرف إيفرمكتين سوبر وأمبراسين بلس.", "", (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"))
        ]
        for lb in lab_tests:
            c.execute("""
            INSERT INTO lab_tests (user_id, animal_name, test_type, test_date, result_summary, attachment_filename, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, lb)

    conn.commit()
    conn.close()
    print("Invoices and Lab Tests seeded cleanly!")

if __name__ == "__main__":
    seed()
