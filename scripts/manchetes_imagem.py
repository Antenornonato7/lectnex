"""Imagem do dia (1200×630, JPG) para a página manchetes/AAAA-MM-DD.html → assets/og/manchetes/AAAA-MM-DD.jpg.

É a imagem grande que o Google Discover, o WhatsApp, o Telegram e o Discord mostram ao compartilhar a página:
data, Ibovespa e dólar no dia, a curva do Ibovespa com as manchetes de alto impacto e a manchete que mais mexeu.
"""
import datetime as dt
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from og_leitura import BG, CARD, LINE, MUTED, ORANGE, TEAL_L, VERDE, VERMELHO, WHITE, fonte  # noqa: E402

PASTA = os.path.join(os.path.dirname(__file__), '..', 'assets', 'og', 'manchetes')
DIAS = ['SEGUNDA', 'TERÇA', 'QUARTA', 'QUINTA', 'SEXTA', 'SÁBADO', 'DOMINGO']


def _pct(v):
    return '—' if v is None else ('+' if v > 0 else '−' if v < 0 else '') + f'{abs(v):.2f}%'.replace('.', ',')


def _min(hm):
    h, m = map(int, hm.split(':'))
    return h * 60 + m


def _quebra(d, txt, ft, larg, linhas):
    out, atual = [], ''
    for p in txt.split():
        t = (atual + ' ' + p).strip()
        if d.textlength(t, font=ft) <= larg:
            atual = t
        else:
            out.append(atual); atual = p
            if len(out) == linhas:
                break
    if len(out) < linhas and atual:
        out.append(atual)
    if len(out) == linhas and ' '.join(out) != ' '.join(txt.split()):
        while d.textlength(out[-1] + '…', font=ft) > larg and ' ' in out[-1]:
            out[-1] = out[-1].rsplit(' ', 1)[0]
        out[-1] += '…'
    return out


def gerar(m, vi, vd, top):
    """m: dia de data/dias; vi/vd: variação do Ibovespa/dólar; top: manchete que mais mexeu (dict de itens_do_dia) ou None."""
    os.makedirs(PASTA, exist_ok=True)
    saida = os.path.join(PASTA, f'{m["data"]}.jpg')
    W, H, M = 1200, 630, 60
    im = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 12, H], fill=TEAL_L)
    dia = dt.date.fromisoformat(m['data'])
    d.text((M, 44), f'MERCADO EM 1 MINUTO · {DIAS[dia.weekday()]} {dia:%d/%m/%Y}', font=fonte('JetBrainsMono-Bold.ttf', 26), fill=TEAL_L)
    d.text((M, 84), 'O que mexeu no mercado', font=fonte('InterDisplay-Bold.otf', 56), fill=WHITE)
    # cartões Ibovespa e dólar
    for i, (rot, v) in enumerate((('IBOVESPA · WIN', vi), ('DÓLAR · WDO', vd))):
        x = M + i * 290
        d.rectangle([x, 176, x + 270, 300], fill=CARD, outline=LINE, width=2)
        d.text((x + 18, 190), rot, font=fonte('JetBrainsMono-Bold.ttf', 20), fill=MUTED)
        d.text((x + 18, 222), _pct(v), font=fonte('JetBrainsMono-Bold.ttf', 50), fill=MUTED if v is None else VERDE if v >= 0 else VERMELHO)
    # curva do Ibovespa com as manchetes de alto impacto
    s = m.get('ibov') or {}
    pts = [(_min(p[0]), p[1]) for p in s.get('pontos') or []]
    gx0, gx1, gy0, gy1 = M + 600, W - M, 176, 300
    if len(pts) >= 4:
        base = s.get('anterior') or pts[0][1]
        ys = [v for _, v in pts] + [base]
        lo, hi = min(ys), max(ys)
        pad = (hi - lo) * 0.12 or base * 0.002
        X = lambda t: gx0 + 14 + (t - pts[0][0]) / max(1, pts[-1][0] - pts[0][0]) * (gx1 - gx0 - 28)
        Y = lambda v: gy0 + 12 + (hi + pad - v) / ((hi - lo) + 2 * pad) * (gy1 - gy0 - 24)
        d.rectangle([gx0, gy0, gx1, gy1], fill=CARD, outline=LINE, width=2)
        d.line([(gx0 + 10, Y(base)), (gx1 - 10, Y(base))], fill=LINE, width=2)
        cor = VERDE if (vi or 0) >= 0 else VERMELHO
        d.line([(X(t), Y(v)) for t, v in pts], fill=cor, width=4, joint='curve')
        for mk in m.get('marcadores', []):
            if mk.get('impacto') != 'alto':
                continue
            t = _min(mk['hora'])
            if not pts[0][0] <= t <= pts[-1][0]:
                continue
            v = [v for tt, v in pts if tt <= t][-1]
            d.ellipse([X(t) - 6, Y(v) - 6, X(t) + 6, Y(v) + 6], fill=ORANGE, outline=BG, width=2)
        fl = fonte('JetBrainsMono-Bold.ttf', 17)
        d.text((gx0, gy1 + 8), 'Ibovespa no dia ·', font=fl, fill=MUTED)
        xl = gx0 + d.textlength('Ibovespa no dia · ', font=fl)
        d.ellipse([xl, gy1 + 13, xl + 11, gy1 + 24], fill=ORANGE)
        d.text((xl + 18, gy1 + 8), 'manchete de alto impacto', font=fl, fill=MUTED)
    # manchete que mais mexeu
    if top:
        d.text((M, 350), f'A NOTÍCIA QUE MAIS MEXEU · {top["h"]}', font=fonte('JetBrainsMono-Bold.ttf', 22), fill=ORANGE)
        ft = fonte('InterDisplay-Bold.otf', 38)
        linhas = _quebra(d, top['t'], ft, W - 2 * M, 3)
        for i, l in enumerate(linhas):
            d.text((M, 388 + i * 48), l, font=ft, fill=WHITE)
        reac = ' · '.join(x for x in (f'Ibovespa {_pct(top["ib"])} em 30 min' if top.get('ib') is not None else '',
                                       f'dólar {_pct(top["dl"])}' if top.get('dl') is not None else '') if x)
        if reac:
            d.text((M, 388 + len(linhas) * 48 + 12), reac, font=fonte('JetBrainsMono-Bold.ttf', 22), fill=TEAL_L)
    d.text((M, H - 46), 'lectnex.com.br', font=fonte('JetBrainsMono-Bold.ttf', 24), fill=TEAL_L)
    d.text((M + 250, H - 44), 'conteúdo educacional · não é recomendação', font=fonte('JetBrainsMono-Bold.ttf', 20), fill=MUTED)
    im.save(saida, quality=86, optimize=True, progressive=True)
    return saida
