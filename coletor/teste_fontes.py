import json, urllib.request, time
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36', 'Accept': 'application/json,text/csv,*/*'}
T = 'uRJnTfjL6jypdHfJ8b5LJd'
for nome, url in [
  ('yahoo2-bvsp', 'https://query2.finance.yahoo.com/v8/finance/chart/%5EBVSP?interval=5m&range=5d'),
  ('brapi-bvsp-5m', f'https://brapi.dev/api/quote/%5EBVSP?range=5d&interval=5m&token={T}'),
  ('brapi-usd-5m', f'https://brapi.dev/api/quote/USDBRL=X?range=5d&interval=5m&token={T}'),
  ('brapi-petr-15m', f'https://brapi.dev/api/quote/PETR4?range=1d&interval=15m&token={T}'),
  ('stooq-usdbrl-5', 'https://stooq.com/q/d/l/?s=usdbrl&i=5'),
  ('awesome-usd-n', 'https://economia.awesomeapi.com.br/json/USD-BRL/5'),
]:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
            b = r.read()[:300].decode(errors='replace').replace('\n', ' ')
        print(f'::notice::{nome}: OK {b[:220]}')
    except Exception as e:
        body = ''
        try: body = e.read()[:150].decode(errors='replace')
        except Exception: pass
        print(f'::warning::{nome}: {e} {body}')
    time.sleep(1)
