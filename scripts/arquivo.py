"""Arquivo da Leitura do Dia: data/leitura/AAAA-MM-DD.json + leitura/AAAA-MM-DD.html + leitura/index.html (estáticos, indexáveis).
Na primeira execução recupera as edições antigas pelo histórico do git. Atualiza o sitemap. Última linha: PAGINAS=... (IndexNow)."""
import datetime as dt, glob, json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(__file__))
from semana import head, foot, e, BASE, br  # mesmo cabeçalho/rodapé das páginas semanais

TERM = {'bullish': ('▲ Comprador', 'text-emerald-600 dark:text-emerald-400'), 'bearish': ('▼ Vendedor', 'text-rose-600 dark:text-rose-400'), 'neutro': ('● Neutro', 'text-slate-500')}
SETA = {'alta': '▲', 'baixa': '▼', 'neutro': '●', 'volatil': '↕'}
DIAS = ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo']


def valida(d):
    return isinstance(d, dict) and d.get('data') and isinstance(d.get('resumo'), list) and d['resumo']


def recuperar():
    """Pega a última versão de cada dia no histórico do git e a versão atual."""
    edicoes = {}
    try:
        shas = subprocess.run(['git', 'log', '--format=%H', '--reverse', '--', 'data/leitura.json'], capture_output=True, text=True).stdout.split()
    except Exception:
        shas = []
    for s in shas:
        try:
            d = json.loads(subprocess.run(['git', 'show', f'{s}:data/leitura.json'], capture_output=True, text=True, check=True).stdout)
            if valida(d): edicoes[d['data']] = d
        except Exception:
            pass
    try:
        d = json.load(open('data/leitura.json', encoding='utf-8'))
        if valida(d): edicoes[d['data']] = d
    except Exception:
        pass
    return edicoes


def pagina(d, datas):
    dia = dt.date.fromisoformat(d['data'])
    url = f'{BASE}leitura/{d["data"]}.html'
    titulo = f'Leitura do Dia {br(dia, True)}: {d.get("titulo", "")}'
    desc = (' '.join(d['resumo']))[:155].rsplit(' ', 1)[0] + '…'
    sem = d.get('tipo') == 'sem-pregao'
    resumo = ''.join(f'<li class="flex gap-2"><span class="text-lect-orange">■</span><span>{e(x)}</span></li>' for x in d['resumo'])
    if d.get('termometro'):
        bloco = '<div class="grid grid-cols-2 gap-3">' + ''.join(f'<div class="term-panel p-4"><span class="term-label">{k.upper()}</span><strong class="block font-mono text-lg {TERM.get(v.get("leitura"), TERM["neutro"])[1]}">{TERM.get(v.get("leitura"), TERM["neutro"])[0]}</strong><p class="text-xs text-slate-500 mt-1">{e(v.get("motivo"))}</p></div>' for k, v in d['termometro'].items() if k in ('win', 'wdo')) + '</div>'
    elif d.get('proximo_pregao'):
        p = d['proximo_pregao']; pd = dt.date.fromisoformat(p['data'])
        bloco = f'<div class="term-panel p-4 border-l-4 border-l-lect-orange"><span class="term-label">Sem pregão · próximo pregão {DIAS[pd.weekday()]} {br(pd)}</span><p class="text-sm mt-1">{e(p.get("o_que_esperar"))}</p></div>'
    else:
        bloco = ''
    agenda = ''.join(f'<li><strong class="font-mono text-xs text-lect-teal">{e(x.get("hora"))}</strong> {e(x.get("evento"))}<span class="block text-xs text-slate-500">{e(x.get("por_que"))}</span></li>' for x in d.get('destaques', []))
    ext = ''.join(f'<li class="flex justify-between font-mono text-xs"><span>{e(x.get("ativo"))}</span><strong>{e(x.get("variacao"))}</strong></li>' for x in d.get('exterior', []))
    news = ''.join(f'''<article class="term-panel p-4"><span class="font-mono text-[10px] text-slate-500">{e(n.get("fonte"))}{" · " + e(n.get("hora")) if n.get("hora") else ""}</span>
        <h3 class="font-semibold leading-snug mt-1"><a href="{e(n.get("url"))}" target="_blank" rel="noopener nofollow" class="hover:text-lect-teal">{e(n.get("titulo"))}</a></h3>
        <p class="text-xs text-slate-600 dark:text-slate-300 mt-1">{e(n.get("por_que"))}</p>
        <div class="mt-2 flex gap-1 font-mono text-[10px]">{"".join(f'<span class="px-1 border">{k.upper()} {SETA.get(v, "")}</span>' for k, v in (n.get("impacto") or {}).items() if v in SETA)}</div></article>''' for n in d.get('noticias', []))
    def cartoes(lista):
        return ''.join(f'''<article class="term-panel p-4"><span class="font-mono text-[10px] text-slate-500">{e(n.get("fonte"))}{" · " + e(n.get("hora")) if n.get("hora") else ""}</span>
        <h3 class="font-semibold leading-snug mt-1"><a href="{e(n.get("url"))}" target="_blank" rel="noopener nofollow" class="hover:text-lect-teal">{e(n.get("titulo"))}</a></h3>
        <p class="text-xs text-slate-600 dark:text-slate-300 mt-1">{e(n.get("por_que"))}</p></article>''' for n in lista if n.get('titulo'))
    upd = ''.join(f'''<section><h2 class="font-display font-bold text-lg mb-1">Atualização das {e(u.get("hora"))}</h2>{f'<p class="text-sm text-slate-600 dark:text-slate-300 mb-3">{e(u.get("resumo"))}</p>' if u.get("resumo") else ''}<div class="grid grid-cols-1 md:grid-cols-2 gap-3">{cartoes(u.get("noticias") or [])}</div></section>''' for u in reversed(d.get('atualizacoes') or []) if u.get('noticias'))
    fontes = ' · '.join(f'<a href="{e(f.get("url"))}" target="_blank" rel="noopener nofollow" class="underline decoration-dotted hover:text-lect-teal">{e(f.get("titulo") or f.get("url"))}</a>' for f in d.get('fontes', []))
    i = datas.index(d['data']); ant = datas[i - 1] if i > 0 else None; prox = datas[i + 1] if i + 1 < len(datas) else None
    nav = f'''<nav class="flex justify-between gap-3 font-mono text-xs">{f'<a href="leitura/{ant}.html" class="hover:text-lect-teal">← {br(dt.date.fromisoformat(ant))}</a>' if ant else '<span></span>'}<a href="leitura/" class="hover:text-lect-teal">todas as edições</a>{f'<a href="leitura/{prox}.html" class="hover:text-lect-teal">{br(dt.date.fromisoformat(prox))} →</a>' if prox else '<span></span>'}</nav>'''
    ld = [{'@type': 'Article', 'headline': titulo[:110], 'description': desc, 'url': url, 'inLanguage': 'pt-BR', 'datePublished': d.get('gerado_em') or d['data'],
           'dateModified': d.get('gerado_em') or d['data'], 'author': {'@id': BASE + '#org'}, 'publisher': {'@id': BASE + '#org'}, 'image': BASE + 'assets/brand/og-mercado.jpg'}]
    img = f'{BASE}assets/og/leitura-{d["data"]}.jpg' if os.path.exists(f'assets/og/leitura-{d["data"]}.jpg') else None
    if img: ld[0]['image'] = img
    return head(titulo + ' | Lectnex', desc, url, ld, img) + f'''
        <section class="border-b border-slate-300 dark:border-lect-borderDark grid-bg"><div class="max-w-4xl mx-auto px-4 sm:px-6 py-10">
            <span class="term-label text-lect-teal font-bold">LEITURA DO DIA · {DIAS[dia.weekday()].upper()} {br(dia, True)}{" · SEM PREGÃO" if sem else ""}</span>
            <h1 class="font-display text-2xl sm:text-3xl font-bold tracking-tight mt-1">{e(d.get("titulo"))}</h1>
            <ul class="mt-4 space-y-2 text-sm text-slate-700 dark:text-slate-300 leading-relaxed">{resumo}</ul>
        </div></section>
        <div class="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-6">
            {nav}
            {bloco}
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                {f'<section class="term-panel p-4"><h2 class="term-label font-bold mb-2">Agenda</h2><ul class="space-y-2 text-sm">{agenda}</ul></section>' if agenda else ''}
                {f'<section class="term-panel p-4"><h2 class="term-label font-bold mb-2">Exterior e mercado</h2><ul class="space-y-1.5">{ext}</ul></section>' if ext else ''}
            </div>
            {upd}
            {f'<section><h2 class="font-display font-bold text-lg mb-3">Notícias que importaram</h2><div class="grid grid-cols-1 md:grid-cols-2 gap-3">{news}</div></section>' if news else ''}
            <p class="text-[11px] text-slate-500">Fontes: {fontes}</p>
            <div class="hidden" data-lx-news="chamada" data-titulo="Receba a Leitura do Dia todo dia às 7h40."></div>
            {nav}
            <p class="text-[11px] text-slate-500">Gerado com IA (Claude) a partir de fontes públicas, pode conter imprecisões. Conteúdo educacional, não é recomendação de investimento. <a href="index.html" class="text-lect-teal hover:underline">Leitura de hoje no Mercado Hoje →</a></p>
        </div>
''' + foot()


def indice(edicoes, datas):
    url = BASE + 'leitura/'
    titulo = 'Arquivo da Leitura do Dia: o que moveu WIN, WDO e DI | Lectnex'
    desc = 'Todas as edições da Leitura do Dia do Lectnex: resumo do mercado, termômetro de mini índice e mini dólar, agenda e notícias de cada pregão.'
    itens = ''.join(f'''<li><a href="leitura/{dd}.html" class="flex items-center justify-between gap-3 term-panel p-4 hover:border-lect-teal"><span><span class="font-mono text-[11px] text-slate-500">{DIAS[dt.date.fromisoformat(dd).weekday()]} {br(dt.date.fromisoformat(dd), True)}</span><strong class="block font-display">{e(edicoes[dd].get("titulo"))}</strong></span><i class="ph-bold ph-arrow-right text-lect-teal"></i></a></li>''' for dd in reversed(datas))
    return head(titulo, desc, url, [{'@type': 'CollectionPage', 'name': titulo, 'url': url, 'inLanguage': 'pt-BR'}]) + f'''
        <section class="border-b border-slate-300 dark:border-lect-borderDark grid-bg"><div class="max-w-4xl mx-auto px-4 sm:px-6 py-10">
            <span class="term-label text-lect-teal font-bold">ARQUIVO</span><h1 class="font-display text-3xl font-bold tracking-tight mt-1">Leitura do Dia: todas as edições</h1>
            <p class="mt-2 text-sm text-slate-600 dark:text-slate-300">O resumo de cada dia para quem opera mini índice, mini dólar e juros.</p></div></section>
        <div class="max-w-4xl mx-auto px-4 sm:px-6 py-8"><ul class="space-y-3">{itens}</ul></div>
''' + foot()


def main():
    edicoes = {}
    for f in glob.glob('data/leitura/*.json'):
        try:
            d = json.load(open(f, encoding='utf-8'))
            if valida(d): edicoes[d['data']] = d
        except Exception:
            pass
    edicoes.update(recuperar())  # a versão mais nova de cada dia vence
    for dd, d in edicoes.items():
        arq = f'data/leitura/{dd}.json'
        if not os.path.exists(arq) or json.load(open(arq, encoding='utf-8')) != d:
            json.dump(d, open(arq, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    datas = sorted(edicoes)
    mudou = []
    for dd in datas:
        out = f'leitura/{dd}.html'; novo = pagina(edicoes[dd], datas)
        if not os.path.exists(out) or open(out, encoding='utf-8').read() != novo:
            open(out, 'w', encoding='utf-8').write(novo); mudou.append(out)
    ix = indice(edicoes, datas)
    if not os.path.exists('leitura/index.html') or open('leitura/index.html', encoding='utf-8').read() != ix:
        open('leitura/index.html', 'w', encoding='utf-8').write(ix); mudou.append('leitura/index.html')
    sm = open('sitemap.xml', encoding='utf-8').read()
    sm = re.sub(r'\s*<url><loc>[^<]*/leitura/[^<]*</loc>.*?</url>', '', sm)
    novas = ''.join(f'\n  <url><loc>{BASE}leitura/{dd}.html</loc><lastmod>{dd}</lastmod><changefreq>monthly</changefreq><priority>0.5</priority></url>' for dd in datas)
    novas += f'\n  <url><loc>{BASE}leitura/</loc><lastmod>{datas[-1] if datas else dt.date.today().isoformat()}</lastmod><changefreq>daily</changefreq><priority>0.6</priority></url>'
    open('sitemap.xml', 'w', encoding='utf-8').write(sm.replace('</urlset>', novas + '\n</urlset>'))
    print(f'::notice::Arquivo: {len(datas)} edição(ões); alteradas: {", ".join(mudou) or "nenhuma"}')
    print('PAGINAS=' + ' '.join(mudou))


if __name__ == '__main__':
    main()
