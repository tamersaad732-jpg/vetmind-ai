import urllib.request, json, ssl

ctx = ssl._create_unverified_context()
url = 'https://archive.org/advancedsearch.php?q=mediatype%3Atexts%20AND%20format%3A%22Text%20PDF%22%20AND%20(veterinary%20OR%20%22diseases%20of%20cattle%22%20OR%20%22diseases%20of%20poultry%22)&fl[]=identifier,title,item_size&sort[]=downloads%20desc&rows=30&output=json'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        docs = res.get('response', {}).get('docs', [])
        print('Found items:', len(docs))
        for d in docs:
            mb = round(int(d.get('item_size', 0))/1024/1024, 1)
            print(f"{d.get('identifier')} | {d.get('title')} | {mb} MB")
except Exception as e:
    print('Error:', e)
