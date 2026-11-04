"""Antes do dado: no dia de um evento forte (Copom, Fed, payroll, IPCA, CPI…), mostra como o Ibovespa (WIN) e o dólar (WDO)
reagiram nas últimas vezes.

Fontes (só dados do próprio site):
  - data/reacoes.json   reação às divulgações anteriores do MESMO tipo de evento (30 min ou abertura seguinte)
  - data/manchetes.json reação às manchetes do mesmo tema (arquivo de manchetes)
Saídas:
  - data/antes.json     lido pelo card do Mercado Hoje e pela Leitura do Dia ({} quando não há evento forte hoje)
  - story 1080×1920 no Telegram PRIVADO do dono (pule com --sem-envio)
Uso: python3 scripts/antes_dado.py [saida.png] [--data AAAA-MM-DD] [--sem-envio]
"""
import datetime as dt
import json
import os
import statistics
import sys

BRT = dt.timezone(dt.timedelta(hours=-3))
# tipo no calendário → (grupo de tipos que contam como "a mesma divulgação", tema do arquivo de manchetes, nome curto)
EVENTOS = {
    'copom': (['copom'], 'copom', 'Copom'),
    'fomc': (['fomc'], 'fed', 'Fed'),
    'payroll': (['payroll', 'desemprego-eua', 'salario-eua'], 'emprego', 'Payroll'),
    'desemprego-eua': (['payroll', 'desemprego-eua', 'salario-eua'], 'emprego', 'Payroll'),
    'ipca': (['ipca'], 'inflacao', 'IPCA'),
    'ipca-15': (['ipca-15', 'ipca'], 'inflacao', 'IPCA-15'),
    'cpi-eua': (['cpi-eua'], 'inflacao', 'CPI'),
    'pce-eua': (['pce-eua', 'cpi-eua'], 'inflacao', 'PCE'),
    'ata-copom': (['ata-copom', 'copom'], 'copom', 'Ata do Copom'),
    'pib': (['pib'], 'fiscal', 'PIB'),
    'jolts': (['jolts'], 'emprego', 'JOLTS'),
    'caged': (['caged'], 'emprego', 'Caged'),
}
PRIORIDADE = list(EVENTOS)  # empate de importância: Copom, Fed, payroll, IPCA… primeiro


def ler(caminho, padrao):
    try:
        return json.load(open(caminho, encoding='utf-8'))
    except Exception:
        return padrao


def estat(vals):
    v = [x for x in vals if isinstance(x, (int, float))]
    if not v:
        return None
    return {'n': len(v), 'sobe': round(sum(1 for x in v if x > 0) / len(v) * 100), 'mediana': round(statistics.median(v), 2),
            'movimento': round(sum(abs(x) for x in v) / len(v), 2)}


def montar(hoje):
    cal = ler('data/calendario.json', {}).get('eventos', [])
    evs = [e for e in cal if e.get('data') == hoje.isoformat() and (e.get('importancia') or 1) >= 3 and e.get('tipo') in EVENTOS]
    if not evs:
        return {}
    ev = sorted(evs, key=lambda e: PRIORIDADE.index(e['tipo']))[0]
    grupo, tema, curto = EVENTOS[ev['tipo']]
    regs = [r for r in ler('data/reacoes.json', {}).get('registros', []) if r.get('tipo') in grupo and r.get('data', '') < hoje.isoformat()]
    vistos, passadas = set(), []
    for r in sorted(regs, key=lambda r: (r['data'], r.get('hora') or ''), reverse=True):
        if r['data'] in vistos:  # payroll e desemprego saem juntos: uma linha por dia
            continue
        vistos.add(r['data'])
        passadas.append({'data': r['data'], 'evento': r.get('evento'), 'resultado': r.get('resultado'), 'consenso': r.get('consenso'),
                         'surpresa': r.get('surpresa'), 'win': r.get('win'), 'wdo': r.get('wdo'), 'abertura': bool(r.get('win_abertura')),
                         'janela': r.get('janela', '30min')})
    todas, passadas = passadas, passadas[:12]
    mc = [x for x in ler('data/manchetes.json', {}).get('itens', []) if tema in (x.get('tm') or []) and x.get('d', '') < hoje.isoformat()]
    temas = ler('data/manchetes.json', {}).get('temas', {})
    out = {'data': hoje.isoformat(), 'tipo': ev['tipo'], 'curto': curto, 'evento': ev['evento'], 'hora': ev.get('hora'), 'pais': ev.get('pais'),
           'consenso': ev.get('consenso'), 'anterior': ev.get('anterior'), 'passadas': passadas,
           'divulgacoes': {'win': estat([p['win'] for p in todas]), 'wdo': estat([p['wdo'] for p in todas]), 'desde': todas[-1]['data'] if todas else None},
           'por_surpresa': {sp: {'win': estat([p['win'] for p in todas if p['surpresa'] == sp]), 'wdo': estat([p['wdo'] for p in todas if p['surpresa'] == sp])}
                            for sp in ('acima', 'abaixo') if sum(1 for p in todas if p['surpresa'] == sp) >= 3},
           'manchetes': {'tema': tema, 'nome': temas.get(tema, tema), 'win': estat([x.get('ib') for x in mc]), 'wdo': estat([x.get('dl') for x in mc])},
           'gerado_em': dt.datetime.now(BRT).isoformat(timespec='minutes')}
    if not passadas and not (out['manchetes']['win'] or out['manchetes']['wdo']):
        out['vazio'] = True  # evento forte, mas ainda sem histórico: o card mostra só o aviso
    return out


def pct(v):
    return '—' if v is None else ('+' if v > 0 else '−' if v < 0 else '') + f'{abs(v):.2f}%'.replace('.', ',')


def gerar_story(a, saida):
    from PIL import Image, ImageDraw
    sys.path.insert(0, os.path.dirname(__file__))
    from og_leitura import BG, CARD, DIAS, LINE, MUTED, ORANGE, TEAL_L, VERDE, VERMELHO, WHITE, fonte, quebrar
    from story_leitura import H, M, W, tracejado
    d = dt.date.fromisoformat(a['data'])
    im = Image.new('RGB', (W, H), BG)
    dr = ImageDraw.Draw(im)
    for x in range(0, W, 48):
        dr.line([(x, 0), (x, H)], fill='#0A1422')
    for y in range(0, H, 48):
        dr.line([(0, y), (W, y)], fill='#0A1422')
    dr.rectangle([0, 0, W, 12], fill=ORANGE)
    y = 200
    try:
        logo = Image.open('assets/brand/icon-192.png').convert('RGBA').resize((68, 68))
        im.paste(logo, (M, y), logo)
    except Exception:
        pass
    fb = fonte('InterDisplay-Bold.otf', 46)
    dr.text((M + 88, y + 8), 'Lect', font=fb, fill=WHITE)
    dr.text((M + 88 + dr.textlength('Lect', font=fb), y + 8), 'nex', font=fb, fill=TEAL_L)
    y += 120
    dr.text((M, y), f'ANTES DO DADO · {DIAS[d.weekday()]} {d:%d/%m}', font=fonte('JetBrainsMono-Bold.ttf', 32), fill=ORANGE)
    y += 62
    ft = fonte('InterDisplay-Bold.otf', 84)
    for l in quebrar(dr, a['evento'], ft, W - 2 * M, 2):
        dr.text((M, y), l, font=ft, fill=WHITE)
        y += 96
    info = f'Hoje às {a["hora"]}' if a.get('hora') else 'Hoje'
    if a.get('consenso'):
        info += f' · consenso {a["consenso"]}'
    dr.text((M, y + 8), info, font=fonte('Inter-Medium.otf', 38), fill=TEAL_L)
    y += 96
    dr.text((M, y), 'Como o mercado reagiu nas últimas vezes', font=fonte('InterDisplay-Bold.otf', 44), fill=WHITE)
    y += 64
    dr.text((M, y), 'Variação após a divulgação: 30 min (1 h nas mais antigas)' if any(p.get('janela') == '1h' for p in a['passadas']) else 'Variação em 30 min após a divulgação', font=fonte('Inter-Medium.otf', 30), fill=MUTED)
    y += 64

    ps = list(reversed(a['passadas'][:2 if len(a.get('por_surpresa') or {}) == 2 else 4]))
    fm, fs = fonte('JetBrainsMono-Bold.ttf', 30), fonte('JetBrainsMono-Bold.ttf', 24)
    if ps:
        escala = max([abs(p[k]) for p in ps for k in ('win', 'wdo') if isinstance(p.get(k), (int, float))] + [0.3])
        larg = (W - 2 * M - 330) / 2
        dr.text((M + 330, y), 'IBOVESPA · WIN', font=fs, fill=MUTED)
        dr.text((M + 330 + larg + 20, y), 'DÓLAR · WDO', font=fs, fill=MUTED)
        y += 44
        for p in ps:
            pd = dt.date.fromisoformat(p['data'])
            dr.rectangle([M, y, W - M, y + 104], fill=CARD, outline=LINE, width=2)
            dr.text((M + 24, y + 18), f'{pd:%d/%m/%y}', font=fm, fill=WHITE)
            sp = {'acima': 'acima do esperado', 'abaixo': 'abaixo do esperado', 'em linha': 'em linha'}.get(p.get('surpresa'), (p.get('resultado') or '')[:16])
            dr.text((M + 24, y + 62), (sp or 'WIN na abertura' if p.get('abertura') else sp) + ('*' if p.get('abertura') and sp else ''), font=fonte('Inter-Medium.otf', 24), fill=MUTED)
            if p.get('janela') == '1h':
                dr.text((M + 24 + dr.textlength(f'{pd:%d/%m/%y}', font=fm) + 14, y + 24), '1 h', font=fs, fill=MUTED)
            for j, k in enumerate(('win', 'wdo')):
                v = p.get(k)
                x0 = M + 330 + j * (larg + 20)
                meio = x0 + larg / 2
                dr.line([(meio, y + 22), (meio, y + 64)], fill='#334155', width=2)
                if isinstance(v, (int, float)):
                    w = max(4, abs(v) / escala * (larg / 2 - 10))
                    cor = VERDE if v > 0 else VERMELHO
                    dr.rectangle([meio, y + 30, meio + w, y + 58] if v > 0 else [meio - w, y + 30, meio, y + 58], fill=cor)
                    t = pct(v)
                    dr.text((meio - dr.textlength(t, font=fm) / 2, y + 66), t, font=fm, fill=cor)
            y += 116
    else:
        dr.text((M, y), 'Primeira divulgação no nosso histórico.', font=fonte('Inter-Medium.otf', 34), fill=MUTED)
        y += 70

    linhas = []
    dv = a['divulgacoes']
    n = max((dv['win'] or {}).get('n', 0), (dv['wdo'] or {}).get('n', 0))
    if n >= 3:
        linhas.append((f'NAS ÚLTIMAS {n} DIVULGAÇÕES', dv))
    mm = a['manchetes']
    if (mm['win'] or {}).get('n', 0) >= 3:
        linhas.append((f'MANCHETES DE {mm["nome"].upper()} ({mm["win"]["n"]})', mm))
    fr, fv, fl = fonte('Inter-Medium.otf', 30), fonte('InterDisplay-Bold.otf', 40), fonte('JetBrainsMono-Bold.ttf', 20)
    cols = [M + 250, M + 500, M + 740]
    for tit, st in linhas:
        if y > 1470:
            break
        y += 24
        dr.text((M, y), tit, font=fonte('JetBrainsMono-Bold.ttf', 26), fill=TEAL_L)
        y += 46
        for c, rot in zip(cols, ('SUBIU EM', 'MEDIANA', 'MOVIMENTO MÉDIO')):
            dr.text((c, y), rot, font=fl, fill=MUTED)
        y += 30
        for k, nome in (('win', 'Ibovespa'), ('wdo', 'Dólar')):
            e = st.get(k)
            if not e:
                continue
            dr.text((M, y + 6), nome, font=fr, fill='#CBD5E1')
            mov = f'±{e["movimento"]:.2f}%'.replace('.', ',')
            for c, t, cor in zip(cols, (f'{e["sobe"]}%', pct(e['mediana']), mov),
                                 (WHITE, VERDE if e['mediana'] > 0 else VERMELHO if e['mediana'] < 0 else WHITE, WHITE)):
                dr.text((c, y), t, font=fv, fill=cor)
            y += 56
    psu = a.get('por_surpresa') or {}
    if len(psu) == 2 and y < 1300:
        y += 24
        dr.text((M, y), 'SE VIER ACIMA OU ABAIXO DO CONSENSO', font=fonte('JetBrainsMono-Bold.ttf', 26), fill=ORANGE)
        y += 46
        for c, rot in zip(cols, ('VEZES', 'IBOVESPA SUBIU', 'DÓLAR SUBIU')):
            dr.text((c, y), rot, font=fl, fill=MUTED)
        y += 30
        for sp, nome in (('acima', 'Acima'), ('abaixo', 'Abaixo')):
            e = psu[sp]
            dr.text((M, y + 6), nome, font=fr, fill='#CBD5E1')
            n_ = max((e['win'] or {}).get('n', 0), (e['wdo'] or {}).get('n', 0))
            vals = (str(n_), f'{e["win"]["sobe"]}%' if e['win'] else '—', f'{e["wdo"]["sobe"]}%' if e['wdo'] else '—')
            for c, t in zip(cols, vals):
                dr.text((c, y), t, font=fv, fill=WHITE)
            y += 56
    if any(p.get('abertura') for p in ps) and y < 1560:
        dr.text((M, y + 14), '* WIN medido na abertura seguinte (saiu com a bolsa fechada)', font=fonte('Inter-Medium.otf', 24), fill=MUTED)
        y += 40
    n_total = max((dv['win'] or {}).get('n', 0), 0)
    if n_total < 5 and y < 1560:
        dr.text((M, y + 16), 'Amostra pequena: o histórico cresce a cada divulgação.', font=fonte('Inter-Medium.otf', 26), fill=ORANGE)

    tracejado(dr, (M, 1600, W - M, 1730), '#334155')
    s = 'COLOQUE AQUI O STICKER DE LINK'
    dr.text(((W - dr.textlength(s, font=fs)) / 2, 1650), s, font=fs, fill='#475569')
    for i, l in enumerate(('O passado não garante o próximo movimento.', 'Dados: Yahoo Finance (barras de 5 min e 1 h) · lectnex.com.br')):
        f2 = fonte('Inter-Medium.otf', 26)
        dr.text(((W - dr.textlength(l, font=f2)) / 2, 1770 + i * 38), l, font=f2, fill=MUTED)
    im.save(saida, 'PNG', optimize=True)


def main():
    args = [x for x in sys.argv[1:] if not x.startswith('--')]
    hoje = dt.datetime.now(BRT).date()
    if '--data' in sys.argv:
        hoje = dt.date.fromisoformat(sys.argv[sys.argv.index('--data') + 1])
        args = [x for x in args if x != hoje.isoformat()]
    a = montar(hoje)
    velho = ler('data/antes.json', None)
    sem_hora = lambda x: {k: v for k, v in (x or {}).items() if k != 'gerado_em'}
    if sem_hora(velho) != sem_hora(a) or velho is None:
        json.dump(a, open('data/antes.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if not a:
        print('Sem evento forte com histórico hoje: data/antes.json vazio, sem story.')
        return
    print(f'Antes do dado: {a["evento"]} · {len(a["passadas"])} divulgação(ões) anteriores')
    if a.get('vazio') or '--sem-envio' in sys.argv:
        return
    saida = args[0] if args else 'antes-do-dado.png'
    gerar_story(a, saida)
    sys.path.insert(0, os.path.dirname(__file__))
    from og_leitura import DIAS
    from story_leitura import enviar
    d = dt.date.fromisoformat(a['data'])
    legenda = (f'⏱️ <b>Antes do dado</b> · {DIAS[d.weekday()].lower()} {d:%d/%m}: <b>{a["evento"]}</b>' + (f' às {a["hora"]}' if a.get('hora') else '') +
               '\n\nNo Instagram: poste nos stories e coloque o <b>sticker de link</b> na área tracejada com '
               f'<code>lectnex.com.br/manchetes.html#{a["manchetes"]["tema"]}</code> (texto do sticker: "Histórico").')
    enviar(saida, legenda)


if __name__ == '__main__':
    main()
