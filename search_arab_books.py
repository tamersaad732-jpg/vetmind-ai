import urllib.request, json, ssl, sys, urllib.parse

sys.stdout.reconfigure(encoding='utf-8')
ctx = ssl._create_unverified_context()

queries = [
    'بيطري', 'بيطرية', 'أمراض الأبقار', 'أمراض الدواجن', 'أمراض الخيل', 'الطب البيطري', 'أدوية بيطرية'
]

results = {}
for q in queries:
    url = f"https://archive.org/advancedsearch.php?q={urllib.parse.quote(q)}%20AND%20mediatype:texts%20AND%20format:%22Text%20PDF%22&fl[]=identifier,title,item_size&sort[]=downloads%20desc&rows=10&output=json"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx, timeout=6) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            docs = data.get('response', {}).get('docs', [])
            for d in docs:
                ident = d.get('identifier')
                if ident not in results:
                    results[ident] = (d.get('title'), round(int(d.get('item_size', 0))/1024/1024, 1))
    except Exception as e:
        pass

for k, v in results.items():
    print(f"{k} | {v[0]} | {v[1]} MB")
