"""Imagem do resultado de cada divulgação (1200×630, JPG) → assets/og/dados/<dado>-<data>.jpg.

Serve de prévia da página (Open Graph) e vai junto nos posts (Discord e Telegram para o X).
Mostra: nome do dado, data e horário, "saiu X · consenso Y" com a seta da surpresa, a reação de WIN e WDO e,
quando o pregão está gravado em data/dias/, o mini gráfico do Ibovespa e do dólar até 1 h depois do dado.
"""
import datetime as dt
import json
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from og_leitura import BG, CARD, LINE, MUTED, ORANGE, TEAL_L, VERDE, VERMELHO, WHITE, fonte  # noqa: E402

PASTA = os.path.join(os.path.dirname(__file__), '..', 'assets', 'og', 'dados')
DIAS = ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo']


def _pct(v):
    return '—' if v is None else ('+' if v > 0 else '−' if v < 0 else '') + f'{abs(v):.2f}%'.replace('.', ',')


def _min(h):
    import re
    m = re.match(r'(\d{1,2})[h:](\d{2})?', h or '')
    return int(m.group(1)) * 60 + int(m.group(2) or 0) if m else None


def _serie(dia, chave, t0):
    try:
        d = json.load(open(os.path.join(os.path.dirname(__file__), '..', 'data', 'dias', f'{dia}.json'), encoding='utf-8'))
    except Exception:
        return []
    pts = [(_min(p[0]), p[1]) for p in (d.get(chave) or {}).get('pontos', []) if _min(p[0]) is not None]
    pts = [p for p in pts if t0 - 30 <= p[0] <= t0 + 60]
    if len(pts) < 4:
        return []
    ref = next((v for m, v in reversed(pts) if m <= t0), pts[0][1])
    return [(m, (v / ref - 1) * 100) for m, v in pts]


def gerar(r, evento, slug):
    os.makedirs(PASTA, exist_ok=True)
    saida = os.path.join(PASTA, f'{slug}.jpg')
    W, H, M = 1200, 630, 64
    im = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 12, H], fill=TEAL_L)
    dia = dt.date.fromisoformat(r['data'])
    d.text((M, 50), f'DIVULGAÇÃO · {DIAS[dia.weekday()].upper()} {dia:%d/%m/%Y}' + (f' · {r["hora"]}' if r.get('hora') else ''), font=fonte('JetBrainsMono-Bold.ttf', 26), fill=TEAL_L)
    ft = fonte('InterDisplay-Bold.otf', 64)
    nome = evento if d.textlength(evento, font=ft) < W - 2 * M else evento[:30] + '…'
    d.text((M, 92), nome, font=ft, fill=WHITE)
    # saiu × consenso
    sup = r.get('surpresa')
    fs, fc = fonte('InterDisplay-Bold.otf', 96), fonte('JetBrainsMono-Bold.ttf', 30)
    d.text((M, 186), str(r.get('resultado') or '—'), font=fs, fill=WHITE)
    x = M + d.textlength(str(r.get('resultado') or '—'), font=fs) + 28
    if r.get('consenso'):
        d.text((x, 214), f'consenso {r["consenso"]}', font=fc, fill=MUTED)
        x2 = x + d.textlength(f'consenso {r["consenso"]}', font=fc) + 24
        if sup in ('acima', 'abaixo', 'em linha'):
            rot = {'acima': '▲ ACIMA', 'abaixo': '▼ ABAIXO', 'em linha': '= EM LINHA'}[sup]
            fb = fonte('JetBrainsMono-Bold.ttf', 26)
            w = d.textlength(rot, font=fb) + 28
            d.rectangle([x2, 214, x2 + w, 254], fill=ORANGE if sup == 'acima' else '#3B82F6' if sup == 'abaixo' else MUTED)
            d.text((x2 + 14, 219), rot, font=fb, fill=BG)
    # reação
    janela = '1 h' if r.get('janela') == '1h' else '30 min'
    y = 330
    for i, (rot, k) in enumerate((('WIN', 'win'), ('WDO', 'wdo'))):
        bx = M + i * 300
        v = r.get(k)
        d.rectangle([bx, y, bx + 270, y + 140], fill=CARD, outline=LINE, width=2)
        d.text((bx + 20, y + 16), f'{rot} EM {janela.upper()}', font=fonte('JetBrainsMono-Bold.ttf', 22), fill=MUTED)
        d.text((bx + 20, y + 56), _pct(v), font=fonte('JetBrainsMono-Bold.ttf', 54), fill=MUTED if v is None else VERDE if v >= 0 else VERMELHO)
    # mini gráfico
    t0 = _min(r.get('hora'))
    gx0, gx1, gy0, gy1 = M + 620, W - M, y, y + 140
    series = [(TEAL_L, 'Ibovespa', _serie(r['data'], 'ibov', t0)), (ORANGE, 'dólar', _serie(r['data'], 'dolar', t0))] if t0 is not None else []
    series = [(c, n, s) for c, n, s in series if s]
    if series:
        d.rectangle([gx0, gy0, gx1, gy1], fill=CARD, outline=LINE, width=2)
        xs = [m for _, _, s in series for m, _ in s]
        ys = [v for _, _, s in series for _, v in s] + [0]
        lo, hi = min(ys), max(ys)
        pad = max(0.05, (hi - lo) * 0.15)
        lo, hi = lo - pad, hi + pad
        X = lambda m: gx0 + 16 + (m - min(xs)) / max(1, max(xs) - min(xs)) * (gx1 - gx0 - 32)
        Y = lambda v: gy0 + 14 + (hi - v) / (hi - lo) * (gy1 - gy0 - 28)
        if min(xs) <= t0 <= max(xs):
            d.line([(X(t0), gy0 + 8), (X(t0), gy1 - 8)], fill=MUTED, width=2)
        fl, lx = fonte('JetBrainsMono-Bold.ttf', 20), gx0 + 16
        for c, n, s in series:
            d.line([(X(m), Y(v)) for m, v in s], fill=c, width=4, joint='curve')
            d.text((lx, gy1 + 10), n, font=fl, fill=c)
            lx += d.textlength(n, font=fl) + 24
        d.text((lx, gy1 + 10), 'até 1 h depois do dado', font=fl, fill=MUTED)
    d.text((M, H - 60), 'lectnex.com.br', font=fonte('JetBrainsMono-Bold.ttf', 26), fill=TEAL_L)
    d.text((M + 260, H - 58), 'conteúdo educacional · não é recomendação', font=fonte('JetBrainsMono-Bold.ttf', 22), fill=MUTED)
    im.save(saida, quality=88)
    return saida
