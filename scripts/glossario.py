"""Gera glossario.html (estático, indexável) a partir de data/glossario.json.
Rode: python3 scripts/glossario.py   (o HTML sai pronto para o Google: conteúdo no próprio arquivo, JSON-LD DefinedTermSet)."""
import html, json, re, unicodedata

BASE = 'https://lectnex.com.br/'
d = json.load(open('data/glossario.json', encoding='utf-8'))
CAT = d['categorias']
termos = sorted(d['termos'], key=lambda x: unicodedata.normalize('NFD', x['t'].lower()))
e = lambda s: html.escape(s, quote=True)


def slug(s):
    s = unicodedata.normalize('NFD', s.lower()).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def letra(t):
    return unicodedata.normalize('NFD', t[0].upper())[0]


ver = re.search(r'tailwind\.css\?v=([0-9a-z]+)', open('index.html', encoding='utf-8').read()).group(1)
titulo = 'Glossário do Trader: termos de juros, futuros, ações e risco | Lectnex'
desc = f'{len(termos)} termos do mercado financeiro explicados em português simples: breakeven, curva de juros, ajuste diário, rolagem, payroll, Kelly e mais, com links para ferramentas ao vivo.'
ld = {'@context': 'https://schema.org', '@graph': [
    {'@type': 'Organization', '@id': BASE + '#org', 'name': 'Lectnex', 'url': BASE, 'logo': BASE + 'assets/brand/icon-512.png'},
    {'@type': 'DefinedTermSet', '@id': BASE + 'glossario.html#set', 'name': 'Glossário do Trader Lectnex', 'url': BASE + 'glossario.html', 'inLanguage': 'pt-BR',
     'hasDefinedTerm': [{'@type': 'DefinedTerm', 'name': x['t'], 'description': x['d'], 'url': BASE + 'glossario.html#' + slug(x['t']), 'inDefinedTermSet': BASE + 'glossario.html#set'} for x in termos]}]}

letras = sorted({letra(x['t']) for x in termos})
artigos = []
for x in termos:
    s = slug(x['t'])
    tool = f'<a href="{e(x["f"][1])}" class="inline-flex items-center gap-1.5 mt-3 font-mono text-[11px] font-bold text-lect-teal hover:underline"><i class="ph-bold ph-arrow-square-out"></i>Ver na prática: {e(x["f"][0])}</a>' if x.get('f') else ''
    artigos.append(f'''        <article id="{s}" data-cat="{x['c']}" data-q="{e(unicodedata.normalize('NFD', (x['t'] + ' ' + x['d']).lower()).encode('ascii', 'ignore').decode())}" class="gl-item term-panel p-5 scroll-mt-28">
            <div class="flex items-start justify-between gap-3"><h2 class="font-display text-lg font-bold leading-snug"><a href="#{s}" class="hover:text-lect-teal">{e(x['t'])}</a></h2><span class="shrink-0 px-2 py-0.5 font-mono text-[10px] bg-slate-100 dark:bg-lect-bgDark text-slate-500">{e(CAT[x['c']])}</span></div>
            <p class="mt-2 text-sm text-slate-600 dark:text-slate-300 leading-relaxed">{e(x['d'])}</p>{tool}
        </article>''')

pagina = f'''<!DOCTYPE html>
<html lang="pt-BR" class="scroll-smooth">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{e(titulo)}</title>
    <meta name="description" content="{e(desc)}">
    <link rel="canonical" href="{BASE}glossario.html">
    <meta name="theme-color" content="#060D17">
    <link rel="icon" href="assets/brand/favicon.svg" type="image/svg+xml">
    <link rel="icon" href="assets/brand/favicon-32.png" sizes="32x32" type="image/png">
    <link rel="apple-touch-icon" href="assets/brand/apple-touch-icon.png">
    <link rel="manifest" href="manifest.webmanifest">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-title" content="Lectnex">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta property="og:type" content="website">
    <meta property="og:site_name" content="Lectnex Terminal">
    <meta property="og:locale" content="pt_BR">
    <meta property="og:title" content="{e(titulo)}">
    <meta property="og:description" content="{e(desc)}">
    <meta property="og:url" content="{BASE}glossario.html">
    <meta property="og:image" content="{BASE}assets/brand/og-academia.jpg">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{e(titulo)}">
    <meta name="twitter:description" content="{e(desc)}">
    <meta name="twitter:image" content="{BASE}assets/brand/og-academia.jpg">
    <script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
    <script>try{{if(localStorage.getItem('lectnex-theme')!=='light')document.documentElement.classList.add('dark');if(localStorage.getItem('lectnex-hc')==='1')document.documentElement.classList.add('lx-hc')}}catch(e){{document.documentElement.classList.add('dark')}}</script>
    <link rel="stylesheet" href="assets/tailwind.css?v={ver}">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Space+Grotesk:wght@600;700&display=swap" rel="stylesheet" media="print" onload="this.media='all'">
    <noscript><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Space+Grotesk:wght@600;700&display=swap" rel="stylesheet"></noscript>
    <link rel="stylesheet" href="assets/icons/phosphor.css?v={ver}">
    <link rel="stylesheet" href="assets/lectnex.css?v={ver}">
</head>
<body data-page="glossario" class="bg-[#F4F6F9] text-lect-navy dark:bg-lect-bgDark dark:text-slate-100 font-sans antialiased selection:bg-lect-teal selection:text-white">
    <!-- Gerado por scripts/glossario.py a partir de data/glossario.json. Não edite à mão. -->
    <div id="lx-topbar"></div>
    <header id="lx-header"></header>
    <main>
        <section class="border-b border-slate-300 dark:border-lect-borderDark grid-bg">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
                <span class="term-label text-lect-teal font-bold">ACADEMIA LECTNEX · {len(termos)} TERMOS</span>
                <h1 class="font-display text-3xl sm:text-4xl font-bold tracking-tight mt-1">Glossário do Trader</h1>
                <p class="text-sm text-slate-600 dark:text-slate-300 mt-2 max-w-3xl leading-relaxed">Os termos que aparecem na Leitura do Dia, no calendário e nas ferramentas, explicados em português simples, com link para ver cada conceito funcionando com dados de hoje.</p>
                <div class="mt-5 flex flex-col gap-2 max-w-3xl">
                    <label class="sr-only" for="gl-q">Buscar termo</label>
                    <input id="gl-q" type="search" placeholder="Buscar: breakeven, rolagem, payroll…" class="lx-input flex-1 !text-sm" autocomplete="off">
                    <div class="flex flex-wrap gap-1 font-mono text-[11px]" id="gl-cats"><button type="button" data-c="" class="px-2.5 py-1.5 bg-lect-navy text-white dark:bg-lect-teal font-bold">Todos</button>{''.join(f'<button type="button" data-c="{k}" class="px-2.5 py-1.5 bg-white dark:bg-lect-cardDark border border-slate-200 dark:border-lect-borderDark hover:text-lect-teal">{e(v)}</button>' for k, v in CAT.items())}</div>
                </div>
                <nav class="mt-4 flex flex-wrap gap-1 font-mono text-xs" aria-label="Letras">{''.join(f'<a href="#{slug(next(x["t"] for x in termos if letra(x["t"]) == L))}" class="w-7 h-7 inline-flex items-center justify-center border border-slate-200 dark:border-lect-borderDark hover:text-lect-teal hover:border-lect-teal">{L}</a>' for L in letras)}</nav>
            </div>
        </section>
        <section class="py-8">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <p id="gl-none" class="hidden text-sm text-slate-500 mb-4">Nenhum termo encontrado. Sugira um em contato@lectnex.com.br.</p>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
{chr(10).join(artigos)}
                </div>
                <div class="hidden mt-10" data-lx-news="chamada" data-titulo="Aprendeu um termo novo? Veja ele no mercado todo dia."></div>
                <p class="mt-6 text-[11px] text-slate-500">Conteúdo educacional. Não é recomendação de investimento. Regras de tributação de 2026; confirme sempre com a Receita Federal ou seu contador.</p>
            </div>
        </section>
    </main>
    <div id="lx-footer"></div>
    <script src="assets/lectnex-core.js?v={ver}"></script>
    <script>
    (function () {{
        const q = document.getElementById('gl-q'), items = [...document.querySelectorAll('.gl-item')], none = document.getElementById('gl-none');
        let cat = '';
        const norm = s => s.normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase();
        function filtrar() {{
            const t = norm(q.value.trim()); let n = 0;
            items.forEach(a => {{ const ok = (!cat || a.dataset.cat === cat) && (!t || a.dataset.q.includes(t)); a.classList.toggle('hidden', !ok); n += ok; }});
            none.classList.toggle('hidden', n > 0);
        }}
        q.addEventListener('input', filtrar);
        document.querySelectorAll('#gl-cats [data-c]').forEach(b => b.onclick = () => {{
            cat = b.dataset.c;
            document.querySelectorAll('#gl-cats [data-c]').forEach(x => x.className = 'px-2.5 py-1.5 ' + (x === b ? 'bg-lect-navy text-white dark:bg-lect-teal font-bold' : 'bg-white dark:bg-lect-cardDark border border-slate-200 dark:border-lect-borderDark hover:text-lect-teal'));
            filtrar();
        }});
        if (location.hash) {{ const el = document.getElementById(location.hash.slice(1)); if (el) el.classList.add('ring-2', 'ring-lect-orange'); }}
    }})();
    </script>
</body>
</html>
'''
open('glossario.html', 'w', encoding='utf-8').write(pagina)
print(f'glossario.html: {len(termos)} termos')
