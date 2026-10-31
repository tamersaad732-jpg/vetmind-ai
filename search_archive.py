import urllib.request, json, ssl, urllib.parse

ctx = ssl._create_unverified_context()
queries = [
    'title:"Veterinary Pharmacology"',
    'title:"Diseases of Poultry"',
    'title:"Veterinary Parasitology"',
    'title:"Diseases of Cattle"',
    'title:"Equine Medicine"',
    'title:"Veterinary Medicine"'
]
for q in queries:
    url = f'https://archive.org/advancedsearch.php?q={urllib.parse.quote(q)}%20AND%20mediatype:texts&fl[]=identifier,title,item_size&rows=3&output=json'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
            docs = json.loads(resp.read().decode('utf-8')).get('response', {}).get('docs', [])
            print(f'=== Query: {q} ===')
            for d in docs:
                print(' ', d.get('identifier'), '|', d.get('title'))
    except Exception as e:
        print(f'Error for {q}: {e}')
