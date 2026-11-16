"""Carrossel semanal do Instagram (4 imagens 1080×1350), enviado no Telegram PRIVADO do dono no sábado de manhã.

1. Capa: a semana do Ibovespa e do dólar.   2. Dia a dia (fechamentos e variações).
3. Placar do termômetro da semana.           4. Agenda da próxima semana + chamada.
Fechamentos diários: Yahoo Finance (^BVSP e BRL=X). Placar: data/placar-termometro.json. Agenda: data/calendario.json.
Uso: python3 scripts/carrossel_semana.py [--previa] [--dados arquivo.json] [pasta_saida]
"""
import datetime as dt
import re
import json
import os
import sys
import urllib.request
import uuid

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from og_leitura import BG, CARD, LINE, MUTED, ORANGE, TEAL_L, VERDE, VERMELHO, WHITE, fonte, quebrar  # noqa: E402

W, H, M = 1080, 1350, 84
BRT = dt.timezone(dt.timedelta(hours=-3))
HOJE = dt.datetime.now(BRT).date()
DIA = ['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom']
FLAG = {'BR': 'Brasil', 'US': 'EUA', 'CN': 'China', 'EU': 'Europa', 'JP': 'Japão', 'UK': 'Reino Unido'}
SETA = {'bullish': '▲', 'bearish': '▼', 'neutro': '●'}
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36', 'Accept': 'application/json,*/*'}


def pct(v):
    return ('+' if v > 0 else '−' if v < 0 else '') + f'{abs(v):.2f}%'.replace('.', ',')


def cor(v):
    return VERDE if v > 0 else VERMELHO if v < 0 else MUTED


def ler(p):
    try:
        return json.load(open(p, encoding='utf-8'))
    except Exception:
        return None


def yahoo(sym):
    """[(data, fechamento)] dos últimos ~30 pregões."""
    for host in ('query2', 'query1'):
        try:
            req = urllib.request.Request(f'https://{host}.finance.yahoo.com/v8/finance/chart/{urllib.request.quote(sym)}?interval=1d&range=1mo', headers=UA)
            with urllib.request.urlopen(req, timeout=20) as r:
                res = json.load(r)['chart']['result'][0]
            out = []
            for t, c in zip(res['timestamp'], res['indicators']['quote'][0]['close']):
                if c is not None:
                    out.append((dt.datetime.fromtimestamp(t, BRT).date(), float(c)))
            return out
        except Exception as e:
            print(f'::warning::Yahoo {host} {sym}: {e}')
    return []


def semana(serie, ini, fim):
    """Fechamentos da semana [ini, fim] e a variação contra o último fechamento antes de ini."""
    dias = [(d, c) for d, c in serie if ini <= d <= fim]
    antes = [c for d, c in serie if d < ini]
    if not dias or not antes:
        return None
    base, prev, linhas = antes[-1], antes[-1], []
    for d, c in dias:
        linhas.append({'data': d.isoformat(), 'fech': c, 'var': (c / prev - 1) * 100})
        prev = c
    return {'dias': linhas, 'var': (dias[-1][1] / base - 1) * 100, 'fech': dias[-1][1]}


def coletar():
    ini = HOJE - dt.timedelta(days=HOJE.weekday())  # segunda desta semana (no sábado: a semana que acabou)
    fim = ini + dt.timedelta(days=4)
    ib, us = semana(yahoo('^BVSP'), ini, fim), semana(yahoo('BRL=X'), ini, fim)
    placar = [d for d in (ler('data/placar-termometro.json') or {}).get('dias', []) if ini.isoformat() <= d['data'] <= fim.isoformat()]
    todos = (ler('data/placar-termometro.json') or {}).get('dias', [])[-20:]
    cal = ler('data/calendario.json') or {}
    prox_ini, prox_fim = ini + dt.timedelta(days=7), ini + dt.timedelta(days=11)
    evs = [e for e in cal.get('eventos', []) if prox_ini.isoformat() <= e.get('data', '') <= prox_fim.isoformat() and (e.get('importancia') or 1) >= 3]
    evs.sort(key=lambda e: (e['data'], e.get('hora') is None, e.get('hora') or ''))
    ph = (ler('data/placar-historico.json') or {}).get('eventos', [])
    eventos = [e for e in ph if ini.isoformat() <= e['data'] <= fim.isoformat()]
    regs = [x for x in (ler('data/reacoes.json') or {}).get('registros', []) if ini.isoformat() <= x['data'] <= fim.isoformat()
            and (x.get('win') is not None or x.get('wdo') is not None)]
    try:
        from dados_paginas import SOBRE
    except Exception:
        SOBRE = {}
    def prio(x):  # 0: dados principais (IPCA, payroll, CPI, Fed, Copom) · 1: outro dado com consenso, saindo entre 8h e 18h30
        h = re.match(r'(\d{1,2})', x.get('hora') or '')
        no_dia = h and 8 <= int(h.group(1)) <= 18
        return 0 if x.get('tipo') in SOBRE else 1 if (x.get('consenso') and no_dia) else 9
    regs = [x for x in regs if prio(x) < 9]
    regs.sort(key=lambda x: (prio(x), -(abs(x.get('win') or 0) + abs(x.get('wdo') or 0))))
    dados = sorted(regs[:3], key=lambda x: (x['data'], x.get('hora') or ''))
    return {'ini': ini.isoformat(), 'fim': fim.isoformat(), 'ibov': ib, 'dolar': us, 'placar': placar, 'placar20': todos, 'dados': dados,
            'eventos': eventos, 'eventos_total': ph,
            'agenda': [{'data': e['data'], 'hora': e.get('hora'), 'pais': e.get('pais'), 'evento': e['evento']} for e in evs[:6]]}


def base(titulo, n, previa, total=4):
    im = Image.new('RGB', (W, H), BG)
    dr = ImageDraw.Draw(im)
    for x in range(0, W, 48):
        dr.line([(x, 0), (x, H)], fill='#0A1422')
    for y in range(0, H, 48):
        dr.line([(0, y), (W, y)], fill='#0A1422')
    dr.rectangle([0, 0, W, 10], fill=ORANGE)
    try:
        logo = Image.open('assets/brand/icon-192.png').convert('RGBA').resize((56, 56))
        im.paste(logo, (M, 60), logo)
    except Exception:
        pass
    fb = fonte('InterDisplay-Bold.otf', 38)
    dr.text((M + 72, 66), 'Lect', font=fb, fill=WHITE)
    dr.text((M + 72 + dr.textlength('Lect', font=fb), 66), 'nex', font=fb, fill=TEAL_L)
    fm = fonte('JetBrainsMono-Bold.ttf', 24)
    s = f'{n}/{total}'
    dr.text((W - M - dr.textlength(s, font=fm), 76), s, font=fm, fill=MUTED)
    if previa:
        p = 'PRÉVIA · SEMANA EM ANDAMENTO'
        tw = dr.textlength(p, font=fm)
        dr.rectangle([W - M - tw - 100, 66, W - M - 70, 108], fill=ORANGE)
        dr.text((W - M - tw - 86, 74), p, font=fm, fill=BG)
    dr.text((M, 160), titulo, font=fonte('JetBrainsMono-Bold.ttf', 30), fill=ORANGE)
    rod = 'lectnex.com.br · conteúdo educacional, não é recomendação'
    fr = fonte('Inter-Medium.otf', 24)
    dr.text(((W - dr.textlength(rod, font=fr)) / 2, H - 70), rod, font=fr, fill=MUTED)
    return im, dr


def br(iso):
    d = dt.date.fromisoformat(iso)
    return f'{d:%d/%m}'


def slide_dado(x, caminho, n, T, previa):
    """Slide de uma divulgação da semana (mesmo conteúdo da imagem da página dados/<dado>-<data>.html, em retrato)."""
    from divulgacao_imagem import _serie, _min
    im, dr = base('A SEMANA EM DADOS', n, previa, T)
    d = dt.date.fromisoformat(x['data'])
    nome = re.sub(r'\s*\(.*?\)', '', x.get('evento', '')).strip()
    fe = fonte('InterDisplay-Bold.otf', 60)
    for i, l in enumerate(quebrar(dr, nome, fe, W - 2 * M, 2)):
        dr.text((M, 220 + i * 70), l, font=fe, fill=WHITE)
    y = 220 + 70 * len(quebrar(dr, nome, fe, W - 2 * M, 2)) + 10
    dr.text((M, y), f'{DIA[d.weekday()]} {d:%d/%m}' + (f' · {x["hora"]}' if x.get('hora') else ''), font=fonte('JetBrainsMono-Bold.ttf', 28), fill=TEAL_L)
    y += 70
    fs = fonte('InterDisplay-Bold.otf', 120)
    res = str(x.get('resultado') or '—')
    if dr.textlength(res, font=fs) > W - 2 * M:
        fs = fonte('InterDisplay-Bold.otf', 64)
    dr.text((M, y), res, font=fs, fill=WHITE)
    y += 150 if fs.size > 100 else 90
    sup = x.get('surpresa')
    if x.get('consenso'):
        fc = fonte('JetBrainsMono-Bold.ttf', 32)
        dr.text((M, y), f'consenso {x["consenso"]}', font=fc, fill=MUTED)
        if sup in ('acima', 'abaixo', 'em linha'):
            rot = {'acima': '▲ ACIMA', 'abaixo': '▼ ABAIXO', 'em linha': '= EM LINHA'}[sup]
            xb = M + dr.textlength(f'consenso {x["consenso"]}', font=fc) + 28
            fb = fonte('JetBrainsMono-Bold.ttf', 28)
            dr.rectangle([xb, y - 4, xb + dr.textlength(rot, font=fb) + 28, y + 42], fill=ORANGE if sup == 'acima' else '#3B82F6' if sup == 'abaixo' else MUTED)
            dr.text((xb + 14, y + 2), rot, font=fb, fill=BG)
        y += 80
    janela = '1 H' if x.get('janela') == '1h' else '30 MIN'
    bw = (W - 2 * M - 30) // 2
    for i, (rot, k) in enumerate((('WIN', 'win'), ('WDO', 'wdo'))):
        bx, v = M + i * (bw + 30), x.get(k)
        dr.rectangle([bx, y, bx + bw, y + 170], fill=CARD, outline=LINE, width=2)
        dr.text((bx + 24, y + 22), f'{rot} EM {janela}', font=fonte('JetBrainsMono-Bold.ttf', 26), fill=MUTED)
        dr.text((bx + 24, y + 70), pct(v) if v is not None else '—', font=fonte('JetBrainsMono-Bold.ttf', 64), fill=cor(v) if v is not None else MUTED)
    if x.get('win_abertura'):
        dr.text((M, y + 180), 'WIN: bolsa fechada na hora do dado, inclui o gap da abertura', font=fonte('Inter-Medium.otf', 22), fill=MUTED)
        y += 34
    y += 200
    t0 = _min(x.get('hora'))
    series = [(c, n_, _serie(x['data'], k, t0)) for c, n_, k in ((TEAL_L, 'Ibovespa', 'ibov'), (ORANGE, 'dólar', 'dolar'))] if t0 is not None else []
    series = [z for z in series if z[2]]
    if series and y + 260 < H - 120:
        gx0, gx1, gy0, gy1 = M, W - M, y, y + 230
        dr.rectangle([gx0, gy0, gx1, gy1], fill=CARD, outline=LINE, width=2)
        xs = [m for _, _, z in series for m, _ in z]
        ys = [v for _, _, z in series for _, v in z] + [0]
        lo, hi = min(ys), max(ys)
        pad = max(0.05, (hi - lo) * 0.15)
        lo, hi = lo - pad, hi + pad
        X = lambda m: gx0 + 20 + (m - min(xs)) / max(1, max(xs) - min(xs)) * (gx1 - gx0 - 40)
        Y = lambda v: gy0 + 18 + (hi - v) / (hi - lo) * (gy1 - gy0 - 36)
        if min(xs) <= t0 <= max(xs):
            dr.line([(X(t0), gy0 + 10), (X(t0), gy1 - 10)], fill=MUTED, width=2)
        fl, lx = fonte('JetBrainsMono-Bold.ttf', 22), gx0
        for c, n_, z in series:
            dr.line([(X(m), Y(v)) for m, v in z], fill=c, width=5, joint='curve')
            dr.text((lx, gy1 + 12), n_, font=fl, fill=c)
            lx += dr.textlength(n_, font=fl) + 26
        dr.text((lx, gy1 + 12), 'até 1 h depois do dado', font=fl, fill=MUTED)
    try:
        from dados_paginas import SOBRE, SLUG
        if x.get('tipo') in SOBRE:
            dr.text((M, H - 140), f'Histórico e reação: lectnex.com.br/dados/{SLUG.get(x["tipo"], x["tipo"])}', font=fonte('JetBrainsMono-Bold.ttf', 26), fill=TEAL_L)
    except Exception:
        pass
    im.save(caminho)
    return caminho


def slides(dd, pasta, previa=False):
    os.makedirs(pasta, exist_ok=True)
    out = []
    evs = dd.get('eventos') or []
    dds = dd.get('dados') or []
    ND = len(dds)
    T = 4 + ND + (1 if evs else 0)  # capa, dia a dia, placar, [dados da semana], [eventos], agenda
    ib, us = dd.get('ibov'), dd.get('dolar')
    periodo = f'{br(dd["ini"])} a {br(dd["fim"])}'

    # 1. capa
    im, dr = base('A SEMANA NO MERCADO', 1, previa, T)
    ft = fonte('InterDisplay-Bold.otf', 92)
    y = 230
    for linha in ['Como foi', 'a semana'] + ([] if not periodo else []):
        dr.text((M, y), linha, font=ft, fill=WHITE); y += 104
    dr.text((M, y + 6), periodo, font=fonte('JetBrainsMono-Bold.ttf', 44), fill=TEAL_L)
    y += 110
    for chave, nome, fmt in (('ibov', 'IBOVESPA', lambda v: f'{v:,.0f}'.replace(',', '.')), ('dolar', 'DÓLAR', lambda v: 'R$ ' + f'{v:.3f}'.replace('.', ','))):
        s = dd.get(chave)
        if not s:
            continue
        dr.rectangle([M, y, W - M, y + 190], fill=CARD, outline=LINE, width=2)
        dr.rectangle([M, y, M + 10, y + 190], fill=cor(s['var']))
        dr.text((M + 40, y + 28), nome + ' NA SEMANA', font=fonte('JetBrainsMono-Bold.ttf', 26), fill=MUTED)
        dr.text((M + 40, y + 70), pct(s['var']), font=fonte('InterDisplay-Bold.otf', 84), fill=cor(s['var']))
        f2 = fonte('JetBrainsMono-Bold.ttf', 34)
        t = fmt(s['fech'])
        dr.text((W - M - 40 - dr.textlength(t, font=f2), y + 104), t, font=f2, fill=WHITE)
        y += 214
    dr.text((M, H - 150), 'Arraste para o dia a dia, o placar e a agenda →', font=fonte('Inter-Medium.otf', 30), fill=TEAL_L)
    out.append(os.path.join(pasta, '1-capa.png')); im.save(out[-1])

    # 2. dia a dia
    im, dr = base('DIA A DIA', 2, previa, T)
    dr.text((M, 220), 'Fechamentos da semana', font=fonte('InterDisplay-Bold.otf', 64), fill=WHITE)
    y = 340
    fl, fv = fonte('JetBrainsMono-Bold.ttf', 30), fonte('JetBrainsMono-Bold.ttf', 30)
    dias = sorted({x['data'] for s in (ib, us) if s for x in s['dias']})
    col = [M, M + 250, M + 610]
    dr.text((col[1], y), 'IBOVESPA', font=fonte('JetBrainsMono-Bold.ttf', 24), fill=MUTED)
    dr.text((col[2], y), 'DÓLAR', font=fonte('JetBrainsMono-Bold.ttf', 24), fill=MUTED)
    y += 50
    for d in dias:
        dd_ = dt.date.fromisoformat(d)
        dr.rectangle([M, y - 10, W - M, y + 112], fill=CARD, outline=LINE, width=1)
        dr.text((col[0] + 24, y + 30), f'{DIA[dd_.weekday()]} {dd_:%d/%m}', font=fl, fill=WHITE)
        for c, s, fmt in ((col[1], ib, lambda v: f'{v:,.0f}'.replace(',', '.')), (col[2], us, lambda v: f'{v:.3f}'.replace('.', ','))):
            x = next((r for r in (s or {}).get('dias', []) if r['data'] == d), None)
            if x:
                dr.text((c, y + 8), fmt(x['fech']), font=fonte('Inter-Medium.otf', 36), fill=WHITE)
                dr.text((c, y + 56), pct(x['var']), font=fv, fill=cor(x['var']))
        y += 134
    if not dias:
        dr.text((M, y), 'Sem fechamentos disponíveis.', font=fonte('Inter-Medium.otf', 34), fill=MUTED)
    out.append(os.path.join(pasta, '2-dia-a-dia.png')); im.save(out[-1])

    # 3. placar
    im, dr = base('PLACAR DO VIÉS DO MODELO', 3, previa, T)
    dr.text((M, 220), 'O viés do modelo', font=fonte('InterDisplay-Bold.otf', 64), fill=WHITE)
    dr.text((M, 296), 'acertou?', font=fonte('InterDisplay-Bold.otf', 64), fill=WHITE)
    y = 420
    pl = dd.get('placar') or []
    tot = sum(1 for x in pl for k in ('win', 'wdo') if k in x)
    ok = sum(1 for x in pl for k in ('win', 'wdo') if x.get(k, {}).get('acerto'))
    for x in pl:
        d = dt.date.fromisoformat(x['data'])
        dr.rectangle([M, y, W - M, y + 96], fill=CARD, outline=LINE, width=1)
        dr.text((M + 24, y + 28), f'{DIA[d.weekday()]} {d:%d/%m}', font=fl, fill=WHITE)
        xx = M + 250
        for k in ('win', 'wdo'):
            if k in x:
                t = x[k]
                dr.text((xx, y + 28), f'{k.upper()} {SETA.get(t["leitura"], "")} {"acertou" if t["acerto"] else "errou"}', font=fl, fill=VERDE if t['acerto'] else VERMELHO)
                xx += 330
        y += 112
    if tot:
        y += 20
        dr.text((M, y), f'Na semana: {ok} de {tot} ({ok / tot * 100:.0f}%)', font=fonte('InterDisplay-Bold.otf', 52), fill=TEAL_L)
        t20 = dd.get('placar20') or []
        tt = sum(1 for x in t20 for k in ('win', 'wdo') if k in x)
        oo = sum(1 for x in t20 for k in ('win', 'wdo') if x.get(k, {}).get('acerto'))
        if tt and len(t20) > len(pl):
            dr.text((M, y + 74), f'Últimos {len(t20)} pregões: {oo} de {tt} ({oo / tt * 100:.0f}%)', font=fonte('Inter-Medium.otf', 32), fill=MUTED)
    else:
        dr.text((M, y), 'Ainda sem placar nesta semana.', font=fonte('Inter-Medium.otf', 36), fill=MUTED)
    fn = fonte('Inter-Medium.otf', 26)
    for i, l in enumerate(quebrar(dr, 'Critério: conferido pelo Ibovespa (WIN) e pelo dólar à vista (WDO). Neutro acerta se a variação ficou dentro de ±0,7% no WIN e ±0,4% no WDO. Modelo experimental; mostramos os erros também.', fn, W - 2 * M, 3)):
        dr.text((M, H - 220 + i * 36), l, font=fn, fill=MUTED)
    out.append(os.path.join(pasta, '3-placar.png')); im.save(out[-1])

    # 4… a semana em dados: um slide por divulgação (as 3 que mais mexeram), com resultado, reação e mini gráfico
    for i, x in enumerate(dds):
        out.append(slide_dado(x, os.path.join(pasta, f'{4 + i}-dado.png'), 4 + i, T, previa))

    # a semana em eventos (antes × depois), se houve evento forte
    if evs:
        im, dr = base('A SEMANA EM EVENTOS', 4 + ND, previa, T)
        dr.text((M, 220), 'O histórico', font=fonte('InterDisplay-Bold.otf', 64), fill=WHITE)
        dr.text((M, 296), 'acertou?', font=fonte('InterDisplay-Bold.otf', 64), fill=WHITE)
        y = 410
        fe, fs, fj = fonte('InterDisplay-Bold.otf', 38), fonte('Inter-Medium.otf', 26), fonte('JetBrainsMono-Bold.ttf', 26)
        SP = {'acima': 'acima do consenso', 'abaixo': 'abaixo do consenso', 'em linha': 'em linha'}
        for e in evs[:4]:
            d = dt.date.fromisoformat(e['data'])
            dr.rectangle([M, y, W - M, y + 150], fill=CARD, outline=LINE, width=1)
            dr.text((M + 24, y + 18), e['evento'], font=fe, fill=WHITE)
            sub = f'{DIA[d.weekday()]} {d:%d/%m}' + (f' · {SP.get(e.get("surpresa"), e.get("surpresa"))}' if e.get('surpresa') else '')
            dr.text((W - M - 24 - dr.textlength(sub, font=fs), y + 30), sub, font=fs, fill=MUTED)
            for i, (k, nome) in enumerate((('win', 'WIN'), ('wdo', 'WDO'))):
                sb, v, a = (e.get('sobe') or {}).get(k), (e.get('reacao') or {}).get(k), (e.get('acerto') or {}).get(k)
                ind = '—' if sb is None else f'▲ {sb}%' if sb >= 60 else f'▼ {100 - sb}%' if sb <= 40 else 'dividido'
                x = M + 24 + i * ((W - 2 * M) // 2)
                dr.text((x, y + 82), f'{nome} {ind} →', font=fj, fill=MUTED)
                xx = x + dr.textlength(f'{nome} {ind} → ', font=fj)
                if v is None:
                    dr.text((xx, y + 82), 'pendente', font=fj, fill=MUTED)
                else:
                    dr.text((xx, y + 82), pct(v), font=fj, fill=cor(v))
                    if a is not None:
                        dr.text((xx + dr.textlength(pct(v) + ' ', font=fj), y + 82), 'acertou' if a else 'errou', font=fj, fill=VERDE if a else VERMELHO)
            y += 166
        tot = dd.get('eventos_total') or evs
        cont = lambda lst: (sum(1 for e in lst for k in ('win', 'wdo') if (e.get('acerto') or {}).get(k) is not None),
                            sum(1 for e in lst for k in ('win', 'wdo') if (e.get('acerto') or {}).get(k)))
        n, ok = cont(evs)
        nt, okt = cont(tot)
        y += 10
        if n:
            dr.text((M, y), f'Na semana: {ok} de {n} ({ok / n * 100:.0f}%)', font=fonte('InterDisplay-Bold.otf', 48), fill=TEAL_L)
            y += 66
        if nt and nt > n:
            dr.text((M, y), f'Desde o início: {okt} de {nt} ({okt / nt * 100:.0f}%)', font=fonte('Inter-Medium.otf', 32), fill=MUTED)
        fn = fonte('Inter-Medium.otf', 24)
        for i, l in enumerate(quebrar(dr, 'O histórico aponta alta quando o ativo subiu em 60% ou mais das vezes anteriores com a mesma surpresa, e queda com 40% ou menos. Dividido não conta. Reação de 30 min.', fn, W - 2 * M, 3)):
            dr.text((M, H - 210 + i * 34), l, font=fn, fill=MUTED)
        out.append(os.path.join(pasta, f'{4 + ND}-eventos.png')); im.save(out[-1])

    # agenda + chamada (último slide)
    im, dr = base('PRÓXIMA SEMANA', T, previa, T)
    dr.text((M, 220), 'O que vem por aí', font=fonte('InterDisplay-Bold.otf', 64), fill=WHITE)
    y = 340
    ag = dd.get('agenda') or []
    fe, fh = fonte('Inter-Medium.otf', 34), fonte('JetBrainsMono-Bold.ttf', 26)
    for e in ag[:6]:
        d = dt.date.fromisoformat(e['data'])
        linhas = quebrar(dr, e['evento'], fe, W - 2 * M - 230, 2)
        dr.text((M, y + 4), f'{DIA[d.weekday()]} {d:%d/%m}', font=fh, fill=TEAL_L)
        dr.text((M, y + 40), (e.get('hora') or '') + (' · ' + FLAG.get(e.get('pais'), '') if e.get('pais') else ''), font=fonte('JetBrainsMono-Bold.ttf', 22), fill=MUTED)
        for l in linhas:
            dr.text((M + 230, y), l, font=fe, fill=WHITE); y += 44
        y += 34
    if not ag:
        dr.text((M, y), 'A agenda da próxima semana sai na Leitura de domingo.', font=fe, fill=MUTED); y += 60
    yb = max(y + 20, H - 330)
    dr.rectangle([M, yb, W - M, yb + 190], fill='#1A1206', outline=ORANGE, width=2)
    dr.text((M + 36, yb + 30), 'Receba a Leitura do Dia grátis', font=fonte('InterDisplay-Bold.otf', 44), fill=WHITE)
    dr.text((M + 36, yb + 96), 'Cenário, agenda e notícias antes da abertura.', font=fonte('Inter-Medium.otf', 28), fill='#CBD5E1')
    dr.text((M + 36, yb + 138), 'lectnex.com.br/comece', font=fonte('JetBrainsMono-Bold.ttf', 30), fill=ORANGE)
    out.append(os.path.join(pasta, f'{T}-agenda.png')); im.save(out[-1])
    return out


def enviar(arquivos, legenda):
    token = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
    chat = os.environ.get('TELEGRAM_ADMIN_CHAT_ID', '').strip()
    if not token or not chat or chat.startswith('@'):
        print('::warning::Sem TELEGRAM_ADMIN_CHAT_ID (chat privado): carrossel gerado, mas não enviado.')
        return
    for tipo in ('photo', 'document'):
        b = uuid.uuid4().hex
        media = [{'type': tipo, 'media': f'attach://f{i}'} for i in range(len(arquivos))]
        media[-1 if tipo == 'document' else 0]['caption'] = legenda if tipo == 'photo' else f'As mesmas {len(arquivos)} imagens em qualidade original (sem compressão).'
        media[-1 if tipo == 'document' else 0]['parse_mode'] = 'HTML'
        corpo = f'--{b}\r\nContent-Disposition: form-data; name="chat_id"\r\n\r\n{chat}\r\n'.encode()
        corpo += f'--{b}\r\nContent-Disposition: form-data; name="media"\r\n\r\n{json.dumps(media, ensure_ascii=False)}\r\n'.encode()
        for i, a in enumerate(arquivos):
            corpo += f'--{b}\r\nContent-Disposition: form-data; name="f{i}"; filename="{os.path.basename(a)}"\r\nContent-Type: image/png\r\n\r\n'.encode() + open(a, 'rb').read() + b'\r\n'
        corpo += f'--{b}--\r\n'.encode()
        req = urllib.request.Request(f'https://api.telegram.org/bot{token}/sendMediaGroup', data=corpo, headers={'Content-Type': f'multipart/form-data; boundary={b}'})
        urllib.request.urlopen(req, timeout=90).read()
    print('Carrossel enviado no Telegram privado.')


def main():
    previa = '--previa' in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    dados = None
    if '--dados' in sys.argv:
        dados = json.load(open(sys.argv[sys.argv.index('--dados') + 1], encoding='utf-8'))
        args = [a for a in args if a != sys.argv[sys.argv.index('--dados') + 1]]
    dd = dados or coletar()
    pasta = args[0] if args else 'carrossel'
    arqs = slides(dd, pasta, previa)
    ib, us = dd.get('ibov'), dd.get('dolar')
    resumo = ' · '.join(filter(None, [f'Ibovespa {pct(ib["var"])}' if ib else '', f'dólar {pct(us["var"])}' if us else '']))
    legenda = ('🗓️ <b>Carrossel da semana pronto</b>' + (' <i>(prévia, semana em andamento)</i>' if previa else '') + f'\n{resumo}\n\n'
               '<b>Sugestão de legenda para o post:</b>\n'
               f'Como foi a semana no mercado ({br(dd["ini"])} a {br(dd["fim"])}): {resumo}. '
               'Arraste para ver o dia a dia, o placar do viés do nosso modelo (com acertos e erros)' + (', os eventos fortes da semana' if dd.get('eventos') else '') + ' e a agenda da próxima semana. '
               'Placar completo em lectnex.com.br/placar. Leitura do Dia grátis em lectnex.com.br. Conteúdo educacional, não é recomendação. #ibovespa #dolar #daytrade #miniindice #minidolar #b3')
    if os.environ.get('IG_LEGENDA') and not previa:
        cap = legenda.split('<b>Sugestão de legenda para o post:</b>\n', 1)[-1]
        open(os.environ['IG_LEGENDA'], 'w', encoding='utf-8').write(cap.replace('. Arraste', '.\n\nArraste').replace(' Placar completo', '\n\nPlacar completo').replace(' #ibovespa', '\n#ibovespa'))
    enviar(arqs, legenda)


if __name__ == '__main__':
    main()
