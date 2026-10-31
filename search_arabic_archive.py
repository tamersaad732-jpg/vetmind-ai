import urllib.request, json, ssl, urllib.parse, sys
sys.stdout.reconfigure(encoding='utf-8')

ctx = ssl._create_unverified_context()
q = 'language:ara AND ("البيطري" OR "البيطرية" OR "أمراض الدواجن" OR "أمراض الحيوان" OR "أمراض الخيل" OR "أمراض الأبقار")'
url = f'https://archive.org/advancedsearch.php?q={urllib.parse.quote(q)}&fl[]=identifier,title,item_size&rows=25&output=json'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        docs = res.get('response', {}).get('docs', [])
        print('Found Arabic veterinary items:', len(docs))
        for d in docs:
            mb = round(int(d.get('item_size', 0))/1024/1024, 1)
            print(f"{d.get('identifier')} | {d.get('title')} | {mb} MB")
except Exception as e:
    print('Error:', e)
