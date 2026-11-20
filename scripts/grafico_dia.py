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


def titulo_conclusao(m, k, vdia):
    """O título é a própria conclusão do dia (padrão aprovado em 19/11: um gráfico, uma conclusão)."""
    ult = m[k]['pontos'][-1][1]
    verbo = 'sobe' if vdia > 0 else 'cai' if vdia < 0 else 'fica estável'
    vv = f' {pct(vdia)[1:]}' if vdia else ''
    if k == 'ibov':
        return f'Ibovespa {verbo}{vv} e fecha aos {ult:,.0f} pontos'.replace(',', '.')
    return f'Dólar {verbo}{vv} e fecha a R$ {ult:.2f}'.replace('.', ',')


def gerar(m, saida):
    k, campo, mks, vdia = escolher(m)
    s = m[k]
    pts = [(minutos(h), v) for h, v in s['pontos'] if k == 'ibov' or minutos(h) <= 18 * 60 + 25]
    base = s.get('anterior') or pts[0][1]
    outro = 'dolar' if k == 'ibov' else 'ibov'
    so = m.get(outro) or {}
    vo = (so['pontos'][-1][1] / (so.get('anterior') or so['pontos'][0][1]) - 1) * 100 if so.get('pontos') else None
    cor = VERDE if vdia >= 0 else VERMELHO
    fmtv = (lambda v: f'{v:,.0f}'.replace(',', '.')) if k == 'ibov' else (lambda v: f'R$ {v:.2f}'.replace('.', ','))
    im = Image.new('RGB', (W, H), BG)
    dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, W, 10], fill=TEAL_L)
    fb = fonte('InterDisplay-Bold.otf', 40)
    dr.text((M, 60), 'Lect', font=fb, fill=WHITE)
    dr.text((M + dr.textlength('Lect', font=fb), 60), 'nex', font=fb, fill=TEAL_L)
    d = dt.date.fromisoformat(m['data'])
    tag = f'GRÁFICO DO DIA · {DIAS[d.weekday()]} {d:%d/%m}'
    dr.text((W - M - dr.textlength(tag, font=fonte('JetBrainsMono-Bold.ttf', 24)), 72), tag, font=fonte('JetBrainsMono-Bold.ttf', 24), fill=MUTED)
    ft = fonte('InterDisplay-Bold.otf', 74)
    y = 150
    for l in quebrar(dr, titulo_conclusao(m, k, vdia), ft, W - 2 * M, 3):
        dr.text((M, y), l, font=ft, fill=WHITE)
        y += 83
    sub = (f'{"Dólar" if outro == "dolar" else "Ibovespa"} {pct(vo)} no mesmo dia. ' if vo is not None else '') + \
          ('Ibovespa' if k == 'ibov' else 'Dólar comercial') + ', de 5 em 5 minutos.'
    for i2, l in enumerate(quebrar(dr, sub, fonte('Inter-Medium.otf', 34), W - 2 * M, 2)):
        dr.text((M, y + 10 + i2 * 44), l, font=fonte('Inter-Medium.otf', 34), fill=MUTED)
    gx0, gx1, gy0, gy1 = M, W - M - 160, y + 150, H - 230
    ys = [v for _, v in pts] + [base]
    lo, hi = min(ys), max(ys)
    pad = (hi - lo) * 0.12 or base * 0.002
    X = lambda t: gx0 + (t - pts[0][0]) / max(1, pts[-1][0] - pts[0][0]) * (gx1 - gx0)
    Y = lambda v: gy1 - (v - lo + pad) / (hi - lo + 2 * pad) * (gy1 - gy0)
    fm = fonte('JetBrainsMono-Bold.ttf', 22)
    dr.line([(gx0, Y(base)), (gx1, Y(base))], fill=LINE, width=2)
    dr.text((gx1 + 14, Y(base) - 14), 'ontem\n' + fmtv(base), font=fm, fill=MUTED)
    dr.line([(X(t), Y(v)) for t, v in pts], fill=cor, width=6, joint='curve')
    xe, ye = X(pts[-1][0]), Y(pts[-1][1])
    dr.ellipse([xe - 9, ye - 9, xe + 9, ye + 9], fill=cor)
    dr.text((gx1 + 14, ye - 32), fmtv(pts[-1][1]), font=fonte('JetBrainsMono-Bold.ttf', 30 if k == 'dolar' else 26), fill=WHITE)
    dr.text((gx1 + 14, ye + 4), pct(vdia), font=fonte('JetBrainsMono-Bold.ttf', 26), fill=cor)
    top = max(mks, key=lambda x: abs(x[campo])) if mks else None
    if top:   # um destaque só: a manchete com a maior reação em 30 min
        t0 = minutos(top['hora'])
        antes = [v for t, v in pts if t <= t0] or [pts[0][1]]
        x, yy = X(t0), Y(antes[-1])
        dr.ellipse([x - 8, yy - 8, x + 8, yy + 8], fill=ORANGE)
        ly = gy0 + 10 if yy > (gy0 + gy1) / 2 else gy1 - 150
        dr.line([(x, yy), (x, ly + (100 if ly < yy else 0))], fill=ORANGE, width=2)
        tx = max(gx0, min(x - 10, gx1 - 440))
        dr.text((tx, ly), f'{top["hora"]} · {pct(top[campo])} em 30 min', font=fm, fill=ORANGE)
        for i2, l in enumerate(quebrar(dr, top['titulo'], fonte('Inter-Medium.otf', 26), 440, 2)):
            dr.text((tx, ly + 30 + i2 * 32), l, font=fonte('Inter-Medium.otf', 26), fill=WHITE)
    for h in range(10, 19, 2):
        if pts[0][0] <= h * 60 <= pts[-1][0]:
            dr.text((X(h * 60) - 18, gy1 + 12), f'{h}h', font=fm, fill=MUTED)
    dr.line([(M, H - 120), (W - M, H - 120)], fill=LINE, width=2)
    dr.text((M, H - 95), 'Fonte: Yahoo Finance (cotações de 5 min) · reação em 30 min não prova causa', font=fonte('JetBrainsMono-Bold.ttf', 20), fill=MUTED)
    dr.text((M, H - 60), 'lectnex.com.br · conteúdo educacional, não é recomendação', font=fonte('JetBrainsMono-Bold.ttf', 22), fill=MUTED)
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
    tit = titulo_conclusao(m, k, vdia)
    legenda = (f'🗞️ <b>Post do dia: notícia × preço</b> · {DIAS[d.weekday()].lower()} {d:%d/%m}\n\n'
               '<b>Sugestão de legenda:</b>\n'
               f'{tit}. As manchetes seguidas dos maiores movimentos em 30 minutos:\n'
               f'{lst}\n'
               'O movimento seguinte não prova causa, mas mostra como o mercado reage à notícia. Veja o dia completo em lectnex.com.br. '
               'Conteúdo educacional. #ibovespa #dolar #daytrade #miniindice #minidolar #b3')
    if os.environ.get('IG_LEGENDA'):  # legenda limpa para o post no Instagram (coletor/instagram.py)
        open(os.environ['IG_LEGENDA'], 'w', encoding='utf-8').write(
            f'{tit} 📊\n\nAs manchetes seguidas dos maiores movimentos em 30 minutos:\n'
            f'{lst}\n\nO movimento seguinte não prova causa, mas mostra como o mercado reage à notícia. Veja o dia completo em lectnex.com.br.\n\n'
            'Conteúdo educacional, não é recomendação.\n#ibovespa #dolar #daytrade #miniindice #minidolar #b3')
    enviar(saida, legenda)


if __name__ == '__main__':
    main()
