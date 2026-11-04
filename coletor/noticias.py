"""Agora no mercado: manchetes mais recentes e de maior impacto (RSS de veículos da lista do manual), a cada ~15 min.

Gera data/noticias-agora.json com até 10 manchetes das últimas 3 horas, ordenadas por impacto + recência.
Só título, fonte, horário e link (nunca o texto da matéria). Etiquetas WIN/WDO/DI por palavras-chave.
Fontes: veículos da seção "Fontes" de docs/leitura-do-dia.md que publicam RSS. Uma fonte fora do ar é ignorada.
"""
import datetime as dt
import email.utils
import html
import json
import os
import re
import sys
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET

BRT = dt.timezone(dt.timedelta(hours=-3))
AGORA = dt.datetime.now(dt.timezone.utc)
SAIDA = 'data/noticias-agora.json'
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


def parecida(a, b):
    sa, sb = set(re.findall(r'\w{4,}', norm(a))), set(re.findall(r'\w{4,}', norm(b)))
    return bool(sa and sb) and len(sa & sb) / min(len(sa), len(sb)) >= 0.6


def main():
    todos, falhas = [], []
    for fonte, url in FEEDS:
        try:
            todos += ler_feed(fonte, url)
        except Exception as e:
            falhas.append(f'{fonte} ({url.split("/")[2]}): {e.__class__.__name__}')
    if falhas:
        print('::warning::Feeds indisponíveis: ' + ' | '.join(falhas))
    cands = []
    for n in todos:
        idade = (AGORA - n['publicado']).total_seconds() / 60
        if idade < -10 or idade > JANELA_H * 60:
            continue
        score, ativos = pontuar(n['titulo'])
        if score < 3:
            continue
        recencia = 4 if idade <= 15 else 2 if idade <= 60 else 0
        n.update(score=score + recencia, impacto=score, ativos=ativos, idade=idade)
        cands.append(n)
    cands.sort(key=lambda n: (-n['score'], n['idade']))
    final = []
    for n in cands:
        if any(parecida(n['titulo'], f['titulo']) for f in final):
            continue
        final.append(n)
        if len(final) == 10:
            break
    final.sort(key=lambda n: n['idade'])
    novo = {
        'atualizado_em': AGORA.astimezone(BRT).isoformat(timespec='minutes'),
        'janela_horas': JANELA_H,
        'fontes_ok': sorted({f for f, u in FEEDS} - {x.split(' (')[0] for x in falhas}),
        'noticias': [{'titulo': n['titulo'], 'fonte': n['fonte'], 'url': n['url'],
                      'publicado': n['publicado'].astimezone(BRT).isoformat(timespec='minutes'),
                      'impacto': 'alto' if n['impacto'] >= 5 else 'medio', 'ativos': n['ativos']} for n in final],
    }
    try:
        antigo = json.load(open(SAIDA, encoding='utf-8'))
    except Exception:
        antigo = {}
    if [x['url'] for x in antigo.get('noticias', [])] == [x['url'] for x in novo['noticias']]:
        print(f'Sem mudança ({len(final)} manchetes); não grava.')
        return
    json.dump(novo, open(SAIDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(final)} manchetes de {len(todos)} lidas ({len(cands)} relevantes).')
    for n in final:
        print(f"  {n['publicado'].astimezone(BRT):%H:%M} [{n['fonte']}] {'/'.join(n['ativos'])} {n['titulo'][:90]}")


if __name__ == '__main__':
    main()
