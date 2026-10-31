import urllib.request, json, ssl, urllib.parse, sys
sys.stdout.reconfigure(encoding='utf-8')

ctx = ssl._create_unverified_context()
terms = [
    'البيطري', 'بيطري', 'الدواجن', 'الأبقار', 'الخيول', 'الإبل', 'طفيليات', 'فارماكولوجيا'
]
found = {}
for t in terms:
    url = f'https://archive.org/advancedsearch.php?q={urllib.parse.quote(t)}%20AND%20language:ara%20AND%20mediatype:texts&fl[]=identifier,title,item_size&rows=15&output=json'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=6) as resp:
            docs = json.loads(resp.read().decode('utf-8')).get('response', {}).get('docs', [])
            for d in docs:
                ident = d.get('identifier')
                if ident not in found:
                    found[ident] = (d.get('title'), round(int(d.get('item_size', 0))/1024/1024, 1))
    except Exception as e:
        pass

print(f"Total unique Arabic books found: {len(found)}")
for k, v in list(found.items())[:30]:
    print(f"{k} | {v[0]} | {v[1]} MB")
