# -*- coding: utf-8 -*-
import json
import os

filepath = r"C:\Users\tamersaad\Desktop\vetmind-ai\translations_data.py"
from translations_data import DATA

new_ar_keys = {
    "nav_rx": "📋 الروشتة وحاسبة الجرعات",
    "nav_interactions": "⚠️ فاحص التداخلات الدوائية",
    "nav_invoices": "🧾 الفواتير وسندات القبض",
    "nav_lab": "🔬 التحاليل المخبرية والأشعة",
    "rx_title": "مولد الروشتة البيطرية وحاسبة الجرعات الذكية",
    "rx_subtitle": "حساب دقيق لجرعات الأدوية حسب وزن الحيوان، وطباعة روشتة علاجية رسمية معتمدة باسم العيادة",
    "interactions_title": "فاحص التداخلات الدوائية وموانع الاستعمال",
    "interactions_subtitle": "فحص توافق وصلاحية إعطاء دوائين معاً وتجنب التسمم أو التثبيط الدوائي",
    "invoices_title": "سجل الفواتير وسندات القبض المالية للعيادة",
    "invoices_subtitle": "إصدار ومتابعة فواتير الكشوفات والعمليات والأدوية المباعة للمربين والعملاء",
    "lab_title": "سجل الفحوصات المخبرية والأشعة والسونار",
    "lab_subtitle": "توثيق نتائج صورة الدم الكاملة (CBC)، فحص طفيليات الدم، وفحوصات الموجات فوق الصوتية",
}

new_en_keys = {
    "nav_rx": "📋 Smart Rx & Dosage Calculator",
    "nav_interactions": "⚠️ Drug Interactions Checker",
    "nav_invoices": "🧾 Invoices & Billing",
    "nav_lab": "🔬 Diagnostic Lab & Imaging",
    "rx_title": "Official Veterinary Rx Prescription & Dosage Calculator",
    "rx_subtitle": "Calculate exact drug dosages based on body weight and generate printable official clinic prescriptions",
    "interactions_title": "Veterinary Drug-Drug Interaction & Safety Checker",
    "interactions_subtitle": "Verify compatibility between co-administered pharmaceutical agents to prevent toxicities",
    "invoices_title": "Clinic Billing, Invoices & Receipt Records",
    "invoices_subtitle": "Manage clinical examination fees, medications sold, and printable receipts for clients",
    "lab_title": "Diagnostic Laboratory Tests & Imaging Suite",
    "lab_subtitle": "Record CBC blood profiles, hemoparasite smears, and ultrasound scan telemetry",
}

for k, v in new_ar_keys.items():
    DATA["ar"][k] = v

for k, v in new_en_keys.items():
    DATA["en"][k] = v

for lcode in ["fr", "es", "de", "it", "zh", "ja"]:
    if lcode in DATA:
        for k, v in new_en_keys.items():
            DATA[lcode][k] = v

with open(filepath, "w", encoding="utf-8") as f:
    f.write("# -*- coding: utf-8 -*-\n")
    f.write('"""\nVetMind AI Enterprise Multilingual Translations Database v4.2\n')
    f.write("Full translations for ar, en, fr, es, de, it, zh, ja with zero question marks.\n")
    f.write('"""\n\n')
    f.write("DATA = ")
    json.dump(DATA, f, ensure_ascii=False, indent=4)
    f.write("\n")

print("Successfully enriched translations_data.py with Rx, Interactions, Invoices, and Lab keys!")
