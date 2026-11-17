"""Post "Você teria lucrado neste pregão?" (1080×1350, feed) para o pregão da semana do simulador: o gráfico real até o meio do
pregão e o resto escondido, com a chamada para jogar em lectnex.com.br/simulador. Também gera a legenda e o texto do X.

Uso: python3 scripts/simulador_post.py AAAA-MM-DD win|wdo saida.jpg legenda.txt x.txt
"""
import json
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from og_leitura import BG, CARD, LINE, MUTED, ORANGE, TEAL_L, VERDE, VERMELHO, WHITE, fonte, quebrar  # noqa: E402

W, H, M = 1080, 1350, 80
RAIZ = os.path.join(os.path.dirname(__file__), '..')


def minutos(hm):
    h, m = map(int, hm.split(':'))
    return h * 60 + m


def gerar(dia, ativo, saida):
    base = 'dias' if os.path.exists(os.path.join(RAIZ, 'data', 'dias', f'{dia}.json')) else 'sim'
    j = json.load(open(os.path.join(RAIZ, 'data', base, f'{dia}.json'), encoding='utf-8'))
    s = j['ibov' if ativo == 'win' else 'dolar']
    pts = [(minutos(h), v) for h, v in s['pontos'] if ativo == 'win' or minutos(h) <= 18 * 60 + 25]
    corte = pts[0][0] + (pts[-1][0] - pts[0][0]) * 0.45
    vis = [p for p in pts if p[0] <= corte]
    im = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(im)
    for x in range(0, W, 60):
        d.line([(x, 0), (x, H)], fill='#0A1422')
    for y in range(0, H, 60):
        d.line([(0, y), (W, y)], fill='#0A1422')
    d.rectangle([0, 0, W, 12], fill=ORANGE)
    try:
        logo = Image.open(os.path.join(RAIZ, 'assets', 'brand', 'icon-192.png')).convert('RGBA').resize((64, 64))
        im.paste(logo, (M, 70), logo)
    except Exception:
        pass
    fb = fonte('InterDisplay-Bold.otf', 44)
    d.text((M + 80, 78), 'Lect', font=fb, fill=WHITE)
    d.text((M + 80 + d.textlength('Lect', font=fb), 78), 'nex', font=fb, fill=TEAL_L)
    rot = 'SIMULADOR DE PREGÃO'
    fm = fonte('JetBrainsMono-Bold.ttf', 26)
    d.text((W - M - d.textlength(rot, font=fm), 92), rot, font=fm, fill=MUTED)
    nome = 'MINI ÍNDICE (WIN)' if ativo == 'win' else 'MINI DÓLAR (WDO)'
    d.text((M, 200), f'PREGÃO DA SEMANA · {nome}', font=fonte('JetBrainsMono-Bold.ttf', 30), fill=TEAL_L)
    ft = fonte('InterDisplay-Bold.otf', 84)
    for i, l in enumerate(quebrar(d, 'Você teria lucrado neste pregão?', ft, W - 2 * M, 2)):
        d.text((M, 250 + i * 96), l, font=ft, fill=WHITE)
    # gráfico
    gx0, gx1, gy0, gy1 = M, W - M, 500, 1000
    ys = [v for _, v in vis]  # só a parte visível: a escala não entrega o resto do dia
    lo, hi = min(ys), max(ys)
    pad = (hi - lo) * 0.35 or hi * 0.002
    lo, hi = lo - pad, hi + pad
    X = lambda t: gx0 + 20 + (t - pts[0][0]) / max(1, pts[-1][0] - pts[0][0]) * (gx1 - gx0 - 40)
    Y = lambda v: gy0 + 20 + (hi - v) / (hi - lo) * (gy1 - gy0 - 40)
    d.rectangle([gx0, gy0, gx1, gy1], fill=CARD, outline=LINE, width=2)
    cor = VERDE if vis[-1][1] >= (s.get('anterior') or vis[0][1]) else VERMELHO
    d.line([(X(t), Y(v)) for t, v in vis], fill=cor, width=6, joint='curve')
    xc = X(vis[-1][0])
    d.ellipse([xc - 10, Y(vis[-1][1]) - 10, xc + 10, Y(vis[-1][1]) + 10], fill=cor)
    for yy in range(gy0 + 10, gy1 - 10, 18):
        d.line([(xc + 24, yy), (xc + 24, yy + 9)], fill=ORANGE, width=3)
    d.rectangle([xc + 30, gy0 + 2, gx1 - 2, gy1 - 2], fill='#0D1B2E')
    fq = fonte('InterDisplay-Bold.otf', 200)
    cx = (xc + 30 + gx1) / 2
    d.text((cx - d.textlength('?', font=fq) / 2, (gy0 + gy1) / 2 - 130), '?', font=fq, fill=ORANGE)
    fp = fonte('JetBrainsMono-Bold.ttf', 26)
    for k, t1 in enumerate(('e agora?', 'compra, vende', 'ou espera?')):
        d.text((cx - d.textlength(t1, font=fp) / 2, (gy0 + gy1) / 2 + 100 + k * 36), t1, font=fp, fill=MUTED if k else WHITE)
    h0 = f'{vis[0][0] // 60:02d}h'
    hc = f'{vis[-1][0] // 60:02d}h{vis[-1][0] % 60:02d}'
    d.text((gx0 + 20, gy1 + 14), h0, font=fp, fill=MUTED)
    d.text((xc - d.textlength(hc, font=fp) / 2, gy1 + 14), hc, font=fp, fill=ORANGE)
    # chamada
    d.rectangle([M, 1110, W - M, 1230], fill=ORANGE)
    fc = fonte('InterDisplay-Bold.otf', 52)
    tc = 'Jogue grátis: lectnex.com.br/simulador'
    while d.textlength(tc, font=fc) > W - 2 * M - 40:
        fc = fonte('InterDisplay-Bold.otf', fc.size - 2)
    d.text(((W - d.textlength(tc, font=fc)) / 2, 1146), tc, font=fc, fill=BG)
    nota = 'dia real · dinheiro fictício · conteúdo educacional'
    d.text(((W - d.textlength(nota, font=fp)) / 2, 1270), nota, font=fp, fill=MUTED)
    im.save(saida, 'JPEG', quality=90, optimize=True)


def textos(ativo, link='https://lectnex.com.br/simulador'):
    nome = 'mini índice' if ativo == 'win' else 'mini dólar'
    leg = '\n'.join([f'🎮 Você teria lucrado neste pregão de {nome}?', '',
                     'O gráfico é de um dia REAL, até a metade do pregão. Daqui pra frente, a decisão é sua: comprar, vender ou esperar?',
                     'Jogue este e outros 55 pregões inteiros no simulador grátis, com as manchetes aparecendo no horário, e veja seus erros de risco no fim.', '',
                     '👉 lectnex.com.br/simulador (sem cadastro)', '💬 Ranking da semana no Discord: discord.gg/kM6YcQA82P', '',
                     'Comenta: o que você faria agora? 👇', '', 'Dinheiro fictício. Conteúdo educacional, não é recomendação.',
                     f'#daytrade #{"miniindice" if ativo == "win" else "minidolar"} #trader #b3 #simulador #bolsadevalores'])
    x = '\n\n'.join([f'🎮 Pregão real de {nome}, até a metade. E agora: compra, vende ou espera?',
                     f'Jogue o dia inteiro grátis, com as manchetes no horário:\n{link}',
                     'Ranking no Discord: https://discord.gg/kM6YcQA82P'])
    return leg, x


if __name__ == '__main__':
    dia, ativo, saida, arq_leg, arq_x = sys.argv[1:6]
    gerar(dia, ativo, saida)
    leg, x = textos(ativo)
    open(arq_leg, 'w', encoding='utf-8').write(leg)
    open(arq_x, 'w', encoding='utf-8').write(x)
    print(f'Post do simulador: {saida}')
