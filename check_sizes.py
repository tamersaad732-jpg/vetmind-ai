import os

docs = r"C:\Users\tamersaad\Desktop\vetmind-ai\static\reference_docs"
for f in sorted(os.listdir(docs)):
    if f.endswith(('.pdf', '.part')):
        p = os.path.join(docs, f)
        sz = round(os.path.getsize(p) / 1024 / 1024, 2)
        print(f"{f}: {sz} MB")
