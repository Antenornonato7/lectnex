"""Story do placar da semana (1080×1920): acertos e erros do termômetro e do histórico nos eventos, no Telegram PRIVADO do dono.
Roda no fechamento de sexta (ou com --forcar em qualquer dia, para prévia). Lê data/placar-termometro.json e data/placar-historico.json.
Uso: python3 scripts/story_placar.py [saida.png] [--data AAAA-MM-DD] [--forcar] [--sem-envio]
"""
import datetime as dt
import json
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from og_leitura import BG, CARD, DIAS, LINE, MUTED, ORANGE, TEAL_L, VERDE, VERMELHO, WHITE, fonte  # noqa: E402
from story_leitura import H, M, W, enviar, tracejado  # noqa: E402

BRT = dt.timezone(dt.timedelta(hours=-3))
K = ('win', 'wdo')


def ler(p):
    try:
        return json.load(open(p, encoding='utf-8'))
    except Exception:
        return {}


def contar(lst, f):
    n = ok = 0
    for x in lst:
        for k in K:
            a = f(x, k)
            if a is not None:
                n += 1
                ok += bool(a)
    return n, ok


def dados(hoje):
    ini = hoje - dt.timedelta(days=hoje.weekday())
    fim = ini + dt.timedelta(days=4)
    na = lambda d: ini.isoformat() <= d <= fim.isoformat()
    dias = ler('data/placar-termometro.json').get('dias', [])
    evs = ler('data/placar-historico.json').get('eventos', [])
    aT = lambda x, k: x[k].get('acerto') if x.get(k) else None
    aH = lambda e, k: (e.get('acerto') or {}).get(k)
    return {'ini': ini, 'fim': fim, 'dias_sem': [x for x in dias if na(x['data'])], 'evs_sem': [e for e in evs if na(e['data'])],
            'term_sem': contar([x for x in dias if na(x['data'])], aT), 'term_tot': contar(dias, aT), 'n_dias': len(dias),
            'hist_sem': contar([e for e in evs if na(e['data'])], aH), 'hist_tot': contar(evs, aH), 'aT': aT, 'aH': aH}


def gerar(d, saida):
    im = Image.new('RGB', (W, H), BG)
    dr = ImageDraw.Draw(im)
    for x in range(0, W, 48):
        dr.line([(x, 0), (x, H)], fill='#0A1422')
    for y in range(0, H, 48):
        dr.line([(0, y), (W, y)], fill='#0A1422')
    dr.rectangle([0, 0, W, 12], fill=TEAL_L)
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
    dr.text((M, y), f'PLACAR DA SEMANA · {d["ini"]:%d/%m} A {d["fim"]:%d/%m}', font=fonte('JetBrainsMono-Bold.ttf', 32), fill=TEAL_L)
    y += 62
    ft = fonte('InterDisplay-Bold.otf', 96)
    dr.text((M, y), 'Acertamos?', font=ft, fill=WHITE)
    y += 120
    dr.text((M, y), 'Com os erros também.', font=fonte('Inter-Medium.otf', 40), fill=MUTED)
    y += 90

    def bloco(y, titulo, sem, tot, sub, cor_t):
        n, ok = sem
        dr.rectangle([M, y, W - M, y + 300], fill=CARD, outline=LINE, width=2)
        dr.rectangle([M, y, M + 10, y + 300], fill=cor_t)
        dr.text((M + 44, y + 34), titulo, font=fonte('JetBrainsMono-Bold.ttf', 28), fill=cor_t)
        if n:
            fv = fonte('InterDisplay-Bold.otf', 120)
            t = f'{ok} de {n}'
            dr.text((M + 44, y + 80), t, font=fv, fill=WHITE)
            p = f'{ok / n * 100:.0f}%'
            fp = fonte('InterDisplay-Bold.otf', 64)
            dr.text((W - M - 44 - dr.textlength(p, font=fp), y + 118), p, font=fp, fill=VERDE if ok / n >= 0.5 else VERMELHO)
        else:
            dr.text((M + 44, y + 110), 'Sem leituras com direção nesta semana', font=fonte('Inter-Medium.otf', 36), fill=MUTED)
        nt, okt = tot
        linha = sub + (f' · desde o início: {okt} de {nt} ({okt / nt * 100:.0f}%)' if nt > n else '')
        dr.text((M + 44, y + 240), linha, font=fonte('Inter-Medium.otf', 28), fill=MUTED)
        return y + 330

    y = bloco(y, 'TERMÔMETRO DA MANHÃ (WIN E WDO)', d['term_sem'], d['term_tot'], f'{len(d["dias_sem"])} pregões', TEAL_L)
    if d['evs_sem'] or d['hist_tot'][0]:
        nomes = ', '.join(e['evento'] for e in d['evs_sem'][:3]) or 'nenhum evento forte'
        y = bloco(y, 'HISTÓRICO NOS EVENTOS FORTES', d['hist_sem'], d['hist_tot'], nomes, ORANGE)

    # tira dos dias: um quadrado por leitura (verde acertou, vermelho errou)
    if d['dias_sem'] and y < 1380:
        fm = fonte('JetBrainsMono-Bold.ttf', 24)
        dr.text((M, y + 6), 'DIA A DIA', font=fm, fill=MUTED)
        y += 48
        larg = (W - 2 * M) / 5
        for i, x in enumerate(sorted(d['dias_sem'], key=lambda x: x['data'])[:5]):
            dd = dt.date.fromisoformat(x['data'])
            cx = M + i * larg
            dr.text((cx + 8, y), f'{DIAS[dd.weekday()][:3]}', font=fm, fill=WHITE)
            for j, k in enumerate(K):
                a = d['aT'](x, k)
                c = MUTED if a is None else VERDE if a else VERMELHO
                dr.rectangle([cx + 8 + j * 74, y + 44, cx + 72 + j * 74, y + 108], fill=c)
                dr.text((cx + 18 + j * 74, y + 62), k.upper(), font=fonte('JetBrainsMono-Bold.ttf', 20), fill=BG)
        y += 140

    tracejado(dr, (M, 1600, W - M, 1730), '#334155')
    fs = fonte('JetBrainsMono-Bold.ttf', 24)
    s = 'COLOQUE AQUI O STICKER DE LINK'
    dr.text(((W - dr.textlength(s, font=fs)) / 2, 1650), s, font=fs, fill='#475569')
    for i, l in enumerate(('Mede leituras de viés, não operações. Acerto passado não garante o futuro.',
                           'Placar completo em lectnex.com.br/placar · conteúdo educacional')):
        f2 = fonte('Inter-Medium.otf', 25)
        dr.text(((W - dr.textlength(l, font=f2)) / 2, 1770 + i * 38), l, font=f2, fill=MUTED)
    im.save(saida, 'PNG', optimize=True)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    hoje = dt.datetime.now(BRT).date()
    if '--data' in sys.argv:
        hoje = dt.date.fromisoformat(sys.argv[sys.argv.index('--data') + 1])
        args = [a for a in args if a != hoje.isoformat()]
    if hoje.weekday() != 4 and '--forcar' not in sys.argv:
        print('Story do placar só às sextas.')
        return
    d = dados(hoje)
    if not d['dias_sem'] and not d['evs_sem']:
        print('Semana sem placar: story não gerado.')
        return
    saida = args[0] if args else 'placar-semana.png'
    gerar(d, saida)
    n, ok = d['term_sem']
    print(f'Story do placar: termômetro {ok}/{n}')
    if '--sem-envio' in sys.argv:
        return
    hn, hok = d['hist_sem']
    legenda = (f'🎯 <b>Placar da semana</b> · {d["ini"]:%d/%m} a {d["fim"]:%d/%m}\n'
               f'Termômetro: {ok}/{n}' + (f' · Eventos: {hok}/{hn}' if hn else '') +
               '\n\nNo Instagram: poste nos stories e coloque o <b>sticker de link</b> na área tracejada com '
               '<code>lectnex.com.br/placar</code> (texto do sticker: "Placar completo").')
    enviar(saida, legenda)


if __name__ == '__main__':
    main()
