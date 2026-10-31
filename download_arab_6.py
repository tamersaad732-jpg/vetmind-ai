import urllib.request, ssl, os, sys

sys.stdout.reconfigure(encoding='utf-8')
ctx = ssl._create_unverified_context()

url = "https://archive.org/download/20230108_20230108_0831/%D8%A7%D9%84%D9%85%D8%B9%D8%AC%D9%85%2B%D9%81%D9%8A%2B%D8%B9%D9%84%D9%85%2B%D8%A7%D9%84%D8%AF%D9%88%D8%A7%D8%AC%D9%86.pdf"
dest = r"C:\Users\tamersaad\Desktop\vetmind-ai\static\reference_docs\arab_6.pdf"

print("Downloading arab_6 (المعجم في علم الدواجن والإنتاج الحيواني)...", flush=True)
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, context=ctx, timeout=60) as resp, open(dest, 'wb') as out_f:
    out_f.write(resp.read())

sz = round(os.path.getsize(dest) / 1024 / 1024, 2)
print(f"arab_6.pdf successfully downloaded: {sz} MB", flush=True)
