"""Páginas por dado econômico: dados/<tipo>.html + dados/index.html (estáticas, indexáveis).

Cada página: o que é o dado, quando sai (horário mais comum nas divulgações medidas e a próxima pela agenda),
histórico completo (saiu × consenso, surpresa) e a reação de WIN e WDO (30 min) e do DI de 2 anos (no dia).
Fontes: data/reacoes.json, data/calendario.json. Roda depois do coletor da curva (que mede o DI). Atualiza o sitemap.
Última linha: PAGINAS=... (IndexNow).
"""
import collections
import datetime as dt
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from semana import head, foot, e, BASE, br  # noqa: E402

MIN = 5  # divulgações medidas para ganhar página
SOBRE = {
    'ipca': ('IPCA', 'Inflação oficial do Brasil, medida pelo IBGE. Guia as decisões do Copom: IPCA acima do esperado costuma abrir os juros futuros (DI) e pesar no Ibovespa.', 'IBGE'),
    'payroll': ('Payroll', 'Criação de vagas de emprego fora do setor agrícola nos EUA, divulgada pelo Departamento do Trabalho. Mexe com a expectativa de juros do Fed, com o dólar no mundo e, por tabela, com o WDO.', 'BLS (EUA)'),
    'cpi-eua': ('CPI dos EUA', 'Inflação ao consumidor dos EUA. Inflação acima do esperado reforça juros altos por lá, fortalece o dólar e costuma pressionar o WDO para cima.', 'BLS (EUA)'),
    'fomc': ('Decisão do FOMC (Fed)', 'Decisão de juros do banco central dos EUA. A taxa, o comunicado e a entrevista do presidente do Fed mexem com dólar, juros e bolsas no mundo todo.', 'Federal Reserve'),
    'copom': ('Decisão do Copom', 'Decisão da taxa Selic pelo Banco Central do Brasil. Sai depois do fechamento; a reação aparece na abertura seguinte, no DI, no WIN e no WDO.', 'Banco Central do Brasil'),
}
SLUG = {'cpi-eua': 'cpi-eua', 'ipca': 'ipca', 'payroll': 'payroll', 'fomc': 'fomc', 'copom': 'copom'}


def pct(v):
    return '—' if v is None else ('+' if v > 0 else '−' if v < 0 else '') + f'{abs(v):.2f}%'.replace('.', ',')


def bps(v):
    return '—' if v is None else ('+' if v > 0 else '−' if v < 0 else '') + f'{abs(v):.0f} bps'


def cor(v, inverso=False):
    if v is None or v == 0:
        return 'text-slate-500'
    alta = v > 0
    if inverso:
        alta = not alta
    return 'text-emerald-600 dark:text-emerald-400' if alta else 'text-rose-600 dark:text-rose-400'


def media(rs, k, f=None, absoluto=False):
    v = [r[k] for r in rs if isinstance(r.get(k), (int, float)) and (f is None or f(r))]
    if not v:
        return None, 0
    return (sum(abs(x) for x in v) if absoluto else sum(v)) / len(v), len(v)


def pagina(tipo, rs, cal):
    nome, sobre, fonte = SOBRE.get(tipo, (re.sub(r'\s*\(.*?\)', '', rs[-1]['evento']), '', ''))
    slug = SLUG.get(tipo, tipo)
    url = f'{BASE}dados/{slug}.html'
    hora = collections.Counter(r.get('hora') for r in rs if r.get('hora')).most_common(1)
    hora = hora[0][0] if hora else None
    prox = next((x for x in sorted(cal.get('eventos', []), key=lambda x: (x['data'], x.get('hora') or '')) if x.get('tipo') == tipo and x['data'] >= dt.date.today().isoformat() and not x.get('resultado')), None)
    aw, nw = media(rs, 'win', absoluto=True)
    au, nu = media(rs, 'wdo', absoluto=True)
    ad, nd = media(rs, 'di_bps', absoluto=True)
    linhas = ''
    jan = lambda lst: (lambda h, m: '30 min + 1 h' if h and m else '1 h' if h else '30 min')(sum(1 for r in lst if r.get('janela') == '1h'), sum(1 for r in lst if r.get('janela') != '1h'))
    mistura = jan(rs) == '30 min + 1 h'
    obs = lambda n, lst: f'<span class="block text-[10px] font-normal text-slate-600 dark:text-slate-400">{n} obs · {jan(lst)}</span>'
    recentes = {r['data'] for r in sorted(rs, key=lambda r: r['data'], reverse=True)[:12]}  # têm página própria (divulgacao_paginas.py)
    for r in sorted(rs, key=lambda r: r['data'], reverse=True):
        sup = r.get('surpresa')
        linhas += (f'<tr class="border-t border-slate-100 dark:border-lect-borderDark"><td class="px-3 py-2 whitespace-nowrap">{(f'<a href="dados/{slug}-{r["data"]}.html" class="text-lect-teal hover:underline">' + br(dt.date.fromisoformat(r["data"]), True) + '</a>') if r['data'] in recentes else br(dt.date.fromisoformat(r["data"]), True)}</td>'
                   f'<td class="px-3 py-2 font-sans">{e(r.get("resultado") or "—")}</td><td class="px-3 py-2 font-sans text-slate-500">{e(r.get("consenso") or "—")}</td>'
                   f'<td class="px-3 py-2 whitespace-nowrap {"text-lect-orange" if sup == "acima" else "text-sky-600 dark:text-sky-400" if sup == "abaixo" else "text-slate-500"}">{ {"acima": "▲ acima", "abaixo": "▼ abaixo"}.get(sup, "em linha / s.d.") }</td>'
                   f'<td class="px-3 py-2 text-right {cor(r.get("win"))}">{pct(r.get("win"))}{"*" if r.get("win_abertura") else ""}</td>'
                   f'<td class="px-3 py-2 text-right {cor(r.get("wdo"))}">{pct(r.get("wdo"))}</td>'
                   f'<td class="px-3 py-2 text-right {cor(r.get("di_bps"), inverso=True)}">{bps(r.get("di_bps"))}</td>'
                   f'<td class="px-3 py-2 text-slate-600 dark:text-slate-400 whitespace-nowrap">{"1 h" if r.get("janela") == "1h" else "30 min"}</td></tr>')
    cond = ''
    for lbl, f in (('Quando veio ACIMA do consenso', lambda r: r.get('surpresa') == 'acima'), ('Quando veio ABAIXO do consenso', lambda r: r.get('surpresa') == 'abaixo')):
        w, n1 = media(rs, 'win', f)
        u, _ = media(rs, 'wdo', f)
        d_, _ = media(rs, 'di_bps', f)
        if n1:
            sub = [r for r in rs if f(r)]
            cond += (f'<div class="term-panel p-4"><span class="term-label block">{lbl} · {n1} vez(es)</span><div class="mt-2 grid grid-cols-3 gap-2 font-mono text-sm">'
                     f'<div><span class="block text-[10px] text-slate-500">Ibovespa à vista (média)</span><strong class="{cor(w)}">{pct(w)}</strong>{obs(n1, sub)}</div>'
                     f'<div><span class="block text-[10px] text-slate-500">Dólar à vista (média)</span><strong class="{cor(u)}">{pct(u)}</strong>{obs(n1, sub)}</div>'
                     f'<div><span class="block text-[10px] text-slate-500">DI 2a no dia</span><strong class="{cor(d_, True)}">{bps(d_)}</strong></div></div></div>')
    titulo = f'{nome}: histórico de divulgações e reação do mercado | Lectnex'
    desc = f'{nome}: todas as {len(rs)} divulgações medidas, o que saiu contra o consenso e quanto o mini índice (WIN), o mini dólar (WDO) e os juros (DI) reagiram.'
    faq = [(f'Que horas sai o {nome}?', f'Nas divulgações medidas pela Lectnex, o horário mais comum foi {hora} (Brasília). Confira sempre a agenda do dia: horários mudam com o horário de verão dos EUA.' if hora else 'Confira a agenda do dia no Mercado Hoje.'),
           (f'Como o mercado costuma reagir ao {nome}?', f'Em média, o Ibovespa à vista mexeu ±{aw:.2f}% e o dólar à vista ±{au:.2f}% depois do dado ({jan(rs)}), em {len(rs)} divulgações. Média não garante a próxima reação.'.replace('.', ',', 2) if aw is not None and au is not None else 'O histórico ainda é curto.'),
           (f'O que é o {nome}?', sobre or nome)]
    ld = [{'@type': 'Dataset', 'name': f'{nome}: reação do mercado brasileiro', 'description': desc, 'url': url, 'inLanguage': 'pt-BR', 'creator': {'@id': BASE + '#org'},
           'temporalCoverage': f'{min(r["data"] for r in rs)}/{max(r["data"] for r in rs)}', 'isAccessibleForFree': True},
          {'@type': 'FAQPage', 'mainEntity': [{'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in faq]}]
    prox_html = (f'<p class="mt-3 text-sm"><span class="term-label">Próxima divulgação</span> <strong>{br(dt.date.fromisoformat(prox["data"]), True)}{" às " + e(prox["hora"]) if prox.get("hora") else ""}</strong>'
                 f'{" · consenso " + e(prox["consenso"]) if prox.get("consenso") else ""} · <a href="index.html#cal-wrap" class="text-lect-teal hover:underline">agenda</a></p>') if prox else ''
    kpi = lambda rot, v, nota='': f'<div class="term-panel p-3"><span class="term-label block">{rot}</span><strong class="font-mono text-xl">{v}</strong>{nota}</div>'
    corpo = f'''
        <section class="border-b border-slate-300 dark:border-lect-borderDark grid-bg"><div class="max-w-5xl mx-auto px-4 sm:px-6 py-10">
            <span class="term-label text-lect-teal font-bold"><a href="dados/" class="hover:underline">DADOS ECONÔMICOS</a> · {e(fonte)}</span>
            <h1 class="font-display text-3xl font-bold tracking-tight mt-1">{e(nome)}: histórico e reação do mercado</h1>
            <p class="mt-2 text-sm text-slate-600 dark:text-slate-300 max-w-3xl">{e(sobre)}</p>
            {prox_html}
            <div class="mt-5 grid grid-cols-2 md:grid-cols-4 gap-3">{kpi('Divulgações medidas', len(rs))}{kpi('Ibovespa à vista (ref. WIN)', '±' + pct(aw)[1:] if aw is not None else '—', obs(nw, [r for r in rs if isinstance(r.get('win'), (int, float))]))}{kpi('Dólar à vista (ref. WDO)', '±' + pct(au)[1:] if au is not None else '—', obs(nu, [r for r in rs if isinstance(r.get('wdo'), (int, float))]))}{kpi('DI 2 anos · janela: o dia', '±' + bps(ad)[1:] if ad is not None else '—', f'<span class="block text-[10px] text-slate-600 dark:text-slate-400">{nd} obs</span>')}</div>
            <p class="mt-2 font-mono text-[11px] text-slate-500">Média do tamanho do movimento, para cima ou para baixo{f" · horário mais comum: {e(hora)}" if hora else ""}</p>
            {'<p class="mt-2 font-mono text-[11px] text-amber-700 dark:text-amber-400">Atenção: esta série mistura janelas de 30 min (desde set/2026) e de 1 h (divulgações anteriores, barras de 1 hora). A coluna Janela mostra a de cada linha.</p>' if mistura else ''}
        </div></section>
        <div class="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-6">
            {f'<div class="grid grid-cols-1 md:grid-cols-2 gap-3">{cond}</div>' if cond else ''}
            <section><h2 class="font-display font-bold text-lg mb-2">Todas as divulgações</h2>
            <div class="term-panel overflow-x-auto thin-scroll"><table class="w-full font-mono text-xs tabular-nums"><thead><tr class="text-[10px] text-slate-500 uppercase text-left">
            <th class="px-3 py-2">Data</th><th class="px-3 py-2">Saiu</th><th class="px-3 py-2">Consenso</th><th class="px-3 py-2">Surpresa</th><th class="px-3 py-2 text-right">Ibovespa à vista</th><th class="px-3 py-2 text-right">Dólar à vista</th><th class="px-3 py-2 text-right">DI 2a (dia)</th><th class="px-3 py-2">Janela{" (mista)" if mistura else ""}</th></tr></thead>
            <tbody>{linhas}</tbody></table></div>
            <p class="mt-2 text-[11px] text-slate-500">Ativo medido: Ibovespa à vista (referência para o WIN) e dólar à vista (referência para o WDO), não os contratos futuros; do último preço antes do dado até 30 minutos depois (antes de set/2026, até 1 hora depois, com barras de 1 hora). <span class="text-lect-orange">*</span> bolsa fechada na hora do dado: inclui o gap da abertura. DI: taxa prefixada de 2 anos do Tesouro Direto, da manhã do dia do dado à manhã do pregão seguinte. Consensos de fontes públicas; "s.d." = consenso não confirmado. <span class="lx-demo">ESTATÍSTICA · NÃO É RECOMENDAÇÃO</span></p></section>
            <div class="hidden" data-lx-news="chamada" data-titulo="Receba o {e(nome)} e a agenda do dia às 7h40, antes da abertura."></div>
            <section class="space-y-2"><h2 class="font-display font-bold text-lg">Perguntas frequentes</h2>{"".join(f'<details class="term-panel p-4"><summary class="font-semibold cursor-pointer">{e(q)}</summary><p class="mt-2 text-sm text-slate-600 dark:text-slate-300">{e(a)}</p></details>' for q, a in faq)}</section>
            <p class="text-[11px] text-slate-500">Conteúdo educacional. Reação passada não garante reação futura e nada aqui é recomendação de investimento.</p>
        </div>
'''
    return slug, url, head(titulo, desc, url, ld) + corpo + foot()


def indice(paginas):
    url = BASE + 'dados/'
    itens = ''.join(f'<a href="dados/{slug}.html" class="term-panel p-4 hover:border-lect-teal block"><strong class="font-display">{e(nome)}</strong><span class="block font-mono text-[11px] text-slate-500 mt-1">{n} divulgações medidas · Ibovespa à vista ±{pct(aw)[1:] if aw is not None else "—"} em 30 min</span></a>'
                    for slug, nome, n, aw in paginas)
    t = 'Dados econômicos: como o mercado reage a IPCA, payroll, CPI, Fed e Copom | Lectnex'
    d = 'Histórico das principais divulgações econômicas e a reação do mini índice, do mini dólar e dos juros a cada uma.'
    return head(t, d, url, [{'@type': 'CollectionPage', 'name': t, 'url': url, 'inLanguage': 'pt-BR'}]) + f'''
        <section class="border-b border-slate-300 dark:border-lect-borderDark grid-bg"><div class="max-w-5xl mx-auto px-4 sm:px-6 py-10">
            <span class="term-label text-lect-teal font-bold">DADOS ECONÔMICOS</span>
            <h1 class="font-display text-3xl font-bold tracking-tight mt-1">Como o mercado reage a cada dado</h1>
            <p class="mt-2 text-sm text-slate-600 dark:text-slate-300 max-w-3xl">{e(d)} Atualiza sozinho a cada divulgação.</p>
        </div></section>
        <div class="max-w-5xl mx-auto px-4 sm:px-6 py-8 grid grid-cols-1 md:grid-cols-2 gap-3">{itens}</div>
        <div class="max-w-5xl mx-auto px-4 sm:px-6 pb-8"><p class="text-[11px] text-slate-500">Veja também <a href="juros/" class="text-lect-teal hover:underline">Dias que mexeram nos juros</a> e a <a href="index.html#cal-wrap" class="text-lect-teal hover:underline">agenda da semana</a>. Conteúdo educacional, não é recomendação.</p></div>
''' + foot()


def main():
    regs = json.load(open('data/reacoes.json', encoding='utf-8'))['registros']
    try:
        cal = json.load(open('data/calendario.json', encoding='utf-8'))
    except Exception:
        cal = {}
    por = collections.defaultdict(list)
    for r in regs:
        por[r['tipo']].append(r)
    os.makedirs('dados', exist_ok=True)
    mudou, lista = [], []
    for tipo, rs in sorted(por.items(), key=lambda x: -len(x[1])):
        if len(rs) < MIN or tipo not in SOBRE:
            continue
        slug, url, html = pagina(tipo, rs, cal)
        arq = f'dados/{slug}.html'
        if not os.path.exists(arq) or open(arq, encoding='utf-8').read() != html:
            open(arq, 'w', encoding='utf-8').write(html)
            mudou.append(arq)
        lista.append((slug, SOBRE[tipo][0], len(rs), media(rs, 'win', absoluto=True)[0]))
    html = indice(lista)
    if not os.path.exists('dados/index.html') or open('dados/index.html', encoding='utf-8').read() != html:
        open('dados/index.html', 'w', encoding='utf-8').write(html)
        mudou.append('dados/index.html')
    sm = open('sitemap.xml', encoding='utf-8').read()
    hoje = dt.date.today().isoformat()
    for loc in [f'{BASE}dados/'] + [f'{BASE}dados/{s}.html' for s, *_ in lista]:
        if f'{loc}</loc>' not in sm:
            sm = sm.replace('</urlset>', f'  <url><loc>{loc}</loc><lastmod>{hoje}</lastmod><changefreq>weekly</changefreq><priority>0.6</priority></url>\n</urlset>')
    open('sitemap.xml', 'w', encoding='utf-8').write(sm)
    print(f'::notice::Páginas de dados: {len(lista)} dado(s), {len(mudou)} arquivo(s) atualizado(s)')
    print('PAGINAS=' + ' '.join(mudou))


if __name__ == '__main__':
    main()
