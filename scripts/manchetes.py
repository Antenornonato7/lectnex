"""Arquivo de manchetes (notícia × preço).

Lê data/dias/AAAA-MM-DD.json (gravados pelo fechamento) e gera:
  - data/manchetes.json      lista única de todas as manchetes com tema e reação em 30 min (busca de manchetes.html)
  - manchetes/AAAA-MM-DD.html página estática e indexável de cada pregão (gráfico, maiores reações, todas as manchetes)
  - sitemap.xml              entradas de manchetes/
Última linha: PAGINAS=... (IndexNow).
"""
import datetime as dt
import glob
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(__file__))
from semana import BASE, br, e, foot, head  # noqa: E402

DIAS = ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo']
# tema → (rótulo, palavras no título sem acento e em minúsculas). A ordem define a cor/posição dos filtros.
TEMAS = {
    'copom': ('Copom e Selic', ['copom', 'selic', 'galipolo', 'banco central', 'bc ', 'politica monetaria']),
    'fed': ('Fed e juros dos EUA', ['fomc', 'federal reserve', ' fed ', 'powell', 'treasury', 'treasuries', 'rate cut', 'rate hike']),
    'inflacao': ('Inflação', ['ipca', 'inflacao', 'inflation', ' cpi', ' pce', 'igp-m', 'precos ao consumidor']),
    'emprego': ('Emprego e payroll', ['payroll', 'nonfarm', 'jobs report', 'desemprego', 'jolts', 'caged', 'pedidos de seguro']),
    'fiscal': ('Fiscal e governo', ['fiscal', 'arcabouco', 'haddad', 'tesouro', 'orcamento', 'gastos', 'divida publica', 'lula', 'congresso']),
    'petroleo': ('Petróleo e Petrobras', ['petroleo', 'brent', ' oil', 'opep', 'opec', 'petrobras', 'ormuz', 'hormuz']),
    'minerio': ('Minério e Vale', ['minerio', 'iron ore', 'vale ', 'siderurg']),
    'china': ('China', ['china', 'chines', 'pequim', 'beijing', 'xi jinping']),
    'cambio': ('Dólar e câmbio', ['dolar', 'cambio', 'real ', 'ptax', 'dxy']),
    'bolsa': ('Bolsa e empresas', ['ibovespa', 'balanco', 'lucro', 'resultado do', 'earnings', 'dividendos', 'acoes', 'wall street', 's&p 500', 'nasdaq']),
    'geopolitica': ('Tarifas e geopolítica', ['tarifa', 'tariff', 'guerra', ' war', 'sancoes', 'sanctions', 'trump', 'eleic']),
}


def norm(s):
    return ' ' + unicodedata.normalize('NFD', (s or '').lower()).encode('ascii', 'ignore').decode() + ' '


def temas(titulo):
    t = norm(titulo)
    return [k for k, (_, ps) in TEMAS.items() if any(p in t for p in ps)]


def var_dia(s):
    p = (s or {}).get('pontos') or []
    return (p[-1][1] / (s.get('anterior') or p[0][1]) - 1) * 100 if p else None


def pct(v, casas=2):
    return '—' if v is None else ('+' if v > 0 else '−' if v < 0 else '') + f'{abs(v):.{casas}f}%'.replace('.', ',')


def cls(v):
    return 'text-slate-500' if not v else 'text-emerald-600 dark:text-emerald-400' if v > 0 else 'text-rose-600 dark:text-rose-400'


def chip(rot, v):
    if v is None:
        return ''
    c = 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400' if v > 0 else 'bg-rose-500/15 text-rose-700 dark:text-rose-400' if v < 0 else 'bg-slate-500/10'
    return f'<span class="px-1.5 py-0.5 font-mono text-[10px] font-bold {c}">{rot} {pct(v)}</span>'


def minutos(hm):
    h, m = map(int, hm.split(':'))
    return h * 60 + m


def svg(m, k):
    """Gráfico estático do dia (o interativo fica em hoje.html)."""
    s = m.get(k) or {}
    pts = s.get('pontos') or []
    if len(pts) < 2:
        return ''
    base = s.get('anterior') or pts[0][1]
    W, H, pl, pr, pt, pb = 1000, 220, 8, 64, 12, 26
    xs = [minutos(p[0]) for p in pts]
    x0, x1 = min(600, xs[0]), max(1080, xs[-1])
    ys = [p[1] for p in pts] + [base]
    lo, hi = min(ys), max(ys)
    pad = (hi - lo) * 0.08 or base * 0.002
    X = lambda v: pl + (v - x0) / (x1 - x0) * (W - pl - pr)
    Y = lambda v: pt + (1 - (v - (lo - pad)) / ((hi + pad) - (lo - pad))) * (H - pt - pb)
    vd = var_dia(s)
    cor = '#10B981' if vd >= 0 else '#F43F5E'
    nome = 'Ibovespa' if k == 'ibov' else 'Dólar'
    o = [f'<svg viewBox="0 0 {W} {H}" class="w-full h-auto font-mono" role="img" aria-label="{nome} ao longo do dia com as manchetes marcadas">']
    for hh in range(10, 19):
        x = X(hh * 60)
        o.append(f'<line x1="{x:.0f}" y1="{pt}" x2="{x:.0f}" y2="{H - pb}" stroke="currentColor" stroke-opacity=".08"/><text x="{x:.0f}" y="{H - 8}" font-size="11" text-anchor="middle" fill="currentColor" fill-opacity=".5">{hh}h</text>')
    o.append(f'<line x1="{pl}" y1="{Y(base):.1f}" x2="{W - pr}" y2="{Y(base):.1f}" stroke="currentColor" stroke-opacity=".35" stroke-dasharray="4 4"/>'
             f'<text x="{W - pr + 6}" y="{Y(base) + 4:.1f}" font-size="11" fill="currentColor" fill-opacity=".55">ant.</text>')
    d = ''.join(f'{"L" if i else "M"}{X(minutos(p[0])):.1f},{Y(p[1]):.1f}' for i, p in enumerate(pts))
    o.append(f'<path d="{d} L{X(xs[-1]):.1f},{H - pb} L{X(xs[0]):.1f},{H - pb} Z" fill="{cor}" fill-opacity=".08"/><path d="{d}" fill="none" stroke="{cor}" stroke-width="2"/>')
    campo = 'ibov30' if k == 'ibov' else 'dolar30'
    for mk in m.get('marcadores', []):
        t = minutos(mk['hora'])
        if t < xs[0] - 5 or t > xs[-1] + 5:
            continue
        antes = [p for p in pts if minutos(p[0]) <= t] or pts[:1]
        c = '#F59E0B' if mk.get('impacto') == 'alto' else '#14B8A6'
        o.append(f'<circle cx="{X(t):.1f}" cy="{Y(antes[-1][1]):.1f}" r="{6 if mk.get("impacto") == "alto" else 4.5}" fill="{c}" stroke="#05101C" stroke-width="2">'
                 f'<title>{e(mk["hora"])} · {e(mk["titulo"])} ({pct(mk.get(campo))} em 30 min)</title></circle>')
    o.append('</svg>')
    return ''.join(o)


def itens_do_dia(m):
    out = []
    for mk in m.get('marcadores', []):
        out.append({'d': m['data'], 'h': mk['hora'], 't': mk['titulo'], 'f': mk.get('fonte'), 'u': mk.get('url'), 'i': mk.get('impacto'),
                    'ib': mk.get('ibov30'), 'dl': mk.get('dolar30'), 'tm': temas(mk['titulo']), 'tk': mk.get('tickers') or []})
    return out


def mexida(x):
    return max(abs(x['ib'] or 0), abs(x['dl'] or 0) * 1.5)  # dólar anda menos: peso 1,5


def pagina(m, datas):
    dia = dt.date.fromisoformat(m['data'])
    url = f'{BASE}manchetes/{m["data"]}.html'
    its = itens_do_dia(m)
    vi, vd = var_dia(m.get('ibov')), var_dia(m.get('dolar'))
    top = sorted([x for x in its if x['ib'] is not None or x['dl'] is not None], key=lambda x: -mexida(x))[:3]
    titulo = f'O que mexeu no mercado em {br(dia, True)}: Ibovespa {pct(vi)}, dólar {pct(vd)}'
    desc = (f'Manchetes de {DIAS[dia.weekday()]} {br(dia, True)} marcadas no gráfico do Ibovespa e do dólar, com a variação nos 30 minutos seguintes. '
            + (f'Maior reação: {top[0]["t"]}' if top else ''))[:158]
    i = datas.index(m['data'])
    ant, prox = (datas[i - 1] if i > 0 else None), (datas[i + 1] if i + 1 < len(datas) else None)
    nav = (f'<nav class="flex justify-between gap-3 font-mono text-xs">'
           + (f'<a href="manchetes/{ant}.html" class="hover:text-lect-teal">← {br(dt.date.fromisoformat(ant))}</a>' if ant else '<span></span>')
           + '<a href="manchetes.html" class="hover:text-lect-teal">buscar no arquivo</a>'
           + (f'<a href="manchetes/{prox}.html" class="hover:text-lect-teal">{br(dt.date.fromisoformat(prox))} →</a>' if prox else '<span></span>') + '</nav>')
    card = lambda r, v, sub: f'<div class="term-panel p-4"><span class="term-label">{r}</span><strong class="block font-display text-xl mt-1">{v}</strong><span class="block text-[11px] text-slate-500 mt-1">{sub}</span></div>'
    cards = (card('IBOVESPA NO DIA', f'<span class="{cls(vi)}">{pct(vi)}</span>', 'contra o fechamento anterior')
             + card('DÓLAR NO DIA', f'<span class="{cls(vd)}">{pct(vd)}</span>', 'contra o fechamento anterior')
             + card('MANCHETES MARCADAS', len(its), f'{sum(1 for x in its if x["i"] == "alto")} de alto impacto'))
    rot = lambda t: ''.join(f'<a href="manchetes.html#{k}" class="px-1.5 py-0.5 border border-slate-300 dark:border-lect-borderDark hover:border-lect-teal">{TEMAS[k][0]}</a>' for k in t)
    destaque = ''.join(f'''<li class="term-panel p-4 flex gap-3"><span class="w-8 h-8 shrink-0 rounded-full bg-lect-orange text-lect-navy font-bold flex items-center justify-center">{n}</span>
        <div class="min-w-0"><span class="font-mono text-[11px] text-slate-500">{e(x["h"])} · {e(x["f"])}</span>
        <h3 class="font-semibold leading-snug mt-0.5"><a href="{e(x["u"])}" target="_blank" rel="noopener nofollow" class="hover:text-lect-teal">{e(x["t"])}</a></h3>
        <div class="flex flex-wrap gap-1 mt-2">{chip("Ibov 30 min", x["ib"])}{chip("Dólar 30 min", x["dl"])}</div></div></li>''' for n, x in enumerate(top, 1))
    lista = ''.join(f'''<li class="px-4 py-3 flex gap-3"><span class="font-mono text-xs font-bold w-12 shrink-0 {"text-lect-orange" if x["i"] == "alto" else "text-lect-teal"}">{e(x["h"])}</span>
        <div class="min-w-0 flex-1"><a href="{e(x["u"])}" target="_blank" rel="noopener nofollow" class="text-sm font-semibold leading-snug hover:text-lect-teal">{e(x["t"])}</a>
        <div class="flex flex-wrap items-center gap-1 mt-1.5 font-mono text-[10px] text-slate-500">{e(x["f"])} {chip("Ibov", x["ib"])} {chip("Dólar", x["dl"])} {rot(x["tm"])}</div></div></li>''' for x in reversed(its))
    graf = ''.join(f'<div class="term-panel p-4"><div class="flex justify-between"><span class="term-label font-bold">{n}</span><span class="font-mono text-sm font-bold {cls(var_dia(m.get(k)))}">{pct(var_dia(m.get(k)))}</span></div><div class="mt-2">{svg(m, k)}</div></div>'
                   for k, n in (('ibov', 'IBOVESPA · WIN'), ('dolar', 'DÓLAR À VISTA · WDO')) if svg(m, k))
    ld = [{'@type': 'Article', 'headline': titulo[:110], 'description': desc, 'url': url, 'inLanguage': 'pt-BR', 'datePublished': m['data'],
           'dateModified': (m.get('atualizado_em') or m['data']), 'author': {'@id': BASE + '#org'}, 'publisher': {'@id': BASE + '#org'},
           'image': BASE + 'assets/brand/og-mercado.jpg'}]
    return head(titulo + ' | Lectnex', desc, url, ld) + f'''
        <section class="border-b border-slate-300 dark:border-lect-borderDark grid-bg"><div class="max-w-5xl mx-auto px-4 sm:px-6 py-10">
            <span class="term-label text-lect-teal font-bold">NOTÍCIA × PREÇO · {DIAS[dia.weekday()].upper()} {br(dia, True)}</span>
            <h1 class="font-display text-2xl sm:text-3xl font-bold tracking-tight mt-1">O que mexeu no mercado em {br(dia, True)}</h1>
            <p class="mt-2 text-sm text-slate-600 dark:text-slate-300 max-w-3xl">Cada manchete marcada no horário em que saiu e a variação do Ibovespa e do dólar nos 30 minutos seguintes.</p>
        </div></section>
        <div class="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-6">
            {nav}
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">{cards}</div>
            {graf}
            <a href="hoje.html?dia={m["data"]}" class="inline-flex items-center gap-1 font-mono text-xs text-lect-teal hover:underline">Ver o gráfico interativo deste dia <i class="ph-bold ph-arrow-right"></i></a>
            {f'<section><h2 class="font-display font-bold text-lg mb-3">As 3 maiores reações em 30 minutos</h2><ol class="space-y-3">{destaque}</ol></section>' if destaque else ''}
            {f'<section><h2 class="font-display font-bold text-lg mb-3">Todas as manchetes do dia</h2><ol class="term-panel divide-y divide-slate-200 dark:divide-lect-borderDark">{lista}</ol></section>' if lista else ''}
            <p class="text-[11px] text-slate-500">Variação do último preço antes da manchete até 30 minutos depois (cotações de 5 min do Yahoo Finance, Ibovespa e dólar à vista). O movimento seguinte não prova que a notícia foi a causa: o mercado reage a muitas coisas ao mesmo tempo. Conteúdo educacional, não é recomendação de investimento.</p>
            {nav}
        </div>
''' + foot()


def main():
    dias = {}
    for f in sorted(glob.glob('data/dias/????-??-??.json')):
        try:
            m = json.load(open(f, encoding='utf-8'))
            if m.get('data') and (m.get('ibov') or m.get('dolar')):
                dias[m['data']] = m
        except Exception:
            pass
    datas = sorted(dias)
    itens = [x for d in datas for x in itens_do_dia(dias[d])]
    os.makedirs('manchetes', exist_ok=True)
    resumo = {d: {'ib': None if var_dia(dias[d].get('ibov')) is None else round(var_dia(dias[d].get('ibov')), 2),
                  'dl': None if var_dia(dias[d].get('dolar')) is None else round(var_dia(dias[d].get('dolar')), 2)} for d in datas}
    novo = {'gerado_em': dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).isoformat(timespec='minutes'),
            'temas': {k: v[0] for k, v in TEMAS.items()}, 'dias': resumo, 'itens': itens}
    try:
        velho = json.load(open('data/manchetes.json', encoding='utf-8'))
        igual = {k: v for k, v in velho.items() if k != 'gerado_em'} == {k: v for k, v in novo.items() if k != 'gerado_em'}
    except Exception:
        igual = False
    if not igual:
        json.dump(novo, open('data/manchetes.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    mudou = []
    for d in datas:
        out, html = f'manchetes/{d}.html', pagina(dias[d], datas)
        if not os.path.exists(out) or open(out, encoding='utf-8').read() != html:
            open(out, 'w', encoding='utf-8').write(html)
            mudou.append(out)
    sm = open('sitemap.xml', encoding='utf-8').read()
    sm = re.sub(r'\s*<url><loc>[^<]*/manchetes/[^<]*</loc>.*?</url>', '', sm)
    novas = ''.join(f'\n  <url><loc>{BASE}manchetes/{d}.html</loc><lastmod>{d}</lastmod><changefreq>monthly</changefreq><priority>0.5</priority></url>' for d in datas)
    open('sitemap.xml', 'w', encoding='utf-8').write(sm.replace('</urlset>', novas + '\n</urlset>'))
    if mudou:
        mudou.append('manchetes.html')
    print(f'::notice::Arquivo de manchetes: {len(datas)} dia(s), {len(itens)} manchete(s); páginas alteradas: {len(mudou)}')
    print('PAGINAS=' + ' '.join(mudou))


if __name__ == '__main__':
    main()
