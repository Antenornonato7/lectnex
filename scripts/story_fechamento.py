"""Story do fechamento (1080×1920): Ibovespa, dólar, maiores altas e baixas, placar do termômetro e agenda de amanhã.
Lê o resumo que coletor/fechamento.py grava (FECH_JSON) e envia no Telegram PRIVADO do dono.
Uso: python3 scripts/story_fechamento.py resumo.json [saida.png] [--previa "texto da faixa de prévia"]
"""
import datetime as dt
import json
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from og_leitura import BG, CARD, DIAS, LINE, MUTED, ORANGE, TEAL_L, VERDE, VERMELHO, WHITE, fonte, quebrar  # noqa: E402
from story_leitura import H, M, W, enviar, tracejado  # noqa: E402

SETA = {'bullish': '▲ alta', 'bearish': '▼ baixa', 'neutro': '● neutro'}


def pct(v):
    return ('+' if v > 0 else '−' if v < 0 else '') + f'{abs(v):.2f}%'.replace('.', ',')


def cor(v):
    return VERDE if v > 0 else VERMELHO if v < 0 else MUTED


def gerar(r, saida, previa=None):
    im = Image.new('RGB', (W, H), BG)
    dr = ImageDraw.Draw(im)
    for x in range(0, W, 48):
        dr.line([(x, 0), (x, H)], fill='#0A1422')
    for y in range(0, H, 48):
        dr.line([(0, y), (W, y)], fill='#0A1422')
    dr.rectangle([0, 0, 14, H], fill=TEAL_L)

    y = 250
    try:
        logo = Image.open('assets/brand/icon-192.png').convert('RGBA').resize((76, 76))
        im.paste(logo, (M, y), logo)
    except Exception:
        pass
    fb = fonte('InterDisplay-Bold.otf', 50)
    dr.text((M + 96, y + 8), 'Lect', font=fb, fill=WHITE)
    dr.text((M + 96 + dr.textlength('Lect', font=fb), y + 8), 'nex', font=fb, fill=TEAL_L)
    dia = dt.date.fromisoformat(r['data'])
    y += 130
    dr.text((M, y), f'FECHAMENTO · {DIAS[dia.weekday()]} {dia:%d/%m}', font=fonte('JetBrainsMono-Bold.ttf', 32), fill=TEAL_L)
    if previa:
        fp = fonte('JetBrainsMono-Bold.ttf', 24)
        tw = dr.textlength(previa, font=fp)
        dr.rectangle([W - M - tw - 28, y - 4, W - M, y + 38], fill=ORANGE)
        dr.text((W - M - tw - 14, y + 2), previa, font=fp, fill=BG)

    # Ibovespa e dólar em destaque
    y += 70
    fl, fn, fv = fonte('JetBrainsMono-Bold.ttf', 26), fonte('InterDisplay-Bold.otf', 72), fonte('JetBrainsMono-Bold.ttf', 44)
    for chave, nome, fmt in (('ibov', 'IBOVESPA', lambda p: f'{p:,.0f}'.replace(',', '.')), ('dolar', 'DÓLAR À VISTA', lambda p: 'R$ ' + f'{p:.3f}'.replace('.', ','))):
        v = r.get(chave)
        if not v:
            continue
        dr.rectangle([M, y, W - M, y + 170], fill=CARD, outline=LINE, width=2)
        dr.rectangle([M, y, M + 8, y + 170], fill=cor(v['var']))
        dr.text((M + 36, y + 24), nome, font=fl, fill=MUTED)
        dr.text((M + 36, y + 62), fmt(v['preco']), font=fn, fill=WHITE)
        t = pct(v['var'])
        dr.text((W - M - 36 - dr.textlength(t, font=fv), y + 80), t, font=fv, fill=cor(v['var']))
        y += 194

    # maiores altas e baixas
    if r.get('altas') and r.get('baixas'):
        y += 10
        fa = fonte('JetBrainsMono-Bold.ttf', 30)
        col = (W - 2 * M - 24) // 2
        for i, (titulo, lista) in enumerate((('MAIORES ALTAS', r['altas']), ('MAIORES BAIXAS', r['baixas']))):
            x = M + i * (col + 24)
            dr.text((x, y), titulo, font=fl, fill=MUTED)
            yy = y + 46
            for tk, v in lista[:3]:
                dr.text((x, yy), tk, font=fa, fill=WHITE)
                t = pct(v)
                dr.text((x + col - dr.textlength(t, font=fa), yy), t, font=fa, fill=cor(v))
                yy += 46
        y += 46 + 46 * 3 + 20

    # antes × depois: o histórico da manhã contra o que aconteceu hoje (dia de evento forte)
    ad = r.get('antes_depois')
    if ad and y < 1200:
        y += 18
        dr.text((M, y), f'ANTES × DEPOIS · {ad["evento"].upper()}'[:40], font=fl, fill=ORANGE)
        y += 48
        fa = fonte('Inter-Medium.otf', 30)
        sp = {'acima': 'Veio ACIMA do consenso', 'abaixo': 'Veio ABAIXO do consenso', 'em linha': 'Veio em linha com o consenso'}.get(ad.get('surpresa'))
        if sp:
            dr.text((M, y), sp + (f' ({ad["resultado"]} × {ad["consenso"]})' if ad.get('resultado') and ad.get('consenso') else ''), font=fa, fill=WHITE)
            y += 44
        nomes = {'win': 'Ibovespa', 'wdo': 'Dólar'}
        fj = fonte('JetBrainsMono-Bold.ttf', 28)
        for k in ('win', 'wdo'):
            h = (ad.get('hist') or {}).get(k)
            hj = (ad.get('hoje') or {}).get(k)
            if not h and hj is None:
                continue
            t1 = f'{nomes[k]}: subiu em {h["sobe"]}% das {h["n"]} vezes' if h else f'{nomes[k]}:'
            dr.text((M, y), t1, font=fa, fill=MUTED)
            if hj is not None:
                t2 = f'hoje {pct(hj)}'
                dr.text((W - M - dr.textlength(t2, font=fj), y + 2), t2, font=fj, fill=cor(hj))
            y += 44
        if not ad.get('hoje'):
            dr.text((M, y), 'Reação de hoje: medida na abertura de amanhã', font=fonte('Inter-Medium.otf', 26), fill=MUTED)
            y += 40
        y += 12

    # termômetro da manhã × fechamento
    term = r.get('termometro') or {}
    if term and y + 150 < 1440:
        y += 6
        dr.text((M, y), 'TERMÔMETRO DA MANHÃ', font=fl, fill=ORANGE)
        y += 48
        ft = fonte('Inter-Medium.otf', 34)
        for k in ('win', 'wdo'):
            if k not in term:
                continue
            t = term[k]
            ok = t.get('acerto')
            txt = f'{k.upper()} {SETA.get(t.get("leitura"), "")}  →  '
            fj = fonte('JetBrainsMono-Bold.ttf', 34)
            dr.text((M, y), txt, font=fj, fill=WHITE)
            dr.text((M + dr.textlength(txt, font=fj), y), 'acertou' if ok else 'errou', font=fj, fill=VERDE if ok else VERMELHO)
            y += 50
        p = r.get('placar')
        if p and p.get('tot') and y + 48 < 1440:
            s = f'Placar dos últimos {p["n"]} pregões: {p["ok"]}/{p["tot"]} ({p["ok"] / p["tot"] * 100:.0f}%)' if p['n'] > 1 else f'Placar do 1º pregão: {p["ok"]}/{p["tot"]}'
            dr.text((M, y + 4), s, font=fonte('Inter-Medium.otf', 28), fill=MUTED)
            y += 48

    # agenda do próximo pregão, se couber
    ag = r.get('agenda')
    limite = 1440
    if ag and ag.get('eventos') and y + 110 < limite:
        y += 18
        dr.text((M, y), ag['nome'].upper(), font=fl, fill=TEAL_L)
        y += 46
        fh, fe = fonte('JetBrainsMono-Bold.ttf', 28), fonte('Inter-Medium.otf', 32)
        for hora, ev, forte in ag['eventos']:
            linhas = quebrar(dr, ev, fe, W - 2 * M - 170, 1)
            if y + 44 > limite:
                break
            dr.text((M, y + 2), hora[:8], font=fh, fill=TEAL_L)
            dr.text((M + 170, y), linhas[0], font=fe, fill=ORANGE if forte else WHITE)
            y += 48

    tracejado(dr, (M, 1480, W - M, 1630), '#334155')
    fs = fonte('JetBrainsMono-Bold.ttf', 26)
    s = 'COLOQUE AQUI O STICKER DE LINK'
    dr.text(((W - dr.textlength(s, font=fs)) / 2, 1540), s, font=fs, fill='#475569')
    fr = fonte('Inter-Medium.otf', 26)
    for i, txt in enumerate(('Cotações com atraso de ~30 min · conteúdo educacional', 'Termômetro: WIN medido pelo Ibovespa e WDO pelo dólar à vista')):
        dr.text(((W - dr.textlength(txt, font=fr)) / 2, 1660 + i * 38), txt, font=fr, fill=MUTED)
    im.save(saida, 'PNG', optimize=True)
    return saida


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    previa = sys.argv[sys.argv.index('--previa') + 1] if '--previa' in sys.argv else None
    if previa in args:
        args.remove(previa)
    r = json.load(open(args[0], encoding='utf-8'))
    saida = args[1] if len(args) > 1 else 'story-fechamento.png'
    gerar(r, saida, previa)
    dia = dt.date.fromisoformat(r['data'])
    legenda = (f'🔔 <b>Story do fechamento pronto</b> · {DIAS[dia.weekday()].lower()} {dia:%d/%m}\n\n'
               + ('<i>Prévia do formato, com o fechamento do último pregão.</i>\n\n' if previa else '')
               + 'No Instagram: poste a imagem e adicione o <b>sticker de link</b> na área tracejada com '
               '<code>lectnex.com.br</code> (texto do sticker: "Mercado Hoje").')
    enviar(saida, legenda)


if __name__ == '__main__':
    main()
