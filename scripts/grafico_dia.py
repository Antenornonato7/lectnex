"""Post de feed 1080×1350: gráfico do dia (Ibovespa ou dólar, o que mais se mexeu) com as 3 manchetes seguidas
dos maiores movimentos em 30 min marcadas no horário. Enviado no Telegram PRIVADO do dono no fechamento.
Uso: python3 scripts/grafico_dia.py mercado.json [saida.png]   (mercado.json = campo 'mercado' do ao-vivo)
"""
import datetime as dt
import json
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from og_leitura import BG, CARD, DIAS, LINE, MUTED, ORANGE, TEAL_L, VERDE, VERMELHO, WHITE, fonte, quebrar  # noqa: E402
from story_leitura import enviar  # noqa: E402

W, H, M = 1080, 1350, 72


def pct(v):
    return ('+' if v > 0 else '−' if v < 0 else '') + f'{abs(v):.2f}%'.replace('.', ',')


def minutos(hm):
    h, m = map(int, hm.split(':'))
    return h * 60 + m


def escolher(m):
    """Ativo com o maior movimento do dia; manchetes com maior reação nesse ativo."""
    def var(k):
        s = m.get(k) or {}
        p = s.get('pontos') or []
        return (p[-1][1] / (s.get('anterior') or p[0][1]) - 1) * 100 if p else None
    vi, vd = var('ibov'), var('dolar')
    k = 'ibov' if (vi is not None and (vd is None or abs(vi) >= abs(vd) * 1.5)) else 'dolar'  # dólar anda menos: peso 1,5
    if (m.get(k) or {}).get('pontos') is None:
        k = 'ibov' if k == 'dolar' else 'dolar'
    campo = 'ibov30' if k == 'ibov' else 'dolar30'
    mks = [x for x in m.get('marcadores', []) if x.get(campo) is not None]
    mks = sorted(mks, key=lambda x: -abs(x[campo]))[:3]
    return k, campo, sorted(mks, key=lambda x: x['hora']), var(k)


def gerar(m, saida):
    k, campo, mks, vdia = escolher(m)
    s = m[k]
    pts, base = s['pontos'], s.get('anterior') or s['pontos'][0][1]
    nome = 'IBOVESPA' if k == 'ibov' else 'DÓLAR À VISTA'
    im = Image.new('RGB', (W, H), BG)
    dr = ImageDraw.Draw(im)
    for x in range(0, W, 48):
        dr.line([(x, 0), (x, H)], fill='#0A1422')
    for y in range(0, H, 48):
        dr.line([(0, y), (W, y)], fill='#0A1422')
    dr.rectangle([0, 0, W, 10], fill=ORANGE)
    try:
        logo = Image.open('assets/brand/icon-192.png').convert('RGBA').resize((56, 56))
        im.paste(logo, (M, 52), logo)
    except Exception:
        pass
    fb = fonte('InterDisplay-Bold.otf', 38)
    dr.text((M + 72, 58), 'Lect', font=fb, fill=WHITE)
    dr.text((M + 72 + dr.textlength('Lect', font=fb), 58), 'nex', font=fb, fill=TEAL_L)
    d = dt.date.fromisoformat(m['data'])
    dr.text((M, 140), f'NOTÍCIA × PREÇO · {DIAS[d.weekday()]} {d:%d/%m}', font=fonte('JetBrainsMono-Bold.ttf', 28), fill=ORANGE)
    dr.text((M, 180), 'O que mexeu no', font=fonte('InterDisplay-Bold.otf', 64), fill=WHITE)
    dr.text((M, 252), ('Ibovespa' if k == 'ibov' else 'dólar') + ' hoje', font=fonte('InterDisplay-Bold.otf', 64), fill=WHITE)
    cor = VERDE if vdia >= 0 else VERMELHO
    t = pct(vdia)
    fv = fonte('InterDisplay-Bold.otf', 64)
    dr.text((W - M - dr.textlength(t, font=fv), 252), t, font=fv, fill=cor)

    # gráfico
    gx0, gx1, gy0, gy1 = M + 4, W - M - 120, 370, 790
    dr.rectangle([M - 12, gy0 - 24, W - M + 12, gy1 + 50], fill=CARD, outline=LINE, width=2)
    xs = [minutos(p[0]) for p in pts]
    x0, x1 = min(600, xs[0]), max(1080, xs[-1])
    ys = [p[1] for p in pts] + [base]
    lo, hi = min(ys), max(ys)
    pad = (hi - lo) * 0.1 or base * 0.002
    X = lambda v: gx0 + (v - x0) / (x1 - x0) * (gx1 - gx0)
    Y = lambda v: gy0 + (1 - (v - (lo - pad)) / ((hi + pad) - (lo - pad))) * (gy1 - gy0)
    fm = fonte('JetBrainsMono-Bold.ttf', 20)
    for h in range(10, 19, 2):
        x = X(h * 60)
        dr.line([(x, gy0), (x, gy1)], fill='#13233A')
        dr.text((x - 14, gy1 + 12), f'{h}h', font=fm, fill=MUTED)
    yb = Y(base)
    for x in range(int(gx0), int(gx1), 14):
        dr.line([(x, yb), (x + 7, yb)], fill='#475569', width=2)
    dr.text((gx1 + 10, yb - 12), 'ant.', font=fm, fill=MUTED)
    linha = [(X(minutos(p[0])), Y(p[1])) for p in pts]
    dr.polygon(linha + [(linha[-1][0], gy1), (linha[0][0], gy1)], fill=(16, 50, 40) if vdia >= 0 else (60, 18, 30))
    dr.line(linha, fill=cor, width=4, joint='curve')
    ult = pts[-1][1]
    dr.text((gx1 + 10, Y(ult) - 12), f'{ult:,.0f}'.replace(',', '.') if k == 'ibov' else f'{ult:.3f}'.replace('.', ','), font=fm, fill=cor)
    fn = fonte('InterDisplay-Bold.otf', 28)
    for i, mk in enumerate(mks, 1):
        t0 = minutos(mk['hora'])
        antes = [p for p in pts if minutos(p[0]) <= t0] or pts[:1]
        x, y = X(t0), Y(antes[-1][1])
        for yy in range(gy0, gy1, 10):
            dr.line([(x, yy), (x, yy + 5)], fill=ORANGE, width=2)
        dr.ellipse([x - 22, y - 22, x + 22, y + 22], fill=ORANGE, outline=BG, width=4)
        dr.text((x - dr.textlength(str(i), font=fn) / 2, y - 17), str(i), font=fn, fill=BG)

    # legenda das manchetes
    y = 870
    if not mks:
        dr.text((M, y), 'Sem manchetes com reação medida neste dia.', font=fonte('Inter-Medium.otf', 32), fill=MUTED)
    fh, ft, fr = fonte('JetBrainsMono-Bold.ttf', 24), fonte('Inter-Medium.otf', 30), fonte('JetBrainsMono-Bold.ttf', 26)
    for i, mk in enumerate(mks, 1):
        dr.ellipse([M, y + 2, M + 40, y + 42], fill=ORANGE)
        dr.text((M + 20 - dr.textlength(str(i), font=fn) / 2, y + 5), str(i), font=fn, fill=BG)
        dr.text((M + 58, y + 6), f'{mk["hora"]} · {mk["fonte"]}', font=fh, fill=MUTED)
        r = mk[campo]
        tr = f'{pct(r)} em 30 min'
        dr.text((W - M - dr.textlength(tr, font=fr), y + 4), tr, font=fr, fill=VERDE if r > 0 else VERMELHO)
        yy = y + 42
        for l in quebrar(dr, mk['titulo'], ft, W - 2 * M - 58, 2):
            dr.text((M + 58, yy), l, font=ft, fill=WHITE)
            yy += 38
        y = yy + 22
    fs = fonte('Inter-Medium.otf', 22)
    for i, l in enumerate(('Variação do último preço antes da manchete até 30 min depois.',
                           'O movimento seguinte não prova que a notícia foi a causa.',
                           'Cotações de 5 min (Yahoo Finance) · lectnex.com.br/hoje · conteúdo educacional')):
        dr.text(((W - dr.textlength(l, font=fs)) / 2, H - 116 + i * 32), l, font=fs, fill=MUTED)
    im.save(saida, 'PNG', optimize=True)
    return k, mks, vdia


def main():
    m = json.load(open(sys.argv[1], encoding='utf-8'))
    saida = sys.argv[2] if len(sys.argv) > 2 else 'grafico-dia.png'
    if not (m.get('ibov') or m.get('dolar')):
        print('Sem série do dia: post não gerado.')
        return
    k, mks, vdia = gerar(m, saida)
    d = dt.date.fromisoformat(m['data'])
    nome = 'Ibovespa' if k == 'ibov' else 'dólar'
    lst = '\n'.join(f'{i}. {x["hora"]} · {x["titulo"]}' for i, x in enumerate(mks, 1))
    legenda = (f'🗞️ <b>Post do dia: notícia × preço</b> · {DIAS[d.weekday()].lower()} {d:%d/%m}\n\n'
               '<b>Sugestão de legenda:</b>\n'
               f'O que mexeu no {nome} hoje ({pct(vdia)}): marcamos no gráfico as manchetes seguidas dos maiores movimentos em 30 minutos.\n'
               f'{lst}\n'
               'O movimento seguinte não prova causa, mas mostra como o mercado reage à notícia. Veja o dia completo no link da bio. '
               'Conteúdo educacional. #ibovespa #dolar #daytrade #miniindice #minidolar #b3')
    enviar(saida, legenda)


if __name__ == '__main__':
    main()
