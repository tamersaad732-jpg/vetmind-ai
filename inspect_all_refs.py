import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'C:\Users\tamersaad\Desktop\vetmind-ai')
import references_db

refs = references_db.get_all_references()
print(f"Total references in database: {len(refs)}")
missing_count = 0
for idx, r in enumerate(refs, 1):
    rid = r["id"]
    doc_path = os.path.join(r'C:\Users\tamersaad\Desktop\vetmind-ai\static\reference_docs', f"{rid}.txt")
    exists = os.path.exists(doc_path)
    size = os.path.getsize(doc_path) if exists else 0
    if not exists:
        missing_count += 1
    print(f"{idx:02d}. [{rid}] {r['name'][:45]}... | File Exists: {exists} | Size: {size} bytes")

print(f"\nTotal references: {len(refs)}, Missing on disk: {missing_count}")
