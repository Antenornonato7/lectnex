"""Agora no mercado: manchetes mais recentes e de maior impacto (RSS de veículos da lista do manual), quase ao vivo.

Gera data/noticias-agora.json com até 16 manchetes das últimas 3 horas, ordenadas por impacto + recência.
Com LOOP_MIN, repete a coleta a cada 2,5 min durante esse tempo e publica no branch 'ao-vivo' (o site lê de lá).
Reuters e Valor entram via Google Notícias (RSS público), filtrando só os veículos da lista.
Só título, fonte, horário e link (nunca o texto da matéria). Etiquetas WIN/WDO/DI por palavras-chave.
Fontes: veículos da seção "Fontes" de docs/leitura-do-dia.md que publicam RSS. Uma fonte fora do ar é ignorada.
"""
import datetime as dt
import email.utils
import html
import json
import os
import re
import base64
import subprocess
import sys
import time
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET

BRT = dt.timezone(dt.timedelta(hours=-3))
AGORA = dt.datetime.now(dt.timezone.utc)
SAIDA = os.environ.get('SAIDA', 'data/noticias-agora.json')
JANELA_H = 3
UA = {'User-Agent': 'Mozilla/5.0 (compatible; LectnexBot/1.0; +https://lectnex.com.br/)', 'Accept': 'application/rss+xml, application/xml, text/xml, */*'}

FEEDS = [
    ('InfoMoney', 'https://www.infomoney.com.br/mercados/feed/'),
    ('InfoMoney', 'https://www.infomoney.com.br/economia/feed/'),
    ('CNN Brasil', 'https://www.cnnbrasil.com.br/economia/feed/'),
    ('Agência Brasil', 'https://agenciabrasil.ebc.com.br/rss/economia/feed.xml'),
    ('Folha', 'https://feeds.folha.uol.com.br/mercado/rss091.xml'),
    ('Estadão', 'https://www.estadao.com.br/arc/outboundfeeds/feeds/rss/sections/economia/'),
    ('Bloomberg Línea', 'https://www.bloomberglinea.com.br/arc/outboundfeeds/rss/?outputType=xml'),
    ('CNBC', 'https://www.cnbc.com/id/20910258/device/rss/rss.html'),
    ('CNBC', 'https://www.cnbc.com/id/100003114/device/rss/rss.html'),
]
# Google Notícias (RSS público): traz Reuters e Valor, que não têm RSS próprio. Só entram veículos da lista abaixo.
GN = 'https://news.google.com/rss/search?hl=pt-BR&gl=BR&ceid=BR:pt-419&q='
FEEDS_GN = [
    GN + 'Ibovespa+OR+%22d%C3%B3lar%22+OR+Copom+OR+Selic+OR+%22juros+futuros%22+when:2h',
    GN + 'Reuters+Brasil+mercado+OR+Petrobras+OR+Vale+OR+%22Banco+Central%22+when:2h',
    GN + 'a%C3%A7%C3%B5es+B3+fechamento+OR+%22maiores+altas%22+OR+balan%C3%A7o+when:3h',
]
FONTES_OK = {'Reuters': 'Reuters', 'Valor Econômico': 'Valor', 'Valor': 'Valor', 'InfoMoney': 'InfoMoney', 'Folha de S.Paulo': 'Folha',
             'Estadão': 'Estadão', 'Estadão E-Investidor': 'Estadão', 'O Globo': 'O Globo', 'CNN Brasil': 'CNN Brasil', 'Bloomberg Línea': 'Bloomberg Línea',
             'Bloomberg Línea Brasil': 'Bloomberg Línea', 'Agência Brasil': 'Agência Brasil', 'Exame': 'Exame', 'CNBC': 'CNBC', 'Money Times': 'Money Times'}
# empresas → código (para ligar a manchete à cotação do dia)
EMPRESAS = {'petrobras': 'PETR4', 'itau unibanco': 'ITUB4', 'itau': 'ITUB4', 'itausa': 'ITSA4', 'bradesco': 'BBDC4',
            'banco do brasil': 'BBAS3', 'b3': 'B3SA3', 'eletrobras': 'ELET3', 'ambev': 'ABEV3', 'weg': 'WEGE3', 'suzano': 'SUZB3',
            'localiza': 'RENT3', 'magazine luiza': 'MGLU3', 'magalu': 'MGLU3', 'gerdau': 'GGBR4', 'prio': 'PRIO3', 'petrorio': 'PRIO3',
            'rede d\'or': 'RDOR3', 'btg pactual': 'BPAC11', 'btg': 'BPAC11', 'hapvida': 'HAPV3', 'sabesp': 'SBSP3', 'cemig': 'CMIG4',
            'csn mineracao': 'CMIN3', 'cosan': 'CSAN3', 'equatorial': 'EQTL3', 'eneva': 'ENEV3', 'klabin': 'KLBN11', 'renner': 'LREN3',
            'raia drogasil': 'RADL3', 'raiadrogasil': 'RADL3', 'tim brasil': 'TIMS3', 'totvs': 'TOTS3', 'ultrapar': 'UGPA3', 'vibra energia': 'VBBR3',
            'telefonica brasil': 'VIVT3', 'embraer': 'EMBR3', 'braskem': 'BRKM5', 'azul': 'AZUL4', 'gol linhas': 'GOLL4', 'assai': 'ASAI3', 'bb seguridade': 'BBSE3', 'caixa seguridade': 'CXSE3'}


def norm(s):
    s = unicodedata.normalize('NFKD', s.lower())
    return ''.join(c for c in s if not unicodedata.combining(c))


# (peso, ativos, termos) — termos já sem acento e em minúsculas
REGRAS = [
    (5, 'DI WDO', ['copom', 'selic', 'fomc', 'federal reserve', ' fed ', 'powell', 'galipolo', 'banco central', 'taxa de juros', 'interest rate', 'rate cut', 'rate hike']),
    (4, 'DI', ['ipca', 'inflacao', 'inflation', ' cpi', ' pce', 'focus', 'arcabouco', 'fiscal', 'meta fiscal', 'tesouro', 'treasury', 'treasuries', 'di futuro', 'curva de juros', 'haddad']),
    (4, 'WDO', ['dolar', 'cambio', 'real ', 'payroll', 'nonfarm', 'jobs report', 'desemprego nos eua', 'jolts', 'tarifa', 'tariff']),
    (4, 'WIN', ['ibovespa', 'b3 ', 'bolsa brasileira', 'petrobras', 'vale ', 'itau', 'bradesco', 'banco do brasil', 'stocks', 's&p 500', 'nasdaq', 'dow jones', 'wall street']),
    (3, 'WIN WDO', ['petroleo', 'brent', 'oil', 'opep', 'opec', 'ormuz', 'hormuz', 'minerio', 'iron ore', 'china', 'guerra', ' war', 'sancoes', 'sanctions', 'recessao', 'recession']),
    (2, 'WIN', ['balanco', 'lucro', 'resultado do', 'earnings', 'dividendos', 'ipo', 'rating', 'fitch', 'moody', 's&p global']),
    (2, 'DI', ['pib', 'gdp', 'emprego', 'varejo', 'retail sales', 'producao industrial', 'pmi', 'ism ']),
]
FORA = ['horoscopo', 'futebol', 'novela', 'bbb', 'receita de', 'cupom', 'black friday', 'melhores cartoes', 'renda extra', 'como declarar',
        'imposto de renda 20', 'concurso', 'loteria', 'mega-sena', 'quina', 'previsao do tempo', 'podcast', 'video:', 'ao vivo:', 'live:', 'quiz']


def pontuar(titulo):
    t = ' ' + norm(titulo) + ' '
    if any(f in t for f in FORA):
        return 0, []
    score, ativos = 0, set()
    for peso, atv, termos in REGRAS:
        if any(x in t for x in termos):
            score += peso
            ativos.update(atv.split())
    return score, sorted(ativos, key=['WIN', 'WDO', 'DI'].index)


def data_item(it):
    for tag in ('pubDate', '{http://purl.org/dc/elements/1.1/}date', '{http://www.w3.org/2005/Atom}updated', '{http://www.w3.org/2005/Atom}published'):
        el = it.find(tag)
        if el is not None and el.text:
            s = el.text.strip()
            try:
                d = email.utils.parsedate_to_datetime(s)
            except Exception:
                try:
                    d = dt.datetime.fromisoformat(s.replace('Z', '+00:00'))
                except Exception:
                    continue
            return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
    return None


def ler_feed(fonte, url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        raiz = ET.fromstring(r.read())
    itens = raiz.findall('.//item') or raiz.findall('.//{http://www.w3.org/2005/Atom}entry')
    out = []
    for it in itens[:40]:
        tit = it.findtext('title') or it.findtext('{http://www.w3.org/2005/Atom}title') or ''
        link = it.findtext('link') or ''
        if not link:
            el = it.find('{http://www.w3.org/2005/Atom}link')
            link = el.get('href') if el is not None else ''
        tit = html.unescape(re.sub(r'<[^>]+>', '', tit)).strip()
        d = data_item(it)
        if not tit or not link.startswith('http') or not d:
            continue
        out.append({'titulo': tit, 'fonte': fonte, 'url': link.strip(), 'publicado': d})
    return out


def ler_gn(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        raiz = ET.fromstring(r.read())
    out = []
    itens = raiz.findall('.//item')[:60]
    if not getattr(ler_gn, 'avisou', False):
        from collections import Counter
        print('::notice::Google Notícias (1ª consulta): ' + str(len(itens)) + ' itens; fontes: ' + ', '.join(f'{k} ({v})' for k, v in Counter((i.findtext('source') or '?').strip() for i in itens).most_common(12)))
        ler_gn.avisou = True
    for it in itens:
        fonte = (it.findtext('source') or '').strip()
        nome = FONTES_OK.get(fonte)
        if not nome:
            continue
        tit = html.unescape(it.findtext('title') or '').strip()
        tit = re.sub(r'\s+-\s+' + re.escape(fonte) + r'\s*$', '', tit)
        d, link = data_item(it), (it.findtext('link') or '').strip()
        if tit and d and link.startswith('http'):
            out.append({'titulo': tit, 'fonte': nome, 'url': link, 'publicado': d})
    return out


def tickers(titulo):
    t = ' ' + norm(titulo) + ' '
    achados = set(re.findall(r'\b([A-Z]{4}(?:3|4|5|6|11))\b', titulo))
    for nome, tk in EMPRESAS.items():
        if re.search(r'(?<![a-z0-9-])' + re.escape(nome) + r'(?![a-z0-9-])', t):
            achados.add(tk)
    # "Vale" só com maiúscula e fora de expressões comuns ("vale a pena", "vale-refeição")
    if re.search(r'(?<![\w-])Vale(?![\w-])(?!\s+a\s+pena)', titulo):
        achados.add('VALE3')
    return sorted(achados)[:3]


ENVIADAS = []  # [{'url', 'titulo', 'em'}] — últimas 24 h; carregado do branch ao-vivo no início
HOJE = []  # manchetes relevantes do dia (para o fechamento mostrar o que mexeu no preço)


def alerta_celular(final):
    """Push (OneSignal, tag 'surpresa') para manchete de ALTO impacto em WIN/WDO publicada há ≤ 12 min.
    Limites: 7h–21h (Brasília), no máximo 1 a cada 20 min e 5 por dia, nada parecido com o que já foi enviado."""
    global ENVIADAS
    agora_brt = AGORA.astimezone(BRT)
    ENVIADAS = [e for e in ENVIADAS if (AGORA - dt.datetime.fromisoformat(e['em'])).total_seconds() < 86400]
    if not os.environ.get('ONESIGNAL_API_KEY') or not (7 <= agora_brt.hour < 21):
        return ENVIADAS
    hoje = [e for e in ENVIADAS if dt.datetime.fromisoformat(e['em']).astimezone(BRT).date() == agora_brt.date()]
    if len(hoje) >= 5 or (ENVIADAS and (AGORA - dt.datetime.fromisoformat(ENVIADAS[-1]['em'])).total_seconds() < 1200):
        return ENVIADAS
    for n in sorted(final, key=lambda n: n['idade']):
        if n['impacto'] < 5 or n['idade'] > 12 or not ({'WIN', 'WDO'} & set(n['ativos'])):
            continue
        if any(e['url'] == n['url'] or parecida(e['titulo'], n['titulo']) for e in ENVIADAS):
            continue
        try:
            import push
            ok = push.enviar('surpresa', f"⚡ {n['fonte']} · Agora no mercado", n['titulo'][:170],
                             'https://lectnex.com.br/?utm_source=push&utm_medium=noticia#ultimas', 'noticia-' + n['url'])
        except Exception as e:
            print(f'::warning::Push da manchete falhou: {e.__class__.__name__}')
            ok = False
        if ok:
            ENVIADAS.append({'url': n['url'], 'titulo': n['titulo'], 'em': AGORA.isoformat(timespec='seconds')})
            print(f"::notice::Push enviado: {n['titulo'][:90]}")
        break
    return ENVIADAS


MERCADO = {}  # série de 5 min do dia (Ibovespa e dólar) + reação 30 min depois de cada manchete


def serie_yahoo(sym):
    ua = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36', 'Accept': 'application/json'}
    for host in ('query2', 'query1'):
        try:
            req = urllib.request.Request(f'https://{host}.finance.yahoo.com/v8/finance/chart/{sym}?interval=5m&range=1d', headers=ua)
            with urllib.request.urlopen(req, timeout=20) as r:
                res = json.loads(r.read())['chart']['result'][0]
            pts = [(dt.datetime.fromtimestamp(t, BRT), c) for t, c in zip(res['timestamp'], res['indicators']['quote'][0]['close']) if c]
            return pts, res['meta'].get('chartPreviousClose') or res['meta'].get('previousClose')
        except Exception as e:
            err = e
    print(f'::warning::Série de 5 min indisponível ({sym}): {err.__class__.__name__}')
    return [], None


def atualizar_mercado():
    """Durante o pregão (dias úteis, 9h55–18h40), guarda o dia em barras de 5 min e mede a reação de cada manchete."""
    global MERCADO
    agora = AGORA.astimezone(BRT)
    if agora.weekday() >= 5 or not (dt.time(9, 55) <= agora.time() <= dt.time(18, 40)):
        return
    dia = agora.date().isoformat()
    out = {'data': dia, 'atualizado_em': agora.isoformat(timespec='minutes')}
    series = {}
    for nome, sym in (('ibov', '%5EBVSP'), ('dolar', 'BRL%3DX')):
        pts, ant = serie_yahoo(sym)
        pts = [(t, c) for t, c in pts if t.date().isoformat() == dia and dt.time(9, 0) <= t.time() <= dt.time(18, 30)]
        if pts:
            series[nome] = pts
            out[nome] = {'anterior': ant, 'pontos': [[t.strftime('%H:%M'), round(c, 4 if nome == 'dolar' else 0)] for t, c in pts]}
    if not series:
        return

    def reacao(pts, t0):
        antes = [c for t, c in pts if t <= t0]
        depois = [c for t, c in pts if t0 + dt.timedelta(minutes=25) <= t <= t0 + dt.timedelta(minutes=35)]
        return round((depois[0] / antes[-1] - 1) * 100, 2) if antes and depois else None

    marcas = []
    for h in HOJE:
        t0 = dt.datetime.fromisoformat(h['publicado'])
        if t0.date().isoformat() != dia or not (dt.time(9, 0) <= t0.time() <= dt.time(18, 0)):
            continue
        m = {'hora': t0.strftime('%H:%M'), 'titulo': h['titulo'], 'fonte': h['fonte'], 'url': h['url'], 'impacto': h.get('impacto'),
             'ativos': h.get('ativos', []), 'tickers': h.get('tickers', [])}
        if 'ibov' in series: m['ibov30'] = reacao(series['ibov'], t0)
        if 'dolar' in series: m['dolar30'] = reacao(series['dolar'], t0)
        marcas.append(m)
    out['marcadores'] = marcas
    MERCADO = out


def carregar_estado():
    """Lê do branch ao-vivo a lista de manchetes já enviadas por push (para não repetir entre execuções)."""
    global ENVIADAS
    tok, repo = os.environ.get('GITHUB_TOKEN'), os.environ.get('GITHUB_REPOSITORY')
    if not tok or not repo:
        return
    try:
        req = urllib.request.Request(f'https://api.github.com/repos/{repo}/contents/noticias-agora.json?ref=ao-vivo',
                                     headers={'Authorization': f'Bearer {tok}', 'Accept': 'application/vnd.github.raw', 'User-Agent': 'lectnex-bot'})
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.loads(r.read())
        ENVIADAS = d.get('enviadas', [])
        global HOJE
        HOJE = d.get('hoje', [])
        global MERCADO
        MERCADO = d.get('mercado', {})
        json.dump(d, open(SAIDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)  # base de comparação = o que está no ar
    except Exception as e:
        print(f'::warning::Não consegui ler o estado do ao-vivo: {e.__class__.__name__}')


def parecida(a, b):
    sa, sb = set(re.findall(r'\w{4,}', norm(a))), set(re.findall(r'\w{4,}', norm(b)))
    return bool(sa and sb) and len(sa & sb) / min(len(sa), len(sb)) >= 0.6


def main():
    global AGORA
    AGORA = dt.datetime.now(dt.timezone.utc)
    todos, falhas = [], []
    for fonte, url in FEEDS:
        try:
            todos += ler_feed(fonte, url)
        except Exception as e:
            falhas.append(f'{fonte} ({url.split("/")[2]}): {e.__class__.__name__}')
    for url in FEEDS_GN:
        try:
            todos += ler_gn(url)
        except Exception as e:
            falhas.append(f'Google Notícias: {e.__class__.__name__}')
    if falhas:
        print('::warning::Feeds indisponíveis: ' + ' | '.join(falhas))
    cands = []
    for n in todos:
        idade = (AGORA - n['publicado']).total_seconds() / 60
        if idade < -10 or idade > JANELA_H * 60:
            continue
        score, ativos = pontuar(n['titulo'])
        tks = tickers(n['titulo'])
        if tks and score < 3:
            score, ativos = 3, sorted(set(ativos) | {'WIN'}, key=['WIN', 'WDO', 'DI'].index)  # empresa do Ibovespa citada
        if score < 3:
            continue
        n['tickers'] = tks
        recencia = 4 if idade <= 15 else 2 if idade <= 60 else 0
        n.update(score=score + recencia, impacto=score, ativos=ativos, idade=idade)
        cands.append(n)
    cands.sort(key=lambda n: (-n['score'], n['idade']))
    final = []
    for n in cands:
        if any(parecida(n['titulo'], f['titulo']) for f in final):
            continue
        final.append(n)
        if len(final) == 16:
            break
    final.sort(key=lambda n: n['idade'])
    enviadas = alerta_celular(final)
    global HOJE
    dia = AGORA.astimezone(BRT).date().isoformat()
    HOJE = [h for h in HOJE if h['publicado'][:10] == dia]
    urls = {h['url'] for h in HOJE}
    for n in final:
        pub = n['publicado'].astimezone(BRT)
        if pub.date().isoformat() == dia and n['url'] not in urls and (n['impacto'] >= 4 or n.get('tickers')):
            HOJE.append({'titulo': n['titulo'], 'fonte': n['fonte'], 'url': n['url'], 'publicado': pub.isoformat(timespec='minutes'),
                         'impacto': 'alto' if n['impacto'] >= 5 else 'medio', 'ativos': n['ativos'], 'tickers': n.get('tickers', [])})
    HOJE = sorted(HOJE, key=lambda h: h['publicado'])[-80:]
    atualizar_mercado()
    novo = {
        'mercado': MERCADO,
        'hoje': HOJE,
        'enviadas': enviadas,
        'atualizado_em': AGORA.astimezone(BRT).isoformat(timespec='minutes'),
        'janela_horas': JANELA_H,
        'fontes_ok': sorted({n['fonte'] for n in todos}),
        'noticias': [{'titulo': n['titulo'], 'fonte': n['fonte'], 'url': n['url'],
                      'publicado': n['publicado'].astimezone(BRT).isoformat(timespec='minutes'),
                      'impacto': 'alto' if n['impacto'] >= 5 else 'medio', 'ativos': n['ativos'], 'tickers': n.get('tickers', [])} for n in final],
    }
    try:
        antigo = json.load(open(SAIDA, encoding='utf-8'))
    except Exception:
        antigo = {}
    if [x['url'] for x in antigo.get('noticias', [])] == [x['url'] for x in novo['noticias']] and antigo.get('enviadas') == enviadas and len(antigo.get('hoje', [])) == len(HOJE) and antigo.get('mercado', {}).get('atualizado_em') == MERCADO.get('atualizado_em'):
        print(f'Sem mudança ({len(final)} manchetes); não grava.')
        return False
    json.dump(novo, open(SAIDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(final)} manchetes de {len(todos)} lidas ({len(cands)} relevantes).')
    for n in final:
        print(f"  {n['publicado'].astimezone(BRT):%H:%M} [{n['fonte']}] {'/'.join(n['ativos'])} {' '.join(n.get('tickers', []))} {n['titulo'][:90]}")
    return True


def publicar_ao_vivo():
    """Grava o JSON no branch 'ao-vivo' pela API do GitHub (não dispara build do GitHub Pages).
    O site lê de raw.githubusercontent.com/<repo>/ao-vivo/noticias-agora.json."""
    tok, repo = os.environ.get('GITHUB_TOKEN'), os.environ.get('GITHUB_REPOSITORY')
    if not tok or not repo:
        return
    api = f'https://api.github.com/repos/{repo}'
    h = {'Authorization': f'Bearer {tok}', 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'lectnex-bot'}
    def chamar(metodo, url, dados=None):
        req = urllib.request.Request(url, method=metodo, headers=h, data=json.dumps(dados).encode() if dados is not None else None)
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read() or b'{}')
    try:
        chamar('GET', f'{api}/git/ref/heads/ao-vivo')
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        base = chamar('GET', f'{api}/git/ref/heads/main')['object']['sha']
        chamar('POST', f'{api}/git/refs', {'ref': 'refs/heads/ao-vivo', 'sha': base})
    sha = None
    try:
        sha = chamar('GET', f'{api}/contents/noticias-agora.json?ref=ao-vivo')['sha']
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
    corpo = {'message': 'ao vivo: ' + dt.datetime.now(BRT).strftime('%d/%m %H:%M'), 'branch': 'ao-vivo',
             'content': base64.b64encode(open(SAIDA, 'rb').read()).decode()}
    if sha:
        corpo['sha'] = sha
    chamar('PUT', f'{api}/contents/noticias-agora.json', corpo)
    print('Publicado no branch ao-vivo.')


if __name__ == '__main__':
    import urllib.error  # noqa: E402
    laco = float(os.environ.get('LOOP_MIN') or 0)
    carregar_estado()
    fim = time.time() + laco * 60
    while True:
        try:
            if main() and laco:
                publicar_ao_vivo()
        except Exception as e:
            print(f'::warning::Rodada falhou: {e.__class__.__name__}: {e}')
        if not laco or time.time() + 150 > fim:
            break
        time.sleep(150)
