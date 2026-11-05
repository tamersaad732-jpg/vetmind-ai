# -*- coding: utf-8 -*-
"""
VetMind AI International Scientific & Clinical References Database
10 Authoritative Arab & Regional References + 20 Global Tier-1 References
Direct file mappings to Desktop Library & static/reference_docs.
"""

import os
from generate_clean_references import ARAB_REFS as ARAB_REFERENCES, GLOBAL_REFS as GLOBAL_REFERENCES

ALL_REFERENCES = ARAB_REFERENCES + GLOBAL_REFERENCES

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, "static", "reference_docs")
USER_LIBRARY_DIR = r"c:\Users\tamersaad\Desktop\مكتبة المراجع البيطرية المعتمدة (VetMind Library)"

REF_FILES_MAP = {
    "arab_1": "01_دليلك_إلى_رعاية_الأبقار_والإنتاج_الحيواني.pdf",
    "arab_2": "02_علاج_أمراض_المجترات_هاشم.pdf",
    "arab_3": "03_الجراحة_البيطرية_العامة_مكتبة_الإسكندرية.pdf",
    "arab_4": "04_التخدير_في_الطب_البيطري.pdf",
    "arab_5": "05_موسوعة_الأدوية_البيطرية_عزيزة_محروس_وأمين_شتا.pdf",
    "arab_6": "06_الطفيليات_البيطرية.pdf",
    "arab_7": "07_الإبل_العربية_فسيولوجيا_ورعاية_وطب_الإبل_والهجن_الصانع.pdf",
    "arab_8": "08_صحة_ورعاية_الأغنام_فايز_وحامد_سماحة.pdf",
    "arab_9": "09_صحة_الحيوان_والطب_الوقائي_عبدالحميد.pdf",
    "arab_10": "10_تسمين_الدواجن_وصناعتها_د_ابراهيم_سلامة.pdf",
    "global_1": "01_Blood_Radostits_Veterinary_Medicine_10th_Ed.pdf",
    "global_2": "02_Veterinary_Anasthesia_and_Pain_Management_Secrets.pdf",
    "global_3": "03_Clinical_Veterinary_Advisor_Dog_And_Cat.pdf",
    "global_4": "04_Kuby_Immunology_Veterinary_Benchmark.pdf",
    "global_5": "05_Duncan_and_Prasse_Veterinary_Laboratory_Medicine.pdf",
    "global_6": "06_Fundamentals_of_Veterinary_Clinical_Pathology.pdf",
    "global_7": "07_Veterinary_Microbiology_Quinn.pdf",
    "global_8": "08_Textbook_of_Veterinary_General_Pathology.pdf",
    "global_9": "09_Veterinary_Microbiology_Comprehensive.pdf",
    "global_10": "10_Color_Atlas_of_the_Horse_Foot.pdf",
    "global_11": "11_Current_Therapy_in_Equine_Reproduction.pdf",
    "global_12": "12_Manual_of_Equine_Reproduction_3rd_Ed.pdf",
    "global_13": "13_Guide_to_Equine_Injection_and_Regional_Anesthesia.pdf",
    "global_14": "14_Equine_Dentistry_3rd_Edition.pdf",
    "global_15": "15_Equine_Dermatology_2nd_Edition.pdf",
    "global_16": "16_Handbook_of_Equine_Anaesthesia_2nd_Ed.pdf",
    "global_17": "17_Veterinary_Anaesthesia_Clinical_Manual.pdf",
    "global_18": "18_The_Equine_Manual_2nd_Edition.pdf",
    "global_19": "19_The_Equine_Veterinary_Nursing_Manual.pdf",
    "global_20": "20_Rooney_Guide_to_Dissection_of_the_Horse_7th_Ed.pdf",
}

def get_all_references():
    return ALL_REFERENCES

def get_arab_references():
    return ARAB_REFERENCES

def get_global_references():
    return GLOBAL_REFERENCES

def get_reference_by_id(ref_id: str):
    ref_id = (ref_id or "").lower().strip()
    for r in ALL_REFERENCES:
        if r["id"] == ref_id:
            return r
    return None

def get_reference_original_filename(ref_id: str) -> str:
    ref_id = (ref_id or "").lower().strip()
    return REF_FILES_MAP.get(ref_id, f"VetMind_Reference_{ref_id}.pdf")

def resolve_reference_pdf_path(ref_id: str):
    ref_id = (ref_id or "").lower().strip()
    orig_name = REF_FILES_MAP.get(ref_id, "")

    candidates = [
        os.path.join(DOCS_DIR, f"{ref_id}.pdf"),
        os.path.join(DOCS_DIR, orig_name) if orig_name else "",
        os.path.join(USER_LIBRARY_DIR, "01_المراجع_العربية_المعتمدة", orig_name) if orig_name else "",
        os.path.join(USER_LIBRARY_DIR, "02_المراجع_الدولية_المعتمدة_Tier1", orig_name) if orig_name else "",
        os.path.join(USER_LIBRARY_DIR, orig_name) if orig_name else "",
    ]
    for c in candidates:
        if c and os.path.exists(c) and os.path.getsize(c) > 1024:
            return c
    return None
