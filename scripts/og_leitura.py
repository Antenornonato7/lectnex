"""Imagem de compartilhamento (1200×630) de cada Leitura do Dia → assets/og/leitura-AAAA-MM-DD.jpg.
Título, data, termômetro WIN/WDO (ou próximo pregão) nas cores da marca. Requer Pillow (pip install pillow).
Uso: python3 scripts/og_leitura.py [data/leitura/AAAA-MM-DD.json ...]  (sem argumentos: todas as edições sem imagem)."""
import datetime as dt, glob, json, os, sys
from PIL import Image, ImageDraw, ImageFont

F = os.path.join(os.path.dirname(__file__), 'fonts')
NAVY, BG, CARD, TEAL, TEAL_L, ORANGE, WHITE, MUTED, LINE = '#0C1A2A', '#060D17', '#0B1626', '#009988', '#00B4A2', '#F39200', '#FFFFFF', '#94A3B8', '#1E293B'
VERDE, VERMELHO = '#10B981', '#F43F5E'
DIAS = ['SEGUNDA', 'TERÇA', 'QUARTA', 'QUINTA', 'SEXTA', 'SÁBADO', 'DOMINGO']
TERM = {'bullish': ('▲ VIÉS DE ALTA', VERDE), 'bearish': ('▼ VIÉS DE BAIXA', VERMELHO), 'neutro': ('● NEUTRO', MUTED)}


def fonte(nome, tam):
    return ImageFont.truetype(os.path.join(F, nome), tam)


def quebrar(draw, texto, f, largura, max_linhas):
    palavras, linhas, atual = texto.split(), [], ''
    for p in palavras:
        teste = (atual + ' ' + p).strip()
        if draw.textlength(teste, font=f) <= largura:
            atual = teste
        else:
            linhas.append(atual); atual = p
    linhas.append(atual)
    if len(linhas) > max_linhas:
        linhas = linhas[:max_linhas]
        while draw.textlength(linhas[-1] + '…', font=f) > largura:
            linhas[-1] = linhas[-1].rsplit(' ', 1)[0]
        linhas[-1] += '…'
    return linhas


def gerar(d, saida):
    W, H = 1200, 630
    im = Image.new('RGB', (W, H), BG)
    dr = ImageDraw.Draw(im)
    # grade sutil
    for x in range(0, W, 40):
        dr.line([(x, 0), (x, H)], fill='#0A1422')
    for y in range(0, H, 40):
        dr.line([(0, y), (W, y)], fill='#0A1422')
    dr.rectangle([0, 0, 12, H], fill=ORANGE)
    # marca
    try:
        logo = Image.open('assets/brand/icon-192.png').convert('RGBA').resize((64, 64))
        im.paste(logo, (64, 52), logo)
    except Exception:
        pass
    dr.text((144, 58), 'Lect', font=fonte('InterDisplay-Bold.otf', 40), fill=WHITE)
    lw = dr.textlength('Lect', font=fonte('InterDisplay-Bold.otf', 40))
    dr.text((144 + lw, 58), 'nex', font=fonte('InterDisplay-Bold.otf', 40), fill=TEAL_L)
    dia = dt.date.fromisoformat(d['data'])
    rot = f'LEITURA DO DIA · {DIAS[dia.weekday()]} {dia:%d/%m/%Y}'
    fm = fonte('JetBrainsMono-Bold.ttf', 24)
    dr.text((W - 64 - dr.textlength(rot, font=fm), 72), rot, font=fm, fill=ORANGE)
    # título
    ft = fonte('InterDisplay-Bold.otf', 64)
    linhas = quebrar(dr, d.get('titulo', ''), ft, W - 128, 3)
    y = 170
    for l in linhas:
        dr.text((64, y), l, font=ft, fill=WHITE); y += 78
    # rodapé: termômetro ou próximo pregão
    y0 = H - 150
    dr.rectangle([64, y0, W - 64, H - 56], fill=CARD, outline=LINE, width=2)
    fl, fv = fonte('JetBrainsMono-Bold.ttf', 22), fonte('JetBrainsMono-Bold.ttf', 34)
    t = d.get('termometro')
    if t:
        x = 96
        for k in ('win', 'wdo'):
            if k not in t: continue
            txt, cor = TERM.get(t[k].get('leitura'), TERM['neutro'])
            dr.text((x, y0 + 18), k.upper(), font=fl, fill=MUTED)
            dr.text((x, y0 + 46), txt, font=fv, fill=cor)
            x += 400
    elif d.get('proximo_pregao'):
        p = dt.date.fromisoformat(d['proximo_pregao']['data'])
        dr.text((96, y0 + 18), 'SEM PREGÃO HOJE', font=fl, fill=MUTED)
        dr.text((96, y0 + 46), f'Próximo pregão: {DIAS[p.weekday()].lower()} {p:%d/%m}', font=fv, fill=WHITE)
    fs = fonte('Inter-Medium.otf', 22)
    s = 'WIN · WDO · DI'
    dr.text((W - 96 - dr.textlength(s, font=fs), y0 + 34), s, font=fs, fill=TEAL_L)
    dr.text((W - 96 - dr.textlength('educacional', font=fs), y0 + 62), 'educacional', font=fs, fill=MUTED)
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    im.save(saida, 'JPEG', quality=86, optimize=True, progressive=True)


def main():
    arqs = sys.argv[1:] or sorted(glob.glob('data/leitura/*.json'))
    feitos = []
    for a in arqs:
        d = json.load(open(a, encoding='utf-8'))
        out = f'assets/og/leitura-{d["data"]}.jpg'
        if sys.argv[1:] or not os.path.exists(out):
            gerar(d, out); feitos.append(out)
    print(f'::notice::Imagens de compartilhamento: {", ".join(feitos) or "nenhuma nova"}')


if __name__ == '__main__':
    main()
