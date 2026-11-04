"""Avisa Bing/Yandex (IndexNow) das páginas alteradas no último push. Chave pública no arquivo <chave>.txt na raiz do site."""
import glob, json, os, subprocess, urllib.request

BASE = 'https://lectnex.com.br/'
chave = next(os.path.basename(f)[:-4] for f in glob.glob('*.txt') if len(os.path.basename(f)) == 36)
mudou = subprocess.run(['git', 'diff', '--name-only', 'HEAD^', 'HEAD'], capture_output=True, text=True).stdout.split()
if os.environ.get('PAGINAS') is not None:
    paginas = os.environ['PAGINAS'].split()
elif os.environ.get('GITHUB_EVENT_NAME') == 'push':
    paginas = [f for f in mudou if f.endswith('.html') and (('/' not in f) or f.startswith(('semana/', 'leitura/', 'manchetes/')))]
else:
    paginas = sorted(glob.glob('*.html') + glob.glob('semana/*.html') + glob.glob('leitura/*.html') + glob.glob('manchetes/*.html'))
if not paginas:
    print('::notice::IndexNow: nenhuma página alterada.'); raise SystemExit
urls = [BASE + ('' if p == 'index.html' else p[:-10] if p.endswith('/index.html') else p) for p in paginas]
corpo = {'host': 'lectnex.com.br', 'key': chave, 'keyLocation': BASE + chave + '.txt', 'urlList': urls}
req = urllib.request.Request('https://api.indexnow.org/indexnow', data=json.dumps(corpo).encode(), headers={'Content-Type': 'application/json; charset=utf-8'})
try:
    with urllib.request.urlopen(req, timeout=20) as r:
        print(f'::notice::IndexNow: {len(urls)} página(s) enviadas (HTTP {r.status}): {", ".join(paginas)}')
except urllib.error.HTTPError as e:
    print(f'::warning::IndexNow recusou (HTTP {e.code}): {e.read().decode()[:150]}')
