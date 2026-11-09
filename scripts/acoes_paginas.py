"""Páginas estáticas e indexáveis por ação: acoes/<ticker>.html + acoes/index.html.

Lê data/fundos-acoes.json (carteiras de fundos declaradas à CVM, licença ODbL) e gera uma página por ação com os
maiores fundos donos e quem aumentou ou reduziu a posição no mês. Atualiza o sitemap. Roda no workflow
"Coletor CVM" depois da coleta. As páginas só mudam quando o mês de referência muda (cerca de uma vez por mês).
Imprime na última linha as páginas alteradas (para o IndexNow)."""
import datetime as dt, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from semana import BASE, MESES, e, foot, head  # mesmo cabeçalho/rodapé das outras páginas geradas

MIN_FUNDOS = 10   # ação com poucos fundos não vira página (conteúdo raso)
IMG = BASE + 'assets/brand/og-acoes.jpg'

# Nome da empresa pelo prefixo do código. Só para título e texto; ação fora da lista aparece só pelo código.
NOMES = {
    'PETR': 'Petrobras', 'VALE': 'Vale', 'AXIA': 'Axia Energia (ex-Eletrobras)', 'VBBR': 'Vibra Energia', 'ITUB': 'Itaú Unibanco',
    'CMIG': 'Cemig', 'CSMG': 'Copasa', 'BBDC': 'Bradesco', 'EQTL': 'Equatorial', 'MDIA': 'M. Dias Branco', 'ENEV': 'Eneva',
    'BRAV': 'Brava Energia', 'SBSP': 'Sabesp', 'SUZB': 'Suzano', 'ITSA': 'Itaúsa', 'BBAS': 'Banco do Brasil', 'PRIO': 'PRIO',
    'CPLE': 'Copel', 'ALOS': 'Allos', 'EMBJ': 'Embraer', 'RDOR': "Rede D'Or", 'RENT': 'Localiza', 'RAIL': 'Rumo', 'LIGT': 'Light',
    'WEGE': 'WEG', 'SMFT': 'Smart Fit', 'CSAN': 'Cosan', 'TEND': 'Tenda', 'UGPA': 'Ultrapar', 'CBAV': 'CBA', 'BRAP': 'Bradespar',
    'DIRR': 'Direcional', 'ORVR': 'Orizon', 'ABEV': 'Ambev', 'MOTV': 'Motiva (ex-CCR)', 'GGBR': 'Gerdau', 'RADL': 'Raia Drogasil',
    'HYPE': 'Hypera', 'SEER': 'Ser Educacional', 'GOAU': 'Metalúrgica Gerdau', 'CXSE': 'Caixa Seguridade', 'CYRE': 'Cyrela',
    'ISAE': 'ISA Energia', 'BBSE': 'BB Seguridade', 'HAPV': 'Hapvida', 'CSED': 'Cruzeiro do Sul Educacional', 'LREN': 'Lojas Renner',
    'ALPK': 'Estapar', 'CURY': 'Cury', 'JHSF': 'JHSF', 'NATU': 'Natura', 'MULT': 'Multiplan', 'VIVT': 'Vivo (Telefônica Brasil)',
    'USIM': 'Usiminas', 'TOTS': 'TOTVS', 'DXCO': 'Dexco', 'EGIE': 'Engie Brasil', 'DASA': 'Dasa', 'TIMS': 'TIM', 'PSSA': 'Porto Seguro',
    'YDUQ': 'Yduqs', 'ASAI': 'Assaí', 'LOGG': 'Log CP', 'VIVA': 'Vivara', 'GGPS': 'GPS', 'COGN': 'Cogna', 'UNIP': 'Unipar',
    'ECOR': 'Ecorodovias', 'CLSC': 'Celesc', 'MILS': 'Mills', 'RECV': 'PetroRecôncavo', 'ARML': 'Armac', 'CPFE': 'CPFL Energia',
    'CEAB': 'C&A', 'MDNE': 'Moura Dubeux', 'DESK': 'Desktop', 'MRVE': 'MRV', 'CVCB': 'CVC', 'PRNR': 'Priner', 'SBFG': 'Grupo SBF',
    'MOVI': 'Movida', 'FLRY': 'Fleury', 'TTEN': '3tentos', 'EVEN': 'Even', 'SLCE': 'SLC Agrícola', 'CSNA': 'CSN', 'VLID': 'Valid',
    'POMO': 'Marcopolo', 'AURE': 'Auren', 'ABCB': 'Banco ABC Brasil', 'ALPA': 'Alpargatas', 'SIMH': 'Simpar', 'AMAR': 'Marisa',
    'BEEF': 'Minerva', 'BMOB': 'Bemobi', 'OPCT': 'OceanPact', 'IRBR': 'IRB Re', 'GMAT': 'Grupo Mateus', 'TFCO': 'Track & Field',
    'VTRU': 'Vitru', 'BIOM': 'Biomm', 'EZTC': 'EZTec', 'VULC': 'Vulcabras', 'VAMO': 'Vamos', 'GRND': 'Grendene', 'AGRO': 'BrasilAgro',
    'PNVL': 'Panvel', 'LWSA': 'LWSA (Locaweb)', 'SCAR': 'São Carlos', 'CMIN': 'CSN Mineração', 'SHUL': 'Schulz', 'AZZA': 'Azzas 2154',
    'RAPT': 'Randoncorp', 'ONCO': 'Oncoclínicas', 'LEVE': 'Mahle Metal Leve', 'SAPR': 'Sanepar', 'BRSR': 'Banrisul', 'TGMA': 'Tegma',
    'BMEB': 'Banco Mercantil', 'PINE': 'Banco Pine', 'BRKM': 'Braskem', 'CAML': 'Camil', 'ENGI': 'Energisa', 'PGMN': 'Pague Menos',
    'KLBN': 'Klabin', 'MYPK': 'Iochpe-Maxion', 'ESPA': 'Espaçolaser', 'MGLU': 'Magazine Luiza', 'COCE': 'Coelce', 'SMTO': 'São Martinho',
    'SOJA': 'Boa Safra', 'KEPL': 'Kepler Weber', 'CASH': 'Méliuz', 'PLPL': 'Plano & Plano', 'ETER': 'Eternit', 'ANIM': 'Ânima',
    'PFRM': 'Profarma', 'INTB': 'Intelbras', 'SANB': 'Santander Brasil', 'BPAC': 'BTG Pactual', 'BMGB': 'Banco BMG', 'RANI': 'Irani',
    'MEAL': 'IMC', 'PCAR': 'GPA (Pão de Açúcar)', 'FIQE': 'Unifique', 'MELK': 'Melnick', 'TUPY': 'Tupy', 'JSLG': 'JSL', 'ALUP': 'Alupar',
    'AZEV': 'Azevedo & Travassos', 'AALR': 'Alliar', 'HBSA': 'Hidrovias do Brasil', 'BLAU': 'Blau Farmacêutica', 'EUCA': 'Eucatex',
    'QUAL': 'Qualicorp', 'HBOR': 'Helbor', 'TAEE': 'Taesa', 'IGTI': 'Iguatemi', 'SYNE': 'Syn', 'CAMB': 'Cambuci', 'LAVV': 'Lavvi',
    'BRST': 'Brisanet', 'BHIA': 'Casas Bahia', 'MLAS': 'Multilaser', 'AZUL': 'Azul', 'TPIS': 'Triunfo', 'ENJU': 'Enjoei', 'FRAS': 'Fras-le',
    'VITT': 'Vittia', 'LOGN': 'Log-In', 'WIZC': 'Wiz', 'FESA': 'Ferbasa', 'POSI': 'Positivo', 'AMBP': 'Ambipar', 'HBRE': 'HBR Realty',
    'CSUD': 'CSU Digital', 'LJQQ': 'Quero-Quero', 'MATD': 'Mater Dei', 'ALLD': 'Allied', 'AMER': 'Americanas', 'RAIZ': 'Raízen',
    'VVEO': 'Viveo', 'JALL': 'Jalles Machado', 'PTBL': 'Portobello', 'AMOB': 'Automob', 'MTRE': 'Mitre', 'LPSB': 'Lopes', 'TASA': 'Taurus',
    'GFSA': 'Gafisa', 'B3SA': 'B3',
}
CLASSE = {'3': 'ON', '4': 'PN', '5': 'PNA', '6': 'PNB', '7': 'PNC', '8': 'PND', '11': 'unit'}


def n0(v):
    return f'{v:,.0f}'.replace(',', '.')


def grande(v):
    a = abs(v)
    for lim, div, um, varios in ((1e9, 1e9, ' bilhão', ' bilhões'), (1e6, 1e6, ' milhão', ' milhões'), (1e3, 1e3, ' mil', ' mil')):
        if a >= lim:
            return f'{v / div:.1f}'.replace('.', ',') + (varios if a / div >= 1.95 else um)
    return n0(v)


def pct(v, sinal=False):
    return (('+' if v > 0 else '') if sinal else '') + f'{v:.1f}'.replace('.', ',').replace('-', '−') + '%'


def mes_ano(ref):
    y, m = ref.split('-')
    return f'{MESES[int(m) - 1]} de {y}'


def nome(tk):
    return NOMES.get(tk[:4])


def rotulo(tk):
    """'Petrobras PN (PETR4)' ou só 'PETR4'."""
    nm = nome(tk)
    return f'{nm} {CLASSE.get(tk[4:], "")} ({tk})'.replace('  ', ' ') if nm else tk


def url(tk):
    return f'acoes/{tk.lower()}.html'


def tabela(titulo, linhas, cab):
    if not linhas:
        return ''
    return f'''<section class="term-panel overflow-hidden"><h2 class="px-5 py-3 border-b border-slate-200 dark:border-lect-borderDark font-display font-bold">{titulo}</h2>
            <div class="overflow-x-auto"><table class="w-full text-left text-xs tabular-nums"><thead class="quote-head uppercase font-mono"><tr>{"".join(f'<th class="py-2 px-3{" text-right" if i else ""}">{c}</th>' for i, c in enumerate(cab))}</tr></thead>
            <tbody class="divide-y divide-slate-100 dark:divide-lect-borderDark">{"".join(linhas)}</tbody></table></div></section>'''


def linha(i, fundo, *cols):
    return (f'<tr><td class="py-2 px-3"><span class="text-slate-400 font-mono mr-1">{i}.</span><span class="font-semibold">{e(fundo)}</span></td>'
            + ''.join(f'<td class="py-2 px-3 text-right font-mono whitespace-nowrap">{c}</td>' for c in cols) + '</tr>')


def pagina(tk, f, d, ordem):
    ref, prev = mes_ano(d['ref']), (mes_ano(d['prevRef']) if d.get('prevRef') else None)
    nm, rot = nome(tk), rotulo(tk)
    canon = BASE + url(tk)
    top = f['holders']
    top10 = sum(h['value'] for h in top)
    conc = top10 / f['value'] * 100 if f['value'] else 0
    dq = (f['qty'] / f['qtyPrev'] - 1) * 100 if f.get('qtyPrev') else None
    df = f['funds'] - f['fundsPrev'] if f.get('fundsPrev') else None
    titulo = f'{tk}: quais fundos têm {nm} na carteira' if nm else f'{tk}: quais fundos de investimento têm a ação na carteira'
    desc = (f'{n0(f["funds"])} fundos declararam {tk} à CVM em {ref}, somando R$ {grande(f["value"])}. '
            f'Veja os 10 maiores donos, quem aumentou e quem reduziu a posição no mês.')
    resumo = [f'Em <strong>{ref}</strong>, <strong>{n0(f["funds"])} fundos de investimento</strong> declararam {e(rot)} na carteira, somando <strong>{grande(f["qty"])} de ações</strong> e <strong>R$ {grande(f["value"])}</strong>.']
    if top:
        resumo.append(f'O maior detentor é o <strong>{e(top[0]["fund"])}</strong>, com R$ {grande(top[0]["value"])}. Os 10 maiores concentram {pct(conc)} do valor em fundos.')
    if dq is not None and prev:
        verbo = 'aumentou' if dq > 0.05 else 'caiu' if dq < -0.05 else 'ficou estável'
        resumo.append(f'Frente a {prev}, a quantidade total em fundos <strong>{verbo}{"" if verbo == "ficou estável" else " " + pct(abs(dq))}</strong>'
                      + (f' e o número de fundos passou de {n0(f["fundsPrev"])} para {n0(f["funds"])}.' if df else '.'))
    cards = [('Fundos donos', n0(f['funds']), (f'{"+" if df > 0 else "−" if df < 0 else ""}{n0(abs(df))} no mês' if df is not None else ref)),
             ('Valor em fundos', 'R$ ' + grande(f['value']), ref),
             ('Ações em fundos', grande(f['qty']), (pct(dq, True) + ' no mês' if dq is not None else ref)),
             ('Concentração top 10', pct(conc), 'do valor em fundos')]
    cards_html = ''.join(f'<div class="p-3 bg-slate-50 dark:bg-lect-bgDark border border-slate-200 dark:border-lect-borderDark"><span class="term-label block">{a}</span><strong class="block mt-0.5 font-mono">{b}</strong><span class="text-[10px] text-slate-500">{c}</span></div>' for a, b, c in cards)
    t1 = tabela(f'Os 10 maiores fundos donos de {tk}',
                [linha(i + 1, h['fund'], n0(h['qty']), 'R$ ' + grande(h['value']), pct(h['value'] / f['value'] * 100 if f['value'] else 0)) for i, h in enumerate(top)],
                ['Fundo', 'Ações', 'Valor', '% do total em fundos'])
    mov = lambda m: ('+' if m['delta'] > 0 else '−') + n0(abs(m['delta']))
    pos = lambda m: n0(m['qty']) if m['qty'] else 'sem posição declarada'
    t2 = tabela(f'Fundos que mais aumentaram a posição em {tk}', [linha(i + 1, m['fund'], f'<span class="text-emerald-600 dark:text-emerald-400">{mov(m)}</span>', pos(m)) for i, m in enumerate(f.get('buyers') or [])], ['Fundo', 'Variação no mês', 'Posição final'])
    t3 = tabela(f'Fundos que mais reduziram a posição em {tk}', [linha(i + 1, m['fund'], f'<span class="text-rose-600 dark:text-rose-400">{mov(m)}</span>', pos(m)) for i, m in enumerate(f.get('sellers') or [])], ['Fundo', 'Variação no mês', 'Posição final'])
    # links internos: outras classes da mesma empresa + vizinhas no ranking por valor
    irmas = [t for t in ordem if t[:4] == tk[:4] and t != tk]
    i = ordem.index(tk)
    viz = [t for t in ordem[max(0, i - 4):i + 5] if t != tk and t not in irmas]
    rel = ''.join(f'<a href="{url(t)}" class="px-2.5 py-1 border border-slate-300 dark:border-lect-borderDark hover:border-lect-teal font-mono text-xs">{t}</a>' for t in irmas + viz)
    ld = [{'@type': 'WebPage', 'name': titulo, 'description': desc, 'url': canon, 'inLanguage': 'pt-BR',
           'publisher': {'@id': BASE + '#org'}, 'primaryImageOfPage': IMG},
          {'@type': 'BreadcrumbList', 'itemListElement': [
              {'@type': 'ListItem', 'position': 1, 'name': 'Ações B3', 'item': BASE + 'acoes.html'},
              {'@type': 'ListItem', 'position': 2, 'name': 'Fundos donos de cada ação', 'item': BASE + 'acoes/'},
              {'@type': 'ListItem', 'position': 3, 'name': tk, 'item': canon}]}]
    return cabeca(titulo + ' | Lectnex', desc, canon, ld) + f'''
        <section class="border-b border-slate-300 dark:border-lect-borderDark grid-bg"><div class="max-w-4xl mx-auto px-4 sm:px-6 py-10">
            <nav class="font-mono text-[11px] text-slate-500"><a href="acoes.html" class="hover:text-lect-teal">Ações B3</a> / <a href="acoes/" class="hover:text-lect-teal">Fundos donos</a> / {tk}</nav>
            <span class="term-label text-lect-teal font-bold block mt-3">QUEM É DONO DA AÇÃO · CVM · {e(ref).upper()}</span>
            <h1 class="font-display text-2xl sm:text-3xl font-bold tracking-tight mt-1">{e(titulo)}</h1>
            <p class="mt-3 text-sm text-slate-600 dark:text-slate-300 leading-relaxed">{" ".join(resumo)}</p>
            <div class="mt-5 grid grid-cols-2 sm:grid-cols-4 gap-3">{cards_html}</div>
            <div class="mt-5 flex flex-wrap gap-2 font-mono text-xs">
                <a href="acoes.html?ticker={tk}" class="px-3.5 py-2 bg-lect-teal text-white font-semibold">Cotação, gráfico e opções de {tk} →</a>
                <a href="laboratorio.html?tab=proventos&amp;ticker={tk}" class="px-3.5 py-2 border border-slate-300 dark:border-lect-borderDark hover:border-lect-teal">Simular dividendos</a>
            </div>
        </div></section>
        <div class="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-5">
            {t1}
            {t2}
            {t3}
            <section class="term-panel p-5 text-sm text-slate-600 dark:text-slate-300 leading-relaxed space-y-2">
                <h2 class="font-display font-bold text-base text-lect-navy dark:text-white">Como ler estes números</h2>
                <p>Todo mês os fundos de investimento brasileiros entregam à CVM a composição da carteira. Esta página soma as posições em {tk} declaradas nesses documentos.</p>
                <p>O dado tem atraso: os fundos podem manter posições em sigilo por até 90 dias, então só entram meses que já estão completos na CVM. Por isso o mês de referência é {ref}. Serve para ver o posicionamento de médio prazo das gestoras, não o fluxo do dia.</p>
                <p>Aumentos e reduções comparam {ref} com {e(prev or "o mês anterior")} e consideram apenas fundos que declararam ações nos dois meses. "Sem posição declarada" significa que o fundo não informou {tk} no mês, o que normalmente indica venda total.</p>
                <p class="text-xs text-slate-500">Fonte: <a class="text-lect-teal underline" href="https://dados.cvm.gov.br/dataset/fi-doc-cda" target="_blank" rel="noopener">CVM, Composição e Diversificação das Aplicações (CDA)</a>, dados abertos sob licença ODbL. Não inclui pessoas físicas, estrangeiros fora de fundos locais, nem o controlador. Conteúdo educacional, não é recomendação de investimento.</p>
            </section>
            <section><h2 class="term-label font-bold mb-2">VEJA TAMBÉM OS FUNDOS DONOS DE</h2><div class="flex flex-wrap gap-1.5">{rel}<a href="acoes/" class="px-2.5 py-1 font-mono text-xs text-lect-teal hover:underline">todas as ações →</a></div></section>
            <div class="hidden" data-lx-news="chamada" data-titulo="Receba a leitura do mercado todo dia de manhã."></div>
        </div>
''' + foot()


def cabeca(titulo, desc, canon, ld):
    return (head(titulo, desc, canon, ld, IMG).replace('data-page="semana"', 'data-page="acoes"')
            .replace('scripts/semana.py', 'scripts/acoes_paginas.py').replace('content="article"', 'content="website"'))


def indice(d, ordem):
    t = d['tickers']
    canon = BASE + 'acoes/'
    ref = mes_ano(d['ref'])
    titulo = 'Quais fundos têm cada ação da B3 na carteira'
    desc = f'Fundos donos de {len(ordem)} ações da B3 segundo as carteiras declaradas à CVM em {ref}: maiores detentores, quem aumentou e quem reduziu a posição.'
    linhas = ''.join(f'''<tr><td class="py-2 px-3"><a href="{url(k)}" class="font-mono font-bold text-lect-teal hover:underline">{k}</a> <span class="text-slate-500">{e(nome(k) or "")}</span></td>
            <td class="py-2 px-3 text-right font-mono">{n0(t[k]["funds"])}</td><td class="py-2 px-3 text-right font-mono whitespace-nowrap">R$ {grande(t[k]["value"])}</td>
            <td class="py-2 px-3 hidden sm:table-cell text-slate-500">{e(t[k]["holders"][0]["fund"][:60]) if t[k]["holders"] else ""}</td></tr>''' for k in ordem)
    ld = [{'@type': 'CollectionPage', 'name': titulo, 'description': desc, 'url': canon, 'inLanguage': 'pt-BR'}]
    return cabeca(titulo + ' | Lectnex', desc, canon, ld) + f'''
        <section class="border-b border-slate-300 dark:border-lect-borderDark grid-bg"><div class="max-w-4xl mx-auto px-4 sm:px-6 py-10">
            <span class="term-label text-lect-teal font-bold">QUEM É DONO DA AÇÃO · CVM · {e(ref).upper()}</span>
            <h1 class="font-display text-3xl font-bold tracking-tight mt-1">{titulo}</h1>
            <p class="mt-2 text-sm text-slate-600 dark:text-slate-300 leading-relaxed">{len(ordem)} ações ordenadas pelo valor que os fundos brasileiros têm em carteira, segundo os documentos entregues à CVM. Clique em uma ação para ver os 10 maiores fundos donos e quem aumentou ou reduziu a posição no mês.</p>
        </div></section>
        <div class="max-w-4xl mx-auto px-4 sm:px-6 py-8">
            <div class="term-panel overflow-x-auto"><table class="w-full text-left text-xs tabular-nums"><thead class="quote-head uppercase font-mono"><tr><th class="py-2 px-3">Ação</th><th class="py-2 px-3 text-right">Fundos</th><th class="py-2 px-3 text-right">Valor em fundos</th><th class="py-2 px-3 hidden sm:table-cell">Maior detentor</th></tr></thead>
            <tbody class="divide-y divide-slate-100 dark:divide-lect-borderDark">{linhas}</tbody></table></div>
            <p class="mt-3 text-[11px] text-slate-500">Fonte: CVM (CDA), dados abertos sob licença ODbL. Mês de referência com atraso por causa do sigilo de até 90 dias. Conteúdo educacional, não é recomendação de investimento.</p>
        </div>
''' + foot()


def main():
    d = json.load(open('data/fundos-acoes.json', encoding='utf-8'))
    t = d['tickers']
    ordem = sorted((k for k, v in t.items() if v['funds'] >= MIN_FUNDOS and v['value'] > 0), key=lambda k: -t[k]['value'])
    os.makedirs('acoes', exist_ok=True)
    mudou = []

    def grava(arq, novo):
        velho = open(arq, encoding='utf-8').read() if os.path.exists(arq) else ''
        limpa = lambda s: re.sub(r'\?v=[0-9a-z]+', '', s)   # troca de versão do CSS não conta como mudança de conteúdo
        if limpa(novo) != limpa(velho):
            mudou.append(arq)
        if novo != velho:
            open(arq, 'w', encoding='utf-8').write(novo)

    for k in ordem:
        grava(url(k), pagina(k, t[k], d, ordem))
    grava('acoes/index.html', indice(d, ordem))
    # ação que saiu da lista: remove a página
    validas = {url(k) for k in ordem} | {'acoes/index.html'}
    for arq in os.listdir('acoes'):
        if arq.endswith('.html') and f'acoes/{arq}' not in validas:
            os.remove(f'acoes/{arq}')
    # sitemap: mantém a data das páginas que não mudaram
    sm = open('sitemap.xml', encoding='utf-8').read()
    datas = dict(re.findall(r'<loc>' + re.escape(BASE) + r'(acoes/[^<]*)</loc><lastmod>([^<]+)</lastmod>', sm))
    sm = re.sub(r'\s*<url><loc>[^<]*/acoes/[^<]*</loc>.*?</url>', '', sm)
    hoje = dt.date.today().isoformat()
    data = lambda arq, loc: hoje if arq in mudou else datas.get(loc, hoje)
    novas = f'\n\n  <url><loc>{BASE}acoes/</loc><lastmod>{data("acoes/index.html", "acoes/")}</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>'
    novas += ''.join(f'\n  <url><loc>{BASE}{url(k)}</loc><lastmod>{data(url(k), url(k))}</lastmod><changefreq>monthly</changefreq><priority>0.6</priority></url>' for k in ordem)
    open('sitemap.xml', 'w', encoding='utf-8').write(sm.replace('</urlset>', novas + '\n</urlset>'))
    print(f'::notice::Ações: {len(ordem)} página(s), referência {d["ref"]}; alteradas: {len(mudou)}')
    print('PAGINAS=' + ' '.join(mudou))


if __name__ == '__main__':
    main()
