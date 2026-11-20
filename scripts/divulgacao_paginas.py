"""Página de cada divulgação: dados/<tipo>-<AAAA-MM-DD>.html (ex.: dados/ipca-2026-11-10.html).

"IPCA de outubro: saiu X, consenso Y, como o mercado reagiu" — gerada sozinha assim que a reação é medida
(workflow "Reação aos dados") e completada com o DI no dia seguinte (workflow da curva).
Quando o pregão daquele dia está gravado em data/dias/, mostra o gráfico do Ibovespa e do dólar em volta do horário.
Mantém só as últimas 12 divulgações de cada dado (páginas antigas continuam no ar, só saem da lista).
Última linha: PAGINAS=... (IndexNow).
"""
import datetime as dt
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from semana import head, foot, e, BASE, br  # noqa: E402
from dados_paginas import SOBRE, SLUG, pct, bps, cor  # noqa: E402

POR_TIPO = 12
MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
ABREV = {m[:3]: m for m in MESES}


def nome_do_evento(r, nome):
    """'IPCA (out)' → 'IPCA de outubro'; sem mês entre parênteses, o nome do dado."""
    ev = r.get('evento', '')
    mm = re.search(r'\bde (' + '|'.join(MESES) + r')\b', ev)
    if mm:
        return f'{nome} de {mm.group(1)}'
    m = re.search(r'\((\w{3})[\w.]*\)', ev)
    if m and m.group(1).lower() in ABREV:
        return f'{nome} de {ABREV[m.group(1).lower()]}'
    return nome


def minutos(h):
    m = re.match(r'(\d{1,2})[h:](\d{2})?', h or '')
    return int(m.group(1)) * 60 + int(m.group(2) or 0) if m else None


def grafico(dia, hora):
    """SVG com Ibovespa e dólar (variação % desde 1 h antes do dado), linha vertical no horário."""
    try:
        d = json.load(open(f'data/dias/{dia}.json', encoding='utf-8'))
    except Exception:
        return ''
    t0 = minutos(hora)
    if t0 is None:
        return ''
    W, H, L, R, T, B = 760, 260, 46, 14, 16, 26
    series = []
    for k, rot, corl in (('ibov', 'Ibovespa (WIN)', '#00B4A2'), ('dolar', 'Dólar (WDO)', '#F39200')):
        pts = [(minutos(p[0]), p[1]) for p in (d.get(k) or {}).get('pontos', []) if minutos(p[0]) is not None]
        pts = [p for p in pts if t0 - 60 <= p[0] <= t0 + 120]
        if len(pts) < 4:
            continue
        ref = next((v for m, v in reversed(pts) if m <= t0), pts[0][1])
        series.append((rot, corl, [(m, (v / ref - 1) * 100) for m, v in pts]))
    if not series:
        return ''
    xs = [m for _, _, s in series for m, _ in s]
    ys = [v for _, _, s in series for _, v in s] + [0]
    x0, x1 = min(xs), max(xs)
    ylo, yhi = min(ys), max(ys)
    pad = max(0.05, (yhi - ylo) * 0.15)
    ylo, yhi = ylo - pad, yhi + pad
    X = lambda m: L + (m - x0) / max(1, x1 - x0) * (W - L - R)
    Y = lambda v: T + (yhi - v) / (yhi - ylo) * (H - T - B)
    s = f'<svg viewBox="0 0 {W} {H}" class="w-full h-auto font-mono" role="img" aria-label="Ibovespa e dólar em volta da divulgação">'
    s += f'<line x1="{L}" x2="{W - R}" y1="{Y(0):.1f}" y2="{Y(0):.1f}" class="stroke-slate-300 dark:stroke-slate-600" stroke-dasharray="3 3"/>'
    for v in (ylo + pad, yhi - pad):
        s += f'<text x="{L - 6}" y="{Y(v) + 3:.1f}" text-anchor="end" font-size="10" class="fill-slate-400">{pct(v)}</text>'
    if x0 <= t0 <= x1:
        s += f'<line x1="{X(t0):.1f}" x2="{X(t0):.1f}" y1="{T}" y2="{H - B}" stroke="#94A3B8" stroke-width="1.5"/><text x="{X(t0) + 4:.1f}" y="{T + 10}" font-size="10" class="fill-slate-500">{e(hora)} divulgação</text>'
    for m in range(x0 - x0 % 30 + 30, x1 + 1, 60):
        s += f'<text x="{X(m):.1f}" y="{H - 8}" text-anchor="middle" font-size="10" class="fill-slate-400">{m // 60:02d}h{m % 60:02d}</text>'
    for rot, corl, pts in series:
        s += f'<polyline fill="none" stroke="{corl}" stroke-width="2.2" stroke-linejoin="round" points="{" ".join(f"{X(m):.1f},{Y(v):.1f}" for m, v in pts)}"/>'
    s += '</svg>'
    leg = ' '.join(f'<span class="inline-flex items-center gap-1.5"><span class="w-3 h-0.5 inline-block" style="background:{c}"></span>{e(r)}</span>' for r, c, _ in series)
    return (f'<section class="term-panel p-4"><div class="flex flex-wrap items-baseline justify-between gap-2"><h2 class="font-display font-bold">O preço em volta do dado</h2>'
            f'<span class="font-mono text-[11px] text-slate-500 flex gap-4">{leg}</span></div><div class="mt-2">{s}</div>'
            f'<p class="mt-1 text-[11px] text-slate-500">Variação desde o último preço antes do dado, barras de 5 minutos (Yahoo Finance, Ibovespa e dólar à vista).{" O Ibovespa só começa a negociar às 10h: a linha dele parte da abertura." if any(r.startswith("Ibov") and pts[0][0] > t0 for r, _, pts in series) else ""} Notícia perto de um movimento não prova que ela o causou.</p></section>')


def pagina(r, nome, tipo, outras):
    slug = f'{SLUG.get(tipo, tipo)}-{r["data"]}'
    url = f'{BASE}dados/{slug}.html'
    dia = dt.date.fromisoformat(r['data'])
    evento = nome_do_evento(r, nome)
    sup = r.get('surpresa')
    sup_txt = {'acima': 'veio acima do consenso', 'abaixo': 'veio abaixo do consenso'}.get(sup, 'veio em linha com o consenso' if r.get('consenso') else 'sem consenso confirmado')
    titulo = f'{evento} ({br(dia, True)}): saiu {r.get("resultado") or "—"}' + (f', consenso {r["consenso"]}' if r.get('consenso') else '') + ' | Lectnex'
    desc = f'{evento} divulgado em {br(dia, True)}{" às " + r["hora"] if r.get("hora") else ""}: saiu {r.get("resultado") or "—"}' + \
           (f' contra consenso de {r["consenso"]}' if r.get('consenso') else '') + '. Veja como o mini índice, o mini dólar e os juros reagiram.'
    kpi = lambda rot, v, c='': f'<div class="term-panel p-3"><span class="term-label block">{rot}</span><strong class="font-mono text-xl {c}">{v}</strong></div>'
    janela = '1 hora' if r.get('janela') == '1h' else '30 min'
    lista = ''.join(f'<li><a href="dados/{SLUG.get(tipo, tipo)}-{o["data"]}.html" class="hover:text-lect-teal">{br(dt.date.fromisoformat(o["data"]), True)}</a> · saiu {e(o.get("resultado") or "—")}'
                    f' · Ibovespa à vista <span class="{cor(o.get("win"))}">{pct(o.get("win"))}</span></li>' for o in outras if o['data'] != r['data'])[:4000]
    ld = [{'@type': 'NewsArticle', 'headline': titulo.replace(' | Lectnex', ''), 'datePublished': f'{r["data"]}T{(r.get("hora") or "09h").replace("h", ":")[:5].ljust(5, "0")}:00-03:00',
           'dateModified': dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).isoformat(timespec='seconds'), 'url': url, 'inLanguage': 'pt-BR',
           'author': {'@id': BASE + '#org'}, 'publisher': {'@id': BASE + '#org'}, 'description': desc}]
    corpo = f'''
        <section class="border-b border-slate-300 dark:border-lect-borderDark grid-bg"><div class="max-w-4xl mx-auto px-4 sm:px-6 py-10">
            <span class="term-label text-lect-teal font-bold"><a href="dados/" class="hover:underline">DADOS</a> · <a href="dados/{SLUG.get(tipo, tipo)}.html" class="hover:underline">{e(nome.upper())}</a></span>
            <h1 class="font-display text-3xl font-bold tracking-tight mt-1">{e(evento)}: saiu {e(r.get("resultado") or "—")}</h1>
            <p class="mt-2 text-sm text-slate-600 dark:text-slate-300">Divulgado em {DIAS_SEMANA[dia.weekday()]}, {br(dia, True)}{" às " + e(r["hora"]) + " (Brasília)" if r.get("hora") else ""}. O resultado {sup_txt}{" (" + e(r["consenso"]) + ")" if r.get("consenso") else ""}.</p>
            <div class="mt-5 grid grid-cols-2 md:grid-cols-4 gap-3">
                {kpi("Saiu", e(r.get("resultado") or "—"))}{kpi("Consenso", e(r.get("consenso") or "—"), "text-slate-500")}
                {kpi(f"Ibovespa à vista em {janela} · 1 obs", pct(r.get("win")) + ("*" if r.get("win_abertura") else ""), cor(r.get("win")))}{kpi(f"Dólar à vista em {janela} · 1 obs", pct(r.get("wdo")), cor(r.get("wdo")))}
            </div>
            <p class="mt-2 font-mono text-[11px] text-slate-500">DI de 2 anos no dia: <strong class="{cor(r.get("di_bps"), True)}">{bps(r.get("di_bps")) if "di_bps" in r and r.get("di_bps") is not None else (r.get("di_obs") or "medido no pregão seguinte")}</strong>{" · * bolsa fechada na hora do dado: inclui o gap da abertura" if r.get("win_abertura") else ""}</p>
        </div></section>
        <div class="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-6">
            {grafico(r["data"], r.get("hora"))}
            <section class="term-panel p-4"><h2 class="font-display font-bold">Divulgações anteriores</h2><ul class="mt-2 space-y-1 font-mono text-xs">{lista}</ul>
            <p class="mt-2 text-xs"><a href="dados/{SLUG.get(tipo, tipo)}.html" class="font-bold text-lect-teal hover:underline">Histórico completo e médias do {e(nome)} →</a></p></section>
            <div class="hidden" data-lx-news="chamada" data-titulo="Receba a agenda e os resultados dos dados às 7h40, antes da abertura."></div>
            <p class="text-[11px] text-slate-500">Ativo medido: Ibovespa à vista (referência para o WIN) e dólar à vista (referência para o WDO), não os contratos futuros; do último preço antes do dado até {janela} depois. DI: taxa prefixada de 2 anos do Tesouro Direto, da manhã do dia à manhã do pregão seguinte. Consenso de fontes públicas. Conteúdo educacional, não é recomendação de investimento. <span class="lx-demo">ESTATÍSTICA · NÃO É RECOMENDAÇÃO</span></p>
        </div>
'''
    img = None
    try:  # imagem do resultado: prévia ao compartilhar e anexo dos posts
        from divulgacao_imagem import gerar as gerar_img, PASTA
        if not os.path.exists(os.path.join(PASTA, f'{slug}.jpg')) or os.environ.get('REFAZER_IMAGENS'):
            gerar_img(r, evento, slug)
        img = f'{BASE}assets/og/dados/{slug}.jpg'
    except Exception as ex:
        print(f'::warning::Imagem de {slug}: {ex}')
    return slug, url, head(titulo, desc, url, ld, img) + corpo + foot()


DIAS_SEMANA = ['segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado', 'domingo']


def main():
    regs = json.load(open('data/reacoes.json', encoding='utf-8'))['registros']
    os.makedirs('dados', exist_ok=True)
    mudou, locs, novas = [], [], []
    for tipo, (nome, _, _) in SOBRE.items():
        rs = sorted([r for r in regs if r.get('tipo') == tipo], key=lambda r: r['data'], reverse=True)[:POR_TIPO]
        for r in rs:
            slug, url, html = pagina(r, nome, tipo, rs)
            arq = f'dados/{slug}.html'
            locs.append((url, r['data']))
            nova = not os.path.exists(arq)
            if nova and (dt.date.today() - dt.date.fromisoformat(r['data'])).days <= 3:
                novas.append({'evento': nome_do_evento(r, nome), 'url': url, 'resultado': r.get('resultado'), 'consenso': r.get('consenso'),
                              'surpresa': r.get('surpresa'), 'win': r.get('win'), 'wdo': r.get('wdo'), 'janela': '1 h' if r.get('janela') == '1h' else '30 min',
                              'win_abertura': r.get('win_abertura'), 'imagem': f'assets/og/dados/{SLUG.get(tipo, tipo)}-{r["data"]}.jpg'})
            if not os.path.exists(arq) or re.sub(r'"dateModified": "[^"]+"', '', open(arq, encoding='utf-8').read()) != re.sub(r'"dateModified": "[^"]+"', '', html):
                open(arq, 'w', encoding='utf-8').write(html)
                mudou.append(arq)
    sm = open('sitemap.xml', encoding='utf-8').read()
    for loc, d in locs:
        if f'{loc}</loc>' not in sm:
            sm = sm.replace('</urlset>', f'  <url><loc>{loc}</loc><lastmod>{d}</lastmod><changefreq>monthly</changefreq><priority>0.5</priority></url>\n</urlset>')
    open('sitemap.xml', 'w', encoding='utf-8').write(sm)
    if novas:  # para o post automático (scripts/postar_divulgacao.py), depois que a página estiver no ar
        json.dump(novas, open(os.path.join(os.environ.get('RUNNER_TEMP', '.'), 'novas-divulgacoes.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'::notice::Páginas de divulgação: {len(locs)} no ar, {len(mudou)} atualizada(s), {len(novas)} nova(s) para postar')
    print('PAGINAS=' + ' '.join(mudou))


if __name__ == '__main__':
    main()
