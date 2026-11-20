"""Carrosséis da semana no padrão "um gráfico, uma conclusão" (aprovado em 19/11/2026), 1080×1350:
ranking  → (sexta à noite) capa + as 5 manchetes que mais mexeram na semana (reação em 30 min) + chamada para salvar.
agenda   → (segunda cedo) os 5 eventos mais importantes da semana (calendario.json) que podem mexer no WIN e no WDO.
Uso: python3 scripts/carrossel_semana.py ranking|agenda pasta_saida [AAAA-MM-DD]   → imagens + legenda.txt + x.txt
"""
import datetime as dt
import json
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from og_leitura import BG, CARD, LINE, MUTED, ORANGE, TEAL_L, VERDE, VERMELHO, WHITE, fonte, quebrar  # noqa: E402

RAIZ = os.path.join(os.path.dirname(__file__), '..')
W, H, M = 1080, 1350, 80
F = lambda n, t: fonte(n, t)
B, R, MO = 'InterDisplay-Bold.otf', 'Inter-Medium.otf', 'JetBrainsMono-Bold.ttf'
DIAS = ['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom']
pct = lambda v: ('+' if v > 0 else '−') + f'{abs(v):.2f}%'.replace('.', ',')
mn = lambda hm: int(hm[:2]) * 60 + int(hm[3:5])


def base(tag):
    im = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 10], fill=TEAL_L)
    d.text((M, 60), 'Lect', font=F(B, 40), fill=WHITE); d.text((M + d.textlength('Lect', font=F(B, 40)), 60), 'nex', font=F(B, 40), fill=TEAL_L)
    d.text((W - M - d.textlength(tag, font=F(MO, 24)), 72), tag, font=F(MO, 24), fill=MUTED)
    return im, d
def rodape(d, fonte_txt, pagina=None):
    d.line([(M, H - 120), (W - M, H - 120)], fill=LINE, width=2)
    d.text((M, H - 95), fonte_txt, font=F(MO, 22), fill=MUTED)
    d.text((M, H - 60), 'lectnex.com.br · conteúdo educacional, não é recomendação', font=F(MO, 22), fill=MUTED)
    if pagina: d.text((W - M - d.textlength(pagina, font=F(MO, 24)), H - 95), pagina, font=F(MO, 24), fill=TEAL_L)
def titulo(d, txt, y, tam=74, cor=WHITE):
    f = F(B, tam)
    for l in quebrar(d, txt, f, W - 2 * M, 4): d.text((M, y), l, font=f, fill=cor); y += int(tam * 1.12)
    return y
pct = lambda v: ('+' if v > 0 else '−') + f'{abs(v):.2f}%'.replace('.', ',')
mn = lambda hm: int(hm[:2]) * 60 + int(hm[3:5])



def ranking(OUT, data):
    dias = [x for x in json.load(open(os.path.join(RAIZ, 'data', 'dias', 'indice.json'), encoding='utf-8'))['dias'] if x <= data.isoformat()]
    # B) ranking da semana (carrossel: capa, lista, chamada)
    seg = data - dt.timedelta(days=data.weekday()); itens = []
    for dd in dias:
        if dd < seg.isoformat(): continue
        for m in json.load(open(os.path.join(RAIZ, 'data', 'dias', f'{dd}.json'), encoding='utf-8')).get('marcadores', []):
            for campo, nome in (('ibov30', 'Ibovespa'), ('dolar30', 'Dólar')):
                if m.get(campo) is not None: itens.append((abs(m[campo]), dd, m, nome, m[campo]))
    itens.sort(key=lambda x: -x[0]); top, vis = [], set()
    for _, dd, m, nome, v in itens:
        if m['titulo'][:40] in vis or any(dd == a and abs(mn(m['hora']) - mn(b['hora'])) < 30 for a, b, _, _ in top): continue
        vis.add(m['titulo'][:40]); top.append((dd, m, nome, v))
        if len(top) == 5: break
    im, d = base('RANKING DA SEMANA')
    d.text((M, 300), f'{seg:%d/%m} A {data:%d/%m}', font=F(MO, 34), fill=TEAL_L)
    y = titulo(d, 'As 5 notícias que mais mexeram no mercado esta semana', 360, 96)
    d.text((M, y + 30), 'E quanto o preço andou nos 30 minutos seguintes.', font=F(R, 38), fill=MUTED)
    d.text((M, H - 260), 'Arraste para o lado →', font=F(B, 44), fill=ORANGE)
    rodape(d, 'Fonte: manchetes e cotações de 5 min gravadas pela Lectnex', '1/3'); im.save(os.path.join(OUT, 'B1-ranking-capa.jpg'), quality=92)
    im, d = base('RANKING DA SEMANA'); y = 160
    for i, (dd, m, nome, v) in enumerate(top, 1):
        dd_ = dt.date.fromisoformat(dd)
        d.rectangle([M, y, W - M, y + 182], fill=CARD, outline=LINE, width=2)
        d.text((M + 24, y + 24), f'{i}', font=F(B, 80), fill=ORANGE)
        d.text((M + 110, y + 22), f'{DIAS[dd_.weekday()]} {dd_:%d/%m} · {m["hora"]}', font=F(MO, 22), fill=MUTED)
        for k, l in enumerate(quebrar(d, m['titulo'], F(B, 30), W - 2 * M - 360, 3)): d.text((M + 110, y + 56 + k * 36), l, font=F(B, 30), fill=WHITE)
        cor = VERDE if v > 0 else VERMELHO; tv = pct(v); d.text((W - M - 24 - d.textlength(tv, font=F(MO, 40)), y + 50), tv, font=F(MO, 40), fill=cor)
        d.text((W - M - 24 - d.textlength(nome + ' 30 min', font=F(MO, 20)), y + 104), nome + ' 30 min', font=F(MO, 20), fill=MUTED)
        y += 200
    rodape(d, 'Reação em 30 min: não prova que a notícia foi a causa', '2/3'); im.save(os.path.join(OUT, 'B2-ranking-lista.jpg'), quality=92)
    im, d = base('RANKING DA SEMANA')
    y = titulo(d, 'Salve para rever antes do próximo pregão', 360, 96)
    d.text((M, y + 40), 'Cada dia tem o gráfico completo, com todas as manchetes no horário em que saíram.', font=F(R, 38), fill=MUTED)
    d.rectangle([M, 900, W - M, 1020], fill=TEAL_L); tx = 'lectnex.com.br/hoje'; d.text(((W - d.textlength(tx, font=F(B, 54))) / 2, 928), tx, font=F(B, 54), fill=BG)
    rodape(d, 'Siga a @lectnex.oficial: gráfico do mercado todo dia', '3/3'); im.save(os.path.join(OUT, 'B3-ranking-chamada.jpg'), quality=92)

    return [os.path.join(OUT, f'{k}.jpg') for k in ('B1-ranking-capa', 'B2-ranking-lista', 'B3-ranking-chamada')], top, seg


def agenda(OUT, data):
    ini = data + dt.timedelta(days=(7 - data.weekday()) % 7)  # segunda desta semana (se hoje é segunda) ou a próxima
    fim = ini + dt.timedelta(days=4)
    # C) agenda da semana que vem
    ev = [e for e in json.load(open(os.path.join(RAIZ, 'data', 'calendario.json'), encoding='utf-8'))['eventos'] if ini.isoformat() <= e['data'] <= fim.isoformat()]
    ev.sort(key=lambda e: (-e['importancia'], e['data'])); top5 = sorted(ev[:5], key=lambda e: (e['data'], e.get('hora') or '99'))
    im, d = base('AGENDA DA SEMANA')
    d.text((M, 150), f'{ini:%d} A {fim:%d/%m}', font=F(MO, 34), fill=TEAL_L)
    y = titulo(d, '5 eventos que podem mexer no WIN e no WDO', 200, 64) + 24
    band = {'BR': '🇧🇷', 'US': 'EUA', 'EU': 'Europa'}
    for e in top5:
        dd_ = dt.date.fromisoformat(e['data'])
        d.rectangle([M, y, W - M, y + 140], fill=CARD, outline=LINE, width=2)
        d.rectangle([M, y, M + 10, y + 140], fill=ORANGE if e['importancia'] >= 2 else TEAL_L)
        d.text((M + 34, y + 22), DIAS[dd_.weekday()].upper(), font=F(MO, 30), fill=ORANGE); d.text((M + 34, y + 62), f'{dd_:%d/%m}', font=F(MO, 26), fill=MUTED)
        d.text((M + 34, y + 94), (e.get('hora') or 'dia todo').replace('h', 'h'), font=F(MO, 24), fill=MUTED)
        nome = f"{'EUA' if e['pais']=='US' else 'Brasil' if e['pais']=='BR' else 'Europa'} · {e['evento']}"
        for k, l in enumerate(quebrar(d, nome, F(B, 34), W - 2 * M - 230, 2)): d.text((M + 200, y + 22 + k * 40), l, font=F(B, 34), fill=WHITE)
        chips = ' '.join(k.upper() for k in (e.get('impacto') or {}))
        d.text((M + 200, y + 100), 'mexe com ' + chips, font=F(MO, 22), fill=TEAL_L)
        y += 152
    rodape(d, 'Fonte: calendário da Lectnex (B3, BCB, IBGE e órgãos dos EUA)')
    im.save(os.path.join(OUT, 'agenda-semana.jpg'), quality=92)
    return [os.path.join(OUT, 'agenda-semana.jpg')], top5, ini


def textos(tipo, itens, ini):
    if tipo == 'ranking':
        n1 = itens[0] if itens else None
        leg = ['🏆 As 5 notícias que mais mexeram no mercado esta semana', '']
        leg += [f'{i}. {m["titulo"]} ({nome} {pct(v)} em 30 min)' for i, (dd, m, nome, v) in enumerate(itens, 1)]
        leg += ['', 'Qual delas você operou? Conta aqui 👇', '💾 Salve para rever antes do próximo pregão.',
                '💬 Discord: discord.gg/kM6YcQA82P', 'Reação em 30 min não prova causa. Conteúdo educacional, não é recomendação.',
                '#ibovespa #dolar #daytrade #miniindice #minidolar #b3 #mercadofinanceiro']
        x = '🏆 A notícia que mais mexeu no mercado esta semana:\n\n' + (f'"{n1[1]["titulo"][:150]}"\n{n1[2]} {pct(n1[3])} em 30 min.' if n1 else '') + \
            '\n\nO ranking completo e o gráfico de cada dia: https://lectnex.com.br/hoje.html'
    else:
        leg = [f'📅 Agenda da semana ({ini:%d/%m}): 5 eventos que podem mexer no WIN e no WDO', '']
        leg += [f'• {DIAS[dt.date.fromisoformat(e["data"]).weekday()]} {e.get("hora") or ""} · {e["evento"]}'.replace('  ', ' ') for e in itens]
        leg += ['', 'Qual você vai acompanhar? 👇', '💾 Salve para não ser pego de surpresa.', '📩 Leitura do Dia grátis às 7h40: lectnex.com.br',
                'Conteúdo educacional, não é recomendação.', '#daytrade #miniindice #minidolar #b3 #agendaeconomica #mercadofinanceiro']
        x = f'📅 Agenda da semana ({ini:%d/%m}) para quem opera WIN e WDO:\n\n' + '\n'.join(
            f'{DIAS[dt.date.fromisoformat(e["data"]).weekday()]} {e.get("hora") or ""} · {e["evento"]}' for e in itens[:5]) + '\n\nCalendário completo: https://lectnex.com.br'
    return '\n'.join(leg), x


if __name__ == '__main__':
    tipo, pasta = sys.argv[1], sys.argv[2]
    data = dt.date.fromisoformat(sys.argv[3]) if len(sys.argv) > 3 else dt.date.today()
    os.makedirs(pasta, exist_ok=True)
    imgs, itens, ini = (ranking if tipo == 'ranking' else agenda)(pasta, data)
    leg, x = textos(tipo, itens, ini)
    open(os.path.join(pasta, 'legenda.txt'), 'w', encoding='utf-8').write(leg)
    open(os.path.join(pasta, 'x.txt'), 'w', encoding='utf-8').write(x)
    print('\n'.join(imgs))
