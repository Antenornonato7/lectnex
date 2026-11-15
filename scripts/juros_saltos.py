"""Dias que mexeram nos juros: juros/index.html (estática, indexável) + data/juros-saltos.json (histórico que nunca encolhe).

Fonte dos saltos: data/curva.json (curva prefixada do Tesouro, taxas da manhã). O coletor (coletor/curva.py) marca os dias
em que a curva andou >= 0,75 p.p. em média e procura a manchete que provavelmente explica o dia. Eventos conhecidos
(eleições, IPCA) têm o motivo escrito à mão em FIXOS, com a fonte, e vencem o automático.
Roda depois do coletor da curva. Atualiza o sitemap. Última linha: PAGINAS=... (IndexNow).
"""
import datetime as dt, json, os, re, sys

sys.path.insert(0, os.path.dirname(__file__))
from semana import head, foot, e, BASE, br  # mesmo cabeçalho/rodapé das páginas estáticas

ARQ, SAIDA = 'data/juros-saltos.json', 'juros/index.html'
MINIMO = 0.75  # p.p. em média num dia
DIAS = ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo']
MES3 = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
FIXOS = {
    '2026-10-05': {'rotulo': 'Eleição · 1º turno', 'motivo': 'Juros despencam mais de 1 p.p. com o resultado do 1º turno da eleição presidencial.',
                   'fonte': 'DGABC', 'url': 'https://www.dgabc.com.br/Noticia/4351084/taxas-de-juros-tem-rali-e-despencam-mais-de-1-p-p-com-flavio-a-frente-no-1-turno'},
    '2026-10-26': {'rotulo': 'Eleição · 2º turno', 'motivo': 'Juros disparam após a reeleição no 2º turno: o mercado reprecifica o risco fiscal e a chance de novos cortes da Selic.',
                   'fonte': 'InvestNews', 'url': 'https://investnews.com.br/investimentos/taxas-do-tesouro-direto-disparam-prefixado-vai-a-quase-16-e-ipca-passa-de-8/'},
}


def bps(v):
    return ('+' if v > 0 else '−' if v < 0 else '') + f'{abs(round(v * 100)):.0f} bps'


def nome_venc(v):
    return f'{MES3[int(v[5:7]) - 1].capitalize()}/{v[2:4]}'


def detectar(curva):
    """Saltos presentes na janela atual da curva (30 pregões), com a variação de cada vencimento."""
    hist, achados = curva.get('historico', {}), {}
    ds = sorted(hist)
    for a, b in zip(ds, ds[1:]):
        ant = {p['venc']: p['taxa'] for p in hist[a].get('pre', [])}
        mov = {p['venc']: round(p['taxa'] - ant[p['venc']], 2) for p in hist[b].get('pre', []) if p['venc'] in ant}
        if not mov:
            continue
        media = sum(mov.values()) / len(mov)
        if abs(media) >= MINIMO:
            achados[b] = {'data': b, 'anterior': a, 'media_pp': round(media, 2), 'vertices': mov,
                          'nivel': {p['venc']: p['taxa'] for p in hist[b].get('pre', [])}}
    for ev in curva.get('eventos', []) or []:  # motivo automático do coletor
        if ev.get('data') in achados and ev.get('motivo'):
            achados[ev['data']].update({k: ev.get(k) for k in ('rotulo', 'motivo', 'fonte', 'url', 'hora')}, origem='automático')
    return achados


def juntar():
    try:
        salvo = json.load(open(ARQ, encoding='utf-8'))
    except Exception:
        salvo = {'dias': {}}
    try:
        curva = json.load(open('data/curva.json', encoding='utf-8'))
    except Exception:
        curva = {}
    dias = salvo.get('dias', {})
    for d, novo in detectar(curva).items():
        velho = dias.get(d, {})
        # mantém um motivo já encontrado se o novo vier sem; o fixo (escrito à mão) sempre vence
        if velho.get('motivo') and not novo.get('motivo'):
            novo.update({k: velho.get(k) for k in ('rotulo', 'motivo', 'fonte', 'url', 'hora', 'origem')})
        dias[d] = {**velho, **novo}
    for d, f in FIXOS.items():
        if d in dias:
            dias[d].update(f, origem='editorial')
    return {'atualizado_em': dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).isoformat(timespec='seconds'), 'minimo_pp': MINIMO, 'dias': dict(sorted(dias.items()))}


def cartao(s):
    dia = dt.date.fromisoformat(s['data'])
    m, sobe = s['media_pp'], s['media_pp'] > 0
    top = sorted(s.get('vertices', {}).items(), key=lambda x: -abs(x[1]))[:3]
    cor = 'text-rose-600 dark:text-rose-400' if sobe else 'text-emerald-600 dark:text-emerald-400'
    verts = ''.join(f'<li class="flex justify-between gap-3"><span>{nome_venc(v)}</span><strong class="{cor}">{bps(x)}</strong></li>' for v, x in top)
    if s.get('motivo'):
        prov = f'Motivo provável, pela manchete das {e(s.get("hora"))} · ' if s.get('origem') == 'automático' and s.get('hora') else ''
        fonte = (f'<a href="{e(s.get("url"))}" target="_blank" rel="noopener nofollow" class="underline decoration-dotted hover:text-lect-teal">{e(s.get("fonte") or "fonte")}</a>'
                 if s.get('url') else e(s.get('fonte') or ''))
        motivo = f'<p class="mt-2 text-sm leading-relaxed">{e(s["motivo"])}</p><p class="mt-1 font-mono text-[11px] text-slate-500">{prov}{fonte}</p>'
    else:
        motivo = '<p class="mt-2 text-sm text-slate-500">Salto forte sem manchete guardada que explique o dia.</p>'
    return f'''<article id="d-{s['data']}" class="term-panel p-5 border-l-4 {'border-l-rose-500' if sobe else 'border-l-emerald-500'} scroll-mt-28">
        <div class="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <h2 class="font-display text-lg font-bold">{DIAS[dia.weekday()].capitalize()}, {br(dia, True)}{f' · {e(s.get("rotulo"))}' if s.get('rotulo') and s.get('motivo') else ''}</h2>
            <strong class="font-mono text-xl {cor}">{bps(m)} <span class="text-xs font-normal text-slate-500">em média · {'juros subiram' if sobe else 'juros caíram'}</span></strong>
        </div>
        {motivo}
        <div class="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div><span class="term-label block mb-1">Vencimentos que mais andaram</span><ul class="font-mono space-y-0.5">{verts}</ul></div>
            <div class="text-slate-600 dark:text-slate-300 leading-relaxed"><span class="term-label block mb-1">No pregão</span>{'Juros subindo pesam no <strong>WIN</strong> (varejo, construção, small caps) e costumam apoiar o <strong>WDO</strong>.' if sobe else 'Juros caindo costumam aliviar o <strong>WIN</strong> e pesar no <strong>WDO</strong>.'} <span class="lx-demo">REAÇÃO TÍPICA</span></div>
        </div>
    </article>'''


def pagina(dados):
    url = BASE + 'juros/'
    saltos = sorted(dados['dias'].values(), key=lambda s: s['data'], reverse=True)
    titulo = 'Dias que mexeram nos juros: por que a curva disparou ou despencou | Lectnex'
    desc = ('Cada dia em que os juros futuros (curva prefixada) andaram mais de 0,75 ponto num só pregão, com quanto subiram ou caíram, '
            'os vencimentos que mais andaram e o motivo do dia.')
    ult = saltos[0] if saltos else None
    destaque = (f'<p class="mt-3 text-sm"><span class="term-label">Último salto</span> <a href="juros/#d-{ult["data"]}" class="font-semibold hover:text-lect-teal">'
                f'{br(dt.date.fromisoformat(ult["data"]), True)}: {bps(ult["media_pp"])} em média</a></p>') if ult else ''
    lista = ''.join(cartao(s) for s in saltos) or '<p class="text-sm text-slate-500">Nenhum salto forte registrado ainda.</p>'
    faq = [('Por que os juros dispararam hoje?', 'Quando a curva anda mais de 0,75 ponto num só dia, o motivo costuma ser eleição, decisão do Copom, inflação acima do esperado ou notícia fiscal. Esta página registra cada um desses dias com a manchete que explica o movimento.'),
           ('Juros subindo é ruim para a bolsa?', 'Em geral, juros futuros em alta pesam no Ibovespa e no mini índice (WIN), principalmente varejo, construção e small caps, e costumam fortalecer o dólar (WDO). Não é regra fixa.'),
           ('De onde vêm os números?', 'Da curva prefixada pública do Tesouro Direto (taxas da manhã divulgadas pelo Tesouro Nacional). A curva DI da B3 é parecida, mas não idêntica.')]
    ld = [{'@type': 'CollectionPage', 'name': titulo, 'url': url, 'inLanguage': 'pt-BR', 'dateModified': dados.get('atualizado_em'),
           'about': 'juros futuros, curva de juros, DI, Tesouro Prefixado'},
          {'@type': 'FAQPage', 'mainEntity': [{'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in faq]}]
    faq_html = ''.join(f'<details class="term-panel p-4"><summary class="font-semibold cursor-pointer">{e(q)}</summary><p class="mt-2 text-sm text-slate-600 dark:text-slate-300">{e(a)}</p></details>' for q, a in faq)
    return head(titulo, desc, url, ld) + f'''
        <section class="border-b border-slate-300 dark:border-lect-borderDark grid-bg"><div class="max-w-4xl mx-auto px-4 sm:px-6 py-10">
            <span class="term-label text-lect-teal font-bold">JUROS · MACRO</span>
            <h1 class="font-display text-3xl font-bold tracking-tight mt-1">Dias que mexeram nos juros</h1>
            <p class="mt-2 text-sm text-slate-600 dark:text-slate-300 max-w-2xl">Cada pregão em que a curva de juros prefixada andou mais de {str(MINIMO).replace('.', ',')} ponto em média num dia só: quanto andou, quais vencimentos se mexeram mais e o motivo. Atualiza sozinho.</p>
            {destaque}
            <p class="mt-3 font-mono text-[11px]"><a href="macro.html#ct-wrap" class="text-lect-teal hover:underline">Ver a curva de hoje e a linha do tempo →</a></p>
        </div></section>
        <div class="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-4">
            {lista}
            <div class="hidden" data-lx-news="chamada" data-titulo="Receba a Leitura do Dia às 7h40, com juros, dólar e bolsa."></div>
            <section class="pt-4 space-y-2"><h2 class="font-display font-bold text-lg">Perguntas frequentes</h2>{faq_html}</section>
            <p class="text-[11px] text-slate-500">Fonte das taxas: Tesouro Nacional (Tesouro Direto, taxas da manhã de títulos prefixados). O motivo marcado como "provável" vem da manchete de maior relação com juros publicada naquele dia; notícia perto de um movimento não prova que ela o causou. Conteúdo educacional, não é recomendação de investimento.</p>
        </div>
''' + foot()


def main():
    dados = juntar()
    os.makedirs('juros', exist_ok=True)
    velho = None
    try:
        velho = json.load(open(ARQ, encoding='utf-8'))
    except Exception:
        pass
    if not velho or velho.get('dias') != dados['dias']:
        json.dump(dados, open(ARQ, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    mudou = []
    novo = pagina(dados)
    if not os.path.exists(SAIDA) or open(SAIDA, encoding='utf-8').read() != novo:
        open(SAIDA, 'w', encoding='utf-8').write(novo)
        mudou.append(SAIDA)
    sm = open('sitemap.xml', encoding='utf-8').read()
    if f'{BASE}juros/</loc>' not in sm:
        ultimo = max(dados['dias']) if dados['dias'] else dt.date.today().isoformat()
        sm = sm.replace('</urlset>', f'  <url><loc>{BASE}juros/</loc><lastmod>{ultimo}</lastmod><changefreq>weekly</changefreq><priority>0.6</priority></url>\n</urlset>')
        open('sitemap.xml', 'w', encoding='utf-8').write(sm)
    print(f'::notice::Dias que mexeram nos juros: {len(dados["dias"])} dia(s); página {"atualizada" if mudou else "sem mudança"}')
    print('PAGINAS=' + ' '.join(mudou))


if __name__ == '__main__':
    main()
