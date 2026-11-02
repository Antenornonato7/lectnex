"""Páginas semanais indexáveis da agenda econômica (semana/AAAA-MM-DD.html + semana/index.html).

Lê data/calendario.json, acumula cada semana em data/semana/AAAA-MM-DD.json (para não perder os dias que já
passaram e os resultados que saíram) e gera HTML estático. Atualiza o sitemap. Roda no workflow "Semana".
Imprime na última linha as páginas alteradas (para o IndexNow)."""
import datetime as dt, glob, html, json, os, re

BASE = 'https://lectnex.com.br/'
FLAG = {'BR': '🇧🇷', 'US': '🇺🇸', 'CN': '🇨🇳', 'EU': '🇪🇺', 'JP': '🇯🇵', 'UK': '🇬🇧'}
PAIS = {'BR': 'Brasil', 'US': 'EUA', 'CN': 'China', 'EU': 'Zona do euro', 'JP': 'Japão', 'UK': 'Reino Unido'}
SETA = {'alta': '▲', 'baixa': '▼', 'volatil': '↕', 'neutro': '●'}
DIAS = ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo']
MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
# palavra no nome do evento → verbete do glossário
GLOSS = [('payroll', 'payroll'), ('copom', 'copom'), ('ipca', 'ipca'), ('cpi', 'cpi'), ('fomc', 'fomc'), ('fed', 'fomc'), ('focus', 'focus'), ('vencimento', 'rolagem'), ('desemprego', 'payroll')]
e = lambda s: html.escape(str(s if s is not None else ''), quote=True)


def chave(ev):
    return f"{ev.get('data')}|{ev.get('hora')}|{ev.get('evento')}"


def segunda(d):
    return d - dt.timedelta(days=d.weekday())


def br(d, ano=False):
    return d.strftime('%d/%m/%Y' if ano else '%d/%m')


def ver():
    return re.search(r'tailwind\.css\?v=([0-9a-z]+)', open('index.html', encoding='utf-8').read()).group(1)


def head(titulo, desc, url, extra_ld, img=None):
    img = img or BASE + 'assets/brand/og-mercado.jpg'
    v = ver()
    ld = {'@context': 'https://schema.org', '@graph': [{'@type': 'Organization', '@id': BASE + '#org', 'name': 'Lectnex', 'url': BASE, 'logo': BASE + 'assets/brand/icon-512.png'}] + extra_ld}
    return f'''<!DOCTYPE html>
<html lang="pt-BR" class="scroll-smooth">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <base href="../">
    <title>{e(titulo)}</title>
    <meta name="description" content="{e(desc)}">
    <link rel="canonical" href="{url}">
    <meta name="theme-color" content="#060D17">
    <link rel="icon" href="assets/brand/favicon.svg" type="image/svg+xml">
    <link rel="apple-touch-icon" href="assets/brand/apple-touch-icon.png">
    <link rel="manifest" href="manifest.webmanifest">
    <meta property="og:type" content="article">
    <meta property="og:site_name" content="Lectnex Terminal">
    <meta property="og:locale" content="pt_BR">
    <meta property="og:title" content="{e(titulo)}">
    <meta property="og:description" content="{e(desc)}">
    <meta property="og:url" content="{url}">
    <meta property="og:image" content="{img}">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:image" content="{img}">
    <script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
    <script>try{{if(localStorage.getItem('lectnex-theme')!=='light')document.documentElement.classList.add('dark');if(localStorage.getItem('lectnex-hc')==='1')document.documentElement.classList.add('lx-hc')}}catch(e){{document.documentElement.classList.add('dark')}}</script>
    <link rel="stylesheet" href="assets/tailwind.css?v={v}">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Space+Grotesk:wght@600;700&display=swap" rel="stylesheet" media="print" onload="this.media='all'">
    <link rel="stylesheet" href="assets/icons/phosphor.css?v={v}">
    <link rel="stylesheet" href="assets/lectnex.css?v={v}">
</head>
<body data-page="semana" class="bg-[#F4F6F9] text-lect-navy dark:bg-lect-bgDark dark:text-slate-100 font-sans antialiased selection:bg-lect-teal selection:text-white">
    <!-- Gerado por scripts/semana.py. Não edite à mão. -->
    <div id="lx-topbar"></div>
    <header id="lx-header"></header>
    <main>'''


def foot():
    return f'''    </main>
    <div id="lx-footer"></div>
    <script src="assets/lectnex-core.js?v={ver()}"></script>
</body>
</html>
'''


def link_gloss(nome):
    n = nome.lower()
    for k, s in GLOSS:
        if k in n:
            return f'glossario.html#{s}'
    return None


def pagina(seg, evs, semanas):
    fim = seg + dt.timedelta(days=4)
    url = f'{BASE}semana/{seg.isoformat()}.html'
    altos = [x for x in evs if (x.get('importancia') or 1) >= 3]
    surp = [x for x in evs if x.get('surpresa') and x['surpresa'].get('direcao') in ('acima', 'abaixo') and x.get('resultado')]
    mes = MESES[seg.month - 1]
    titulo = f'Agenda econômica da semana de {br(seg)} a {br(fim, True)}: o que move WIN, WDO e DI'
    nomes = ', '.join(x['evento'].split(' (')[0] for x in altos[:4])
    desc = f'Calendário econômico de {br(seg)} a {br(fim)} de {mes} de {seg.year} com horários de Brasília, consenso e resultados: {nomes}. Impacto em mini índice, mini dólar e juros.'
    hoje = dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).date()
    estado = 'Semana em andamento' if seg <= hoje <= seg + dt.timedelta(days=6) else ('Semana encerrada' if hoje > seg + dt.timedelta(days=6) else 'Próxima semana')
    # resumo
    linhas = [f'<strong>{len(evs)} eventos</strong> no radar, <strong>{len(altos)} de alto impacto</strong>.']
    if altos:
        linhas.append('Destaques: ' + '; '.join(f'{DIAS[dt.date.fromisoformat(x["data"]).weekday()]} {e(x.get("hora") or "")} — {e(x["evento"])}' for x in altos[:5]) + '.')
    if surp:
        linhas.append(f'<strong>{len(surp)} surpresa(s)</strong> em relação ao consenso: ' + '; '.join(f'{e(x["evento"])} ({e(x["resultado"])} vs {e(x.get("consenso") or "—")})' for x in surp) + '.')
    corpo = []
    for i in range(7):
        d = seg + dt.timedelta(days=i)
        dia = sorted([x for x in evs if x['data'] == d.isoformat()], key=lambda x: x.get('hora') or '')
        if not dia:
            continue
        itens = []
        for x in dia:
            imp = max(1, min(3, x.get('importancia') or 1))
            tags = ' '.join(f'<span class="px-1 border text-[10px] font-bold">{k.upper()} {SETA[v]}</span>' for k, v in (x.get('impacto') or {}).items() if v in SETA)
            nums = ' · '.join(f'{lbl} <strong>{e(x[k])}</strong>' for k, lbl in (('anterior', 'anterior'), ('consenso', 'consenso'), ('resultado', 'resultado')) if x.get(k) not in (None, ''))
            s = x.get('surpresa')
            sp = f'<p class="mt-1 text-xs"><span class="px-1 mr-1 font-mono text-[10px] font-bold bg-lect-orange text-lect-navy">SURPRESA {"▲" if s["direcao"] == "acima" else "▼"}</span>{e(s.get("reacao") or "")}</p>' if s and s.get('direcao') in ('acima', 'abaixo') and x.get('resultado') else ''
            gl = link_gloss(x['evento'])
            itens.append(f'''<li class="py-3 flex gap-3"><span class="w-12 shrink-0 font-mono text-xs font-bold text-lect-teal">{e(x.get("hora") or "dia")}</span><div class="min-w-0">
                <h3 class="font-semibold leading-snug">{FLAG.get(x.get("pais"), "")} {e(x["evento"])} <span class="font-mono text-[10px] text-lect-orange" title="importância {imp} de 3">{"●" * imp}</span> <span class="sr-only">{PAIS.get(x.get("pais"), "")}</span></h3>
                {f'<p class="text-xs text-slate-500 mt-0.5">{e(x["nota"])}</p>' if x.get('nota') else ''}
                <div class="mt-1 flex flex-wrap gap-x-3 gap-y-1 font-mono text-[11px] text-slate-600 dark:text-slate-300">{nums}{(" " + tags) if tags else ""}{f' <a href="{gl}" class="text-lect-teal hover:underline">o que é?</a>' if gl else ''}</div>{sp}</div></li>''')
        corpo.append(f'''<section class="term-panel"><h2 class="px-5 py-3 border-b border-slate-200 dark:border-lect-borderDark font-display font-bold capitalize">{DIAS[d.weekday()]}, {br(d)}</h2><ul class="px-5 divide-y divide-slate-100 dark:divide-lect-borderDark">{"".join(itens)}</ul></section>''')
    idx = semanas.index(seg)
    ant = semanas[idx - 1] if idx > 0 else None
    prox = semanas[idx + 1] if idx + 1 < len(semanas) else None
    nav = f'''<nav class="flex justify-between gap-3 font-mono text-xs">{f'<a href="semana/{ant.isoformat()}.html" class="hover:text-lect-teal">← semana de {br(ant)}</a>' if ant else '<span></span>'}<a href="semana/" class="hover:text-lect-teal">todas as semanas</a>{f'<a href="semana/{prox.isoformat()}.html" class="hover:text-lect-teal">semana de {br(prox)} →</a>' if prox else '<span></span>'}</nav>'''
    ld = [{'@type': 'Article', 'headline': titulo, 'description': desc, 'url': url, 'inLanguage': 'pt-BR', 'datePublished': (seg - dt.timedelta(days=2)).isoformat(),
           'dateModified': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'), 'author': {'@id': BASE + '#org'}, 'publisher': {'@id': BASE + '#org'}, 'image': BASE + 'assets/brand/og-mercado.jpg'}]
    return head(titulo + ' | Lectnex', desc, url, ld) + f'''
        <section class="border-b border-slate-300 dark:border-lect-borderDark grid-bg"><div class="max-w-4xl mx-auto px-4 sm:px-6 py-10">
            <span class="term-label text-lect-teal font-bold">AGENDA ECONÔMICA · {estado.upper()}</span>
            <h1 class="font-display text-2xl sm:text-3xl font-bold tracking-tight mt-1">{e(titulo)}</h1>
            <p class="mt-3 text-sm text-slate-600 dark:text-slate-300 leading-relaxed">{" ".join(linhas)}</p>
            <p class="mt-2 text-xs text-slate-500">Horários de Brasília. ●●● = alto impacto. Setas: direção típica do preço (↕ depende do resultado). <a href="index.html#cal-wrap" class="text-lect-teal hover:underline">Calendário ao vivo no Mercado Hoje →</a></p>
        </div></section>
        <div class="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-4">
            {nav}
            {"".join(corpo)}
            <div class="hidden" data-lx-news="chamada" data-titulo="Receba a agenda e os resultados todo dia de manhã."></div>
            {nav}
            <p class="text-[11px] text-slate-500">Curadoria com apoio de IA a partir de fontes públicas; confira os números na fonte oficial. Conteúdo educacional, não é recomendação de investimento.</p>
        </div>
''' + foot()


def indice(semanas, dados):
    url = BASE + 'semana/'
    titulo = 'Agenda econômica semanal para WIN, WDO e DI | Lectnex'
    desc = 'Arquivo semanal do calendário econômico com horários de Brasília, consenso, resultados e surpresas que movem o mini índice, o mini dólar e os juros.'
    itens = ''.join(f'''<li><a href="semana/{s.isoformat()}.html" class="flex items-center justify-between gap-3 term-panel p-4 hover:border-lect-teal"><span><strong class="font-display">Semana de {br(s)} a {br(s + dt.timedelta(days=4), True)}</strong><span class="block text-xs text-slate-500 mt-0.5">{e(", ".join(x["evento"].split(" (")[0] for x in dados[s] if (x.get("importancia") or 1) >= 3)[:120])}</span></span><i class="ph-bold ph-arrow-right text-lect-teal"></i></a></li>''' for s in reversed(semanas))
    return head(titulo, desc, url, [{'@type': 'CollectionPage', 'name': titulo, 'url': url, 'inLanguage': 'pt-BR'}]) + f'''
        <section class="border-b border-slate-300 dark:border-lect-borderDark grid-bg"><div class="max-w-4xl mx-auto px-4 sm:px-6 py-10">
            <span class="term-label text-lect-teal font-bold">ARQUIVO</span><h1 class="font-display text-3xl font-bold tracking-tight mt-1">Agenda econômica da semana</h1>
            <p class="mt-2 text-sm text-slate-600 dark:text-slate-300">O que movimenta o WIN, o WDO e o DI em cada semana: horários, consenso, resultados e surpresas.</p></div></section>
        <div class="max-w-4xl mx-auto px-4 sm:px-6 py-8"><ul class="space-y-3">{itens}</ul></div>
''' + foot()


def main():
    cal = json.load(open('data/calendario.json', encoding='utf-8'))
    por_semana = {}
    for ev in cal.get('eventos', []):
        try:
            por_semana.setdefault(segunda(dt.date.fromisoformat(ev['data'])), []).append(ev)
        except (KeyError, ValueError):
            continue
    mudou = []
    for seg, evs in por_semana.items():
        arq = f'data/semana/{seg.isoformat()}.json'
        try:
            antigo = json.load(open(arq, encoding='utf-8'))
        except Exception:
            antigo = {'eventos': []}
        m = {chave(x): x for x in antigo['eventos']}
        for x in evs:
            m[chave(x)] = {**m.get(chave(x), {}), **{k: v for k, v in x.items() if v not in (None, '')}}
        # dias futuros: o calendário atual manda (remove eventos que saíram da agenda)
        hoje = dt.date.today().isoformat()
        atuais = {chave(x) for x in evs}
        novo = sorted([x for k, x in m.items() if k in atuais or x['data'] < hoje], key=lambda x: (x['data'], x.get('hora') or ''))
        if novo != antigo['eventos']:
            json.dump({'semana': seg.isoformat(), 'eventos': novo}, open(arq, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    dados = {}
    for f in sorted(glob.glob('data/semana/*.json')):
        s = dt.date.fromisoformat(os.path.basename(f)[:-5])
        dados[s] = json.load(open(f, encoding='utf-8'))['eventos']
    semanas = sorted(s for s in dados if len(dados[s]) >= 4)  # semana com poucos eventos não vira página (conteúdo raso)
    for s in semanas:
        out = f'semana/{s.isoformat()}.html'
        novo = pagina(s, dados[s], semanas)
        velho = open(out, encoding='utf-8').read() if os.path.exists(out) else ''
        if re.sub(r'"dateModified": "[^"]+"', '', novo) != re.sub(r'"dateModified": "[^"]+"', '', velho):
            open(out, 'w', encoding='utf-8').write(novo); mudou.append(out)
    ix = indice(semanas, dados)
    if not os.path.exists('semana/index.html') or open('semana/index.html', encoding='utf-8').read() != ix:
        open('semana/index.html', 'w', encoding='utf-8').write(ix); mudou.append('semana/index.html')
    # sitemap
    sm = open('sitemap.xml', encoding='utf-8').read()
    sm = re.sub(r'\s*<url><loc>[^<]*/semana/[^<]*</loc>.*?</url>', '', sm)
    hoje = dt.date.today().isoformat()
    novas = ''.join(f'\n  <url><loc>{BASE}semana/{s.isoformat()}.html</loc><lastmod>{hoje}</lastmod><changefreq>daily</changefreq><priority>0.6</priority></url>' for s in semanas)
    novas += f'\n  <url><loc>{BASE}semana/</loc><lastmod>{hoje}</lastmod><changefreq>weekly</changefreq><priority>0.5</priority></url>'
    sm = sm.replace('</urlset>', novas + '\n</urlset>')
    open('sitemap.xml', 'w', encoding='utf-8').write(sm)
    print(f'::notice::Semana: {len(semanas)} semana(s); alteradas: {", ".join(mudou) or "nenhuma"}')
    print('PAGINAS=' + ' '.join(mudou))


if __name__ == '__main__':
    main()
