"""Banner do Discord com o fechamento do dia: pega o banner animado da marca (assets/discord/banner.gif), escreve
Ibovespa e dólar do dia em cada quadro e troca o banner do servidor. Roda no workflow do fechamento.
Uso: python3 scripts/discord_banner.py <fechamento.json> [saida.gif] [--so-gerar]
"""
import base64
import datetime as dt
import json
import os
import sys

from PIL import Image, ImageDraw, ImageSequence

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'coletor'))
from og_leitura import DIAS, fonte  # noqa: E402

VERDE, VERMELHO, BRANCO, CINZA, FUNDO = (0, 201, 181), (244, 63, 94), (255, 255, 255), (148, 163, 184), (5, 11, 20)


def pct(v):
    return ('+' if v > 0 else '−' if v < 0 else '') + f'{abs(v):.2f}%'.replace('.', ',')


def gerar(fech, saida):
    dia = dt.date.fromisoformat(fech['data'])
    itens = [(n, fech[k]) for k, n in (('ibov', 'IBOV'), ('dolar', 'DÓLAR')) if fech.get(k) and fech[k].get('var') is not None]
    if not itens:
        raise SystemExit('Sem Ibovespa nem dólar no fechamento: banner não trocado.')
    fl, fv, fd = fonte('JetBrainsMono-Bold.ttf', 22), fonte('JetBrainsMono-Bold.ttf', 34), fonte('JetBrainsMono-Bold.ttf', 18)
    base = Image.open(os.path.join(os.path.dirname(__file__), '..', 'assets', 'discord', 'banner.gif'))
    quadros, tempos = [], []
    for q in ImageSequence.Iterator(base):
        im = q.convert('RGB')
        d = ImageDraw.Draw(im, 'RGBA')
        x, y, h = 40, 452, 64
        rotulo = f'FECHAMENTO · {DIAS[dia.weekday()]} {dia:%d/%m}'
        larg = 24 + sum(d.textlength(n, font=fl) + 12 + d.textlength(pct(v['var']), font=fv) + 36 for n, v in itens)
        larg = max(larg, d.textlength(rotulo, font=fd) + 24)
        d.rectangle([x - 12, y - 34, x - 12 + larg, y + h - 10], fill=FUNDO + (215,))
        d.rectangle([x - 12, y - 34, x - 8, y + h - 10], fill=(0, 153, 136, 255))
        d.text((x, y - 28), rotulo, font=fd, fill=CINZA)
        cx = x
        for n, v in itens:
            d.text((cx, y + 8), n, font=fl, fill=BRANCO)
            cx += d.textlength(n, font=fl) + 12
            t = pct(v['var'])
            d.text((cx, y), t, font=fv, fill=VERDE if v['var'] >= 0 else VERMELHO)
            cx += d.textlength(t, font=fv) + 36
        quadros.append(im.quantize(colors=255, method=Image.Quantize.FASTOCTREE))
        tempos.append(q.info.get('duration', 90))
    quadros[0].save(saida, save_all=True, append_images=quadros[1:], duration=tempos, loop=0, optimize=True)
    return saida


def trocar(arq):
    import discord_post as dc
    if not dc.TOKEN:
        print('::notice::Sem DISCORD_BOT_TOKEN: banner gerado, não enviado.')
        return
    uri = 'data:image/gif;base64,' + base64.b64encode(open(arq, 'rb').read()).decode()
    try:
        dc._req('PATCH', f'/guilds/{dc.GUILD}', {'banner': uri})
        print('::notice::Banner do Discord atualizado com o fechamento do dia.')
    except Exception as e:
        print(f'::warning::Banner do Discord: {e}')


if __name__ == '__main__':
    fech = json.load(open(sys.argv[1], encoding='utf-8'))
    saida = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else os.path.join(os.environ.get('RUNNER_TEMP', '.'), 'banner-dia.gif')
    gerar(fech, saida)
    if '--so-gerar' not in sys.argv:
        trocar(saida)
