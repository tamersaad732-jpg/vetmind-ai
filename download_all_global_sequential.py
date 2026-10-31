# -*- coding: utf-8 -*-
import os
import sys
import time
import ssl
import shutil
import zipfile
import urllib.request

sys.stdout.reconfigure(encoding='utf-8')
ctx = ssl._create_unverified_context()

BASE_DIR = r"C:\Users\tamersaad\Desktop\vetmind-ai"
DOCS_DIR = os.path.join(BASE_DIR, "static", "reference_docs")
DOWNLOADS_DIR = os.path.join(BASE_DIR, "static", "downloads")
DESKTOP_DIR = r"C:\Users\tamersaad\Desktop\مكتبة المراجع البيطرية المعتمدة (VetMind Library)"
GLOBAL_DESKTOP = os.path.join(DESKTOP_DIR, "02_المراجع_الدولية_المعتمدة_Tier1")
ARAB_DESKTOP = os.path.join(DESKTOP_DIR, "01_المراجع_العربية_المعتمدة")

os.makedirs(DOCS_DIR, exist_ok=True)
os.makedirs(DOWNLOADS_DIR, exist_ok=True)
os.makedirs(GLOBAL_DESKTOP, exist_ok=True)

GLOBAL_BOOKS = [
    {
        "id": "global_1",
        "url": "https://archive.org/download/BLOODRADOSTITSVeterinaryMedicine10thEdition/BLOOD%20RADOSTITS%20Veterinary%20Medicine%2010th%20Edition.pdf",
        "title_en": "01_Blood_Radostits_Veterinary_Medicine_10th_Ed"
    },
    {
        "id": "global_2",
        "url": "https://archive.org/download/largeanimalinternalmedicine/Veterinary%20Anasthesia%20and%20Pain%20Management%20Secrets.pdf",
        "title_en": "02_Veterinary_Anasthesia_and_Pain_Management_Secrets"
    },
    {
        "id": "global_3",
        "url": "https://archive.org/download/BLOODRADOSTITSVeterinaryMedicine10thEdition/Clinical%20Veterinary%20Advisor%20Dog%20And%20Cat.pdf",
        "title_en": "03_Clinical_Veterinary_Advisor_Dog_And_Cat"
    },
    {
        "id": "global_4",
        "url": "https://archive.org/download/BLOODRADOSTITSVeterinaryMedicine10thEdition/Immunology%20by%20Kuby%205th%20edition.pdf",
        "title_en": "04_Kuby_Immunology_Veterinary_Benchmark"
    },
    {
        "id": "global_5",
        "url": "https://archive.org/download/DuncanPrassesVeterinaryLaboratoryMedicineClinicalPathology/Duncan%20%26%20Prasse%27s%20Veterinary%20Laboratory%20Medicine%20Clinical%20Pathology.pdf",
        "title_en": "05_Duncan_and_Prasse_Veterinary_Laboratory_Medicine"
    },
    {
        "id": "global_6",
        "url": "https://archive.org/download/BLOODRADOSTITSVeterinaryMedicine10thEdition/Fundamentals%20of%20Veterinary%20Clinical%20Pathology.pdf",
        "title_en": "06_Fundamentals_of_Veterinary_Clinical_Pathology"
    },
    {
        "id": "global_7",
        "url": "https://archive.org/download/BLOODRADOSTITSVeterinaryMedicine10thEdition/Vet%20Microbiology%20Quinn.pdf",
        "title_en": "07_Veterinary_Microbiology_Quinn"
    },
    {
        "id": "global_8",
        "url": "https://archive.org/download/BLOODRADOSTITSVeterinaryMedicine10thEdition/Textbook%20of%20Veterinary%20General%20Pathology.pdf",
        "title_en": "08_Textbook_of_Veterinary_General_Pathology"
    },
    {
        "id": "global_9",
        "url": "https://archive.org/download/BLOODRADOSTITSVeterinaryMedicine10thEdition/Veterinary%20Microbiology.pdf",
        "title_en": "09_Veterinary_Microbiology_Comprehensive"
    },
    {
        "id": "global_10",
        "url": "https://archive.org/download/largeanimalinternalmedicine/Color%20Atlas%20of%20the%20Horse%27s%20Foot%20complete.pdf",
        "title_en": "10_Color_Atlas_of_the_Horse_Foot"
    },
    {
        "id": "global_11",
        "url": "https://archive.org/download/largeanimalinternalmedicine/Current%20Therapy%20in%20Equine%20Reproduction%201.pdf",
        "title_en": "11_Current_Therapy_in_Equine_Reproduction"
    },
    {
        "id": "global_12",
        "url": "https://archive.org/download/largeanimalinternalmedicine/Manual%20of%20Equine%20Reproduction%20%28Third%20Edition%292.pdf",
        "title_en": "12_Manual_of_Equine_Reproduction_3rd_Ed"
    },
    {
        "id": "global_13",
        "url": "https://archive.org/download/largeanimalinternalmedicine/A%20GUIDE%20TO%20EQUINE%20INJECTION%20AND%20REGIONAL%20ANESTHESIA.pdf",
        "title_en": "13_Guide_to_Equine_Injection_and_Regional_Anesthesia"
    },
    {
        "id": "global_14",
        "url": "https://archive.org/download/largeanimalinternalmedicine/Equine%20Dentistry%20%28Third%20Edition%29.pdf",
        "title_en": "14_Equine_Dentistry_3rd_Edition"
    },
    {
        "id": "global_15",
        "url": "https://archive.org/download/largeanimalinternalmedicine/Equine%20Dermatology%20%28Second%20Edition%29.pdf",
        "title_en": "15_Equine_Dermatology_2nd_Edition"
    },
    {
        "id": "global_16",
        "url": "https://archive.org/download/largeanimalinternalmedicine/Handbook%20of%20Equine%20Anaesthesia%20%2C%202nd%20edition.pdf",
        "title_en": "16_Handbook_of_Equine_Anaesthesia_2nd_Ed"
    },
    {
        "id": "global_17",
        "url": "https://archive.org/download/largeanimalinternalmedicine/Veterinary%20Anaesthesia%20%28bibliotecamvz.blogspot.com%29.pdf",
        "title_en": "17_Veterinary_Anaesthesia_Clinical_Manual"
    },
    {
        "id": "global_18",
        "url": "https://archive.org/download/largeanimalinternalmedicine/The%20Equine%20Manual%20%20%28Second%20Edition%29.pdf",
        "title_en": "18_The_Equine_Manual_2nd_Edition"
    },
    {
        "id": "global_19",
        "url": "https://archive.org/download/largeanimalinternalmedicine/The%20Equine%20Veterinary%20Nursing%20Manual.pdf",
        "title_en": "19_The_Equine_Veterinary_Nursing_Manual"
    },
    {
        "id": "global_20",
        "url": "https://archive.org/download/largeanimalinternalmedicine/Rooney_s%20Guide%20To%20The%20Dissection%20of%20the%20Horse%20-%207th%20Ed%20-%20Orsini%20and%20Sack.pdf",
        "title_en": "20_Rooney_Guide_to_Dissection_of_the_Horse_7th_Ed"
    }
]

def download_file(url, dest_path, ref_id):
    part_path = dest_path + ".part"
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, context=ctx, timeout=300) as resp, open(part_path, 'wb') as out_f:
                chunk_size = 128 * 1024
                total = 0
                t0 = time.time()
                last_log = t0
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    out_f.write(chunk)
                    total += len(chunk)
                    now = time.time()
                    if now - last_log >= 12:
                        mb = round(total / 1024 / 1024, 2)
                        print(f"  [{ref_id}] {mb} MB downloaded...", flush=True)
                        last_log = now

            if os.path.exists(dest_path):
                os.remove(dest_path)
            os.rename(part_path, dest_path)
            sz = round(os.path.getsize(dest_path)/1024/1024, 2)
            print(f"[DONE] {ref_id} ({sz} MB) in {round(time.time()-t0, 1)}s", flush=True)
            return True
        except Exception as e:
            print(f"  [ATTEMPT {attempt}] {ref_id} failed: {e}", flush=True)
            if os.path.exists(part_path):
                try:
                    os.remove(part_path)
                except Exception:
                    pass
            time.sleep(2)
    return False

def sync_to_desktop_and_zip():
    print("\n--- Syncing to Desktop and building ZIP bundles ---", flush=True)
    # Copy global to desktop
    for b in GLOBAL_BOOKS:
        ref_id = b["id"]
        src = os.path.join(DOCS_DIR, f"{ref_id}.pdf")
        if os.path.exists(src) and os.path.getsize(src) > 500 * 1024:
            dst = os.path.join(GLOBAL_DESKTOP, f"{b['title_en']}.pdf")
            shutil.copy2(src, dst)
            
    # Also sync arab_6
    src_a6 = os.path.join(DOCS_DIR, "arab_6.pdf")
    if os.path.exists(src_a6) and os.path.getsize(src_a6) > 500 * 1024:
        dst_a6 = os.path.join(ARAB_DESKTOP, "06_المعجم_في_علم_الدواجن_والإنتاج_الحيواني.pdf")
        shutil.copy2(src_a6, dst_a6)
        
    # Rebuild Global ZIP
    global_zip = os.path.join(DOWNLOADS_DIR, "VetMind_Global_Tier1_20_References.zip")
    with zipfile.ZipFile(global_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for b in GLOBAL_BOOKS:
            src = os.path.join(DOCS_DIR, f"{b['id']}.pdf")
            if os.path.exists(src):
                zf.write(src, arcname=f"{b['title_en']}.pdf")
    print(f"  Global ZIP: {round(os.path.getsize(global_zip)/1024/1024, 2)} MB", flush=True)
    shutil.copy2(global_zip, os.path.join(DESKTOP_DIR, "VetMind_Global_Tier1_20_References.zip"))

    # Rebuild Complete ZIP
    complete_zip = os.path.join(DOWNLOADS_DIR, "VetMind_Enterprise_30_References_Complete.zip")
    with zipfile.ZipFile(complete_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for i in range(1, 11):
            src = os.path.join(DOCS_DIR, f"arab_{i}.pdf")
            if os.path.exists(src):
                zf.write(src, arcname=f"01_المراجع_العربية/arab_{i}.pdf")
        for b in GLOBAL_BOOKS:
            src = os.path.join(DOCS_DIR, f"{b['id']}.pdf")
            if os.path.exists(src):
                zf.write(src, arcname=f"02_المراجع_الدولية/{b['title_en']}.pdf")
    print(f"  Complete 30 ZIP: {round(os.path.getsize(complete_zip)/1024/1024, 2)} MB", flush=True)
    shutil.copy2(complete_zip, os.path.join(DESKTOP_DIR, "مكتبة_المراجع_البيطرية_الكاملة_30_مرجع_VetMind_Enterprise.zip"))

def main():
    print(f"Starting Sequential Global Book Downloader for {len(GLOBAL_BOOKS)} books...", flush=True)
    for b in GLOBAL_BOOKS:
        ref_id = b["id"]
        dest = os.path.join(DOCS_DIR, f"{ref_id}.pdf")
        if os.path.exists(dest) and os.path.getsize(dest) > 500 * 1024:
            print(f"[SKIP] {ref_id} already exists ({round(os.path.getsize(dest)/1024/1024, 2)} MB)", flush=True)
            continue
        print(f"\n[DOWNLOADING] {ref_id}: {b['title_en']}...", flush=True)
        download_file(b["url"], dest, ref_id)
        time.sleep(1) # Gentle 1s delay to prevent connection throttle
        
    sync_to_desktop_and_zip()
    print("\n=== ALL GLOBAL BOOKS DOWNLOADED AND PACKAGED SUCCESSFULLY! ===", flush=True)

if __name__ == "__main__":
    main()
