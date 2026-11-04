"""Termo do dia: card 1080×1920 com um termo do glossário ligado à agenda de hoje, no Telegram PRIVADO do dono.

Escolha: o evento mais importante de hoje no calendário define o termo (ex.: Copom → "Copom", payroll → "Payroll").
Sem evento ligado, roda por uma lista fixa de termos do dia a dia do trader (muda a cada dia, sem repetir em ~1 mês).
Uso: python3 scripts/termo_dia.py [saida.png] [--data AAAA-MM-DD]
"""
import datetime as dt
import json
import os
import re
import sys
import unicodedata

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from og_leitura import BG, CARD, DIAS, LINE, MUTED, ORANGE, TEAL_L, WHITE, fonte, quebrar  # noqa: E402
from story_leitura import H, M, W, enviar, tracejado  # noqa: E402

BRT = dt.timezone(dt.timedelta(hours=-3))
# tipo do evento no calendário → termo do glossário
POR_EVENTO = {
    'copom': 'Copom', 'ata-copom': 'Copom', 'fomc': 'FOMC', 'payroll': 'Payroll', 'desemprego-eua': 'Payroll', 'salario-eua': 'Payroll',
    'cpi-eua': 'CPI', 'pce-eua': 'CPI', 'ipca': 'IPCA', 'ipca-15': 'IPCA', 'focus': 'Focus', 'vencimento-wdo': 'Rolagem',
    'vencimento-win': 'Rolagem', 'refunding-eua': 'Treasury 10 anos', 'ism-servicos': 'Consenso de mercado', 'ism-industrial': 'Consenso de mercado',
    'jolts': 'Surpresa (dado econômico)', 'adp': 'Surpresa (dado econômico)', 'caged': 'Juro real', 'bce': 'DXY', 'boe': 'DXY',
    'inflacao-zona-euro': 'DXY', 'pmi-china': 'Risk-on e risk-off', 'cpi-china': 'Risk-on e risk-off', 'eleicoes-eua': 'Volatilidade',
}
RODIZIO = ['Ajuste diário', 'PTAX', 'Stop loss', 'Drawdown', 'Slippage', 'Tick', 'Margem de garantia', 'Alavancagem', 'Gap', 'Leilão',
           'VWAP', 'Book de ofertas', 'Times & Trades', 'Agressão', 'Spread', 'Liquidez', 'Taxa de acerto', 'Payoff', 'Critério de Kelly',
           'Cupom cambial', 'Curva de juros', 'Inclinação da curva', 'DI1 (DI futuro)', 'Preço de ajuste', 'Circuit breaker', 'Prêmio de risco',
           'Carry trade', 'Mini índice (WIN)', 'Mini dólar (WDO)', 'IRRF (dedo-duro)', 'DARF']


def slug(s):
    s = unicodedata.normalize('NFD', s.lower()).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def escolher(hoje, termos, eventos):
    por_nome = {t['t']: t for t in termos}
    evs = sorted([e for e in eventos if e.get('data') == hoje.isoformat() and e.get('tipo') in POR_EVENTO],
                 key=lambda e: (-(e.get('importancia') or 1), list(POR_EVENTO).index(e['tipo'])))  # empate: ordem de POR_EVENTO (Copom, Fed, payroll… primeiro)
    for e in evs:
        t = por_nome.get(POR_EVENTO[e['tipo']])
        if t:
            return t, e
    lista = [por_nome[n] for n in RODIZIO if n in por_nome]
    return lista[hoje.toordinal() % len(lista)], None


def gerar(t, ev, hoje, saida):
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
    y += 130
    dr.text((M, y), f'TERMO DO DIA · {DIAS[hoje.weekday()]} {hoje:%d/%m}', font=fonte('JetBrainsMono-Bold.ttf', 32), fill=TEAL_L)

    y += 70
    nome = t['t']
    tam = 120
    while tam > 64 and any(dr.textlength(l, font=fonte('InterDisplay-Bold.otf', tam)) > W - 2 * M for l in quebrar(dr, nome, fonte('InterDisplay-Bold.otf', tam), 10 ** 6, 2)):
        tam -= 8
    ft = fonte('InterDisplay-Bold.otf', tam)
    for l in quebrar(dr, nome, ft, W - 2 * M, 2):
        dr.text((M, y), l, font=ft, fill=WHITE)
        y += int(tam * 1.12)
    dr.rectangle([M, y + 18, M + 140, y + 26], fill=ORANGE)
    y += 70

    fd = fonte('Inter-Medium.otf', 40)
    linhas = quebrar(dr, t['d'], fd, W - 2 * M, 9)
    for l in linhas:
        dr.text((M, y), l, font=fd, fill='#CBD5E1')
        y += 56

    if ev and y < 1300:
        y += 34
        txt = f'{(ev.get("hora") or "hoje")} · {ev["evento"]}'
        fe = fonte('Inter-Medium.otf', 32)
        el = quebrar(dr, txt, fe, W - 2 * M - 64, 2)
        alt = 92 + 42 * len(el)
        dr.rectangle([M, y, W - M, y + alt], fill=CARD, outline=LINE, width=2)
        dr.rectangle([M, y, M + 8, y + alt], fill=ORANGE)
        dr.text((M + 34, y + 24), 'POR QUE HOJE', font=fonte('JetBrainsMono-Bold.ttf', 26), fill=ORANGE)
        yy = y + 64
        for l in el:
            dr.text((M + 34, yy), l, font=fe, fill=WHITE)
            yy += 42

    tracejado(dr, (M, 1480, W - M, 1630), '#334155')
    fs = fonte('JetBrainsMono-Bold.ttf', 26)
    s = 'COLOQUE AQUI O STICKER DE LINK'
    dr.text(((W - dr.textlength(s, font=fs)) / 2, 1540), s, font=fs, fill='#475569')
    fr = fonte('Inter-Medium.otf', 28)
    r = 'Glossário completo em lectnex.com.br · conteúdo educacional'
    dr.text(((W - dr.textlength(r, font=fr)) / 2, 1660), r, font=fr, fill=MUTED)
    im.save(saida, 'PNG', optimize=True)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    hoje = dt.datetime.now(BRT).date()
    if '--data' in sys.argv:
        hoje = dt.date.fromisoformat(sys.argv[sys.argv.index('--data') + 1])
        args = [a for a in args if a != hoje.isoformat()]
    saida = args[0] if args else 'termo-do-dia.png'
    termos = json.load(open('data/glossario.json', encoding='utf-8'))['termos']
    eventos = json.load(open('data/calendario.json', encoding='utf-8')).get('eventos', [])
    t, ev = escolher(hoje, termos, eventos)
    gerar(t, ev, hoje, saida)
    print(f'Termo do dia: {t["t"]}' + (f' (ligado a: {ev["evento"]})' if ev else ' (rodízio)'))
    legenda = (f'📚 <b>Termo do dia</b> · {DIAS[hoje.weekday()].lower()} {hoje:%d/%m}: <b>{t["t"]}</b>\n'
               + (f'Ligado à agenda: {ev["evento"]}\n' if ev else '') +
               f'\nNo Instagram: poste nos stories e coloque o <b>sticker de link</b> na área tracejada com '
               f'<code>lectnex.com.br/glossario.html#{slug(t["t"])}</code> (texto do sticker: "Glossário").')
    enviar(saida, legenda)


if __name__ == '__main__':
    main()
