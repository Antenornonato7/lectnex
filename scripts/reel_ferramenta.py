"""Reels de ferramenta (1080×1920, 15 s): mostra uma ferramenta GRÁTIS do site, com a tela real do celular rolando, para trazer
gente ao lectnex.com.br e à comunidade do Discord. Roda em rodízio (terça e quinta), uma ferramenta por vez.

Uso: python3 scripts/reel_ferramenta.py [chave|auto] --base https://lectnex.com.br --saida pasta [--quadros 1,5,13]
Gera na pasta: tela.png (print do site), reel.mp4, capa.png, legenda.txt (Instagram/Facebook), x.txt (texto do X) e meta.json.
"""
import datetime as dt
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from og_leitura import BG, CARD, LINE, MUTED, ORANGE, TEAL_L, WHITE, fonte, quebrar  # noqa: E402
from reel_dia import ease, eback, mix  # noqa: E402

W, H, FPS = 1080, 1920, 30
A, B, TOTAL = 2.4, 11.6, 15.0  # gancho | tela rolando | chamada
DISCORD = 'discord.gg/kM6YcQA82P'
CX, CY, CW, CH = 90, 470, 900, 1080  # janela do "celular"

# chave, página, seletor do print, gancho (pergunta que a pessoa já se faz), promessa curta, hashtags extras
FERRAMENTAS = [
    ('risco', 'futuros.html#risco', '#risco', 'Quantos contratos de mini índice cabem na sua conta?',
     'A calculadora de risco responde em segundos: contratos, stop em reais e quanto da conta você arrisca.', '#gestaoderisco'),
    ('ir', 'calculadora-ir-day-trade.html', 'main', 'Quanto de imposto você paga no day trade?',
     'Coloque o resultado do mês e veja o IR, o DARF e o prejuízo para compensar.', '#impostoderenda'),
    ('ponto', 'valor-do-ponto-mini-indice-mini-dolar.html', 'main', 'Quanto vale 1 ponto do WIN e do WDO em reais?',
     'Digite os pontos e veja na hora quanto ganha ou perde por contrato.', '#minidolar'),
    ('plano', 'futuros.html#plano', '#plano', 'Você entra no pregão com um plano ou no improviso?',
     'O Plano do Dia junta eventos, contrato vigente e seu limite de perda numa tela só.', '#disciplina'),
    ('hoje', 'hoje.html', 'main', 'O que mexeu no mercado hoje, minuto a minuto?',
     'O gráfico do Ibovespa e do dólar com as manchetes marcadas na hora em que saíram.', '#noticias'),
    ('vencimento', 'vencimento-mini-indice-mini-dolar.html', 'main', 'Quando vence o mini índice e o mini dólar?',
     'As próximas datas, o último pregão e a contagem regressiva para virar de contrato.', '#minidolar'),
    ('agenda', 'index.html#agenda', '#agenda', 'Qual notícia pode mexer no mercado hoje?',
     'A agenda do dia com o horário de cada dado e o que costuma acontecer com WIN e WDO.', '#agendaeconomica'),
    ('diario', 'futuros.html#diario', '#diario', 'Você anota seus trades? Quem anota erra menos.',
     'Um diário de trades grátis no navegador, ligado à calculadora de IR.', '#diariodetrade'),
]


def escolher(chave='auto', hoje=None):
    if chave and chave != 'auto':
        return next(f for f in FERRAMENTAS if f[0] == chave)
    hoje = hoje or dt.date.today()
    n = hoje.isocalendar()[1] * 2 + (1 if hoje.weekday() >= 3 else 0)
    return FERRAMENTAS[n % len(FERRAMENTAS)]


def printar(base, pagina, seletor, saida):
    """Print do site no celular (390 px, tela 3x, tema escuro), só da ferramenta, sem o cabeçalho fixo."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=3, color_scheme='dark', locale='pt-BR')
        pg.goto(base.rstrip('/') + '/' + pagina, wait_until='domcontentloaded', timeout=60000)
        pg.wait_for_timeout(4500)
        pg.add_style_tag(content='#lx-topbar,#lx-header,header,#lx-cookies,[data-lx-toast]{display:none!important}')
        el = pg.locator(seletor).first
        el.scroll_into_view_if_needed()
        pg.wait_for_timeout(1200)
        caixa = el.bounding_box()
        alt = min(caixa['height'], 1150)
        pg.screenshot(path=saida, full_page=True, clip={'x': 0, 'y': caixa['y'] + pg.evaluate('scrollY'), 'width': 390, 'height': alt})
        b.close()


class Reel:
    def __init__(self, f, tela):
        self.chave, self.pagina, _, self.gancho, self.promessa, _ = f
        im = Image.open(tela).convert('RGB')
        self.tela = im.resize((CW, round(im.height * CW / im.width)), Image.LANCZOS)
        self.url = 'lectnex.com.br/' + self.pagina.split('#')[0].replace('index.html', '')
        if len(self.url) > 34:
            self.url = 'lectnex.com.br'
        self.F = {'g': fonte('InterDisplay-Bold.otf', 92), 'm': fonte('InterDisplay-Bold.otf', 50), 't': fonte('InterDisplay-Bold.otf', 46),
                  'mono': fonte('JetBrainsMono-Bold.ttf', 30), 'monog': fonte('JetBrainsMono-Bold.ttf', 44), 'p': fonte('InterDisplay-Bold.otf', 38)}
        self.base = Image.new('RGB', (W, H), BG)
        d = ImageDraw.Draw(self.base)
        for x in range(0, W, 60):
            d.line([(x, 0), (x, H)], fill=mix('#0A1422', 1))
        for y in range(0, H, 60):
            d.line([(0, y), (W, y)], fill=mix('#0A1422', 1))

    def centro(self, d, y, txt, f, cor):
        d.text(((W - d.textlength(txt, font=f)) / 2, y), txt, font=f, fill=cor)

    def quadro(self, t):
        im = self.base.copy()
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, W, 10], fill=TEAL_L)
        if t < A:  # gancho: pergunta grande
            e = eback(t / 0.5)
            self.centro(d, 520, 'FERRAMENTA GRÁTIS · LECTNEX', self.F['mono'], mix(TEAL_L, ease(t / 0.4)))
            linhas = quebrar(d, self.gancho, self.F['g'], W - 140, 5)
            y0 = 640 + (1 - e) * 60
            for i, l in enumerate(linhas):
                self.centro(d, y0 + i * 112, l, self.F['g'], mix(WHITE, ease((t - 0.1 * i) / 0.35)))
            return im
        if t < B:  # a tela real rolando
            k = (t - A) / (B - A)
            for i, l in enumerate(quebrar(d, self.gancho, self.F['t'], W - 160, 2)):
                self.centro(d, 150 + i * 60, l, self.F['t'], WHITE)
            self.centro(d, 320, self.promessa_curta(), self.F['mono'], TEAL_L)
            sobra = max(0, self.tela.height - CH)
            y = int(sobra * ease(max(0, (k - 0.12) / 0.8)) if k < 0.92 else sobra)
            janela = self.tela.crop((0, y, CW, y + min(CH, self.tela.height)))
            ent = ease((t - A) / 0.45)
            yy = CY + int((1 - ent) * 120)
            d.rectangle([CX - 14, yy - 14, CX + CW + 14, yy + min(CH, self.tela.height) + 14], fill=CARD, outline=LINE, width=3)
            im.paste(janela, (CX, yy))
            d = ImageDraw.Draw(im)
            self.centro(d, CY + CH + 70, self.url, self.F['monog'], ORANGE)
            return im
        # chamada final
        e = eback((t - B) / 0.5)
        self.centro(d, 560, 'Grátis. Sem cadastro.', self.F['g'], WHITE)
        self.centro(d, 690, 'Funciona no celular.', self.F['m'], MUTED)
        bw, bh, by = 880, 150, 860 + (1 - e) * 40
        d.rectangle([(W - bw) / 2, by, (W + bw) / 2, by + bh], fill=TEAL_L)
        f = self.F['monog']
        self.centro(d, by + (bh - 52) / 2, self.url, f, BG)
        a = ease((t - B - 0.7) / 0.5)
        dc = (88, 101, 242)
        d.rectangle([(W - bw) / 2, 1080, (W + bw) / 2, 1230], fill=mix(dc, a), outline=None)
        self.centro(d, 1104, 'Comunidade de traders no Discord', self.F['p'], mix(WHITE, a, dc if a else BG))
        self.centro(d, 1160, DISCORD, self.F['mono'], mix(WHITE, a, dc if a else BG))
        self.centro(d, 1300, 'Seja fundador da Lectnex Pro · lectnex.com.br/pro', self.F['mono'], mix(ORANGE, a))
        self.centro(d, 1420, 'conteúdo educacional · não é recomendação', self.F['mono'], MUTED)
        return im

    def promessa_curta(self):
        return {'risco': 'contratos · stop em R$ · % da conta', 'ir': 'IR do mês · DARF · prejuízo', 'ponto': 'pontos → reais, na hora',
                'plano': 'eventos · contrato · limite de perda', 'hoje': 'gráfico + manchetes no horário',
                'vencimento': 'datas · último pregão · rolagem', 'agenda': 'horário de cada dado do dia',
                'diario': 'anote · revise · melhore'}.get(self.chave, 'grátis no lectnex.com.br')


def textos(f):
    chave, pagina, _, gancho, promessa, tag = f
    url = 'lectnex.com.br/' + pagina.split('#')[0].replace('index.html', '')
    legenda = '\n'.join([gancho, '', promessa, '', f'👉 Grátis e sem cadastro: {url}',
                         f'💬 Comunidade de traders no Discord: {DISCORD}', '👑 Lista de fundadores da Lectnex Pro (grátis): lectnex.com.br/pro', '',
                         'Salve para usar no próximo pregão. Conteúdo educacional, não é recomendação.',
                         f'#daytrade #miniindice #b3 #trader {tag}'])
    x = '\n\n'.join([gancho, promessa, f'Grátis, sem cadastro 👇\nhttps://{url}',
                     f'Comunidade no Discord: https://{DISCORD}'])
    return legenda, x


def capa(r, saida):
    im = r.base.copy()
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 10], fill=ORANGE)
    r.centro(d, 560, 'FERRAMENTA GRÁTIS', r.F['mono'], TEAL_L)
    for i, l in enumerate(quebrar(d, r.gancho, r.F['g'], W - 140, 5)):
        r.centro(d, 650 + i * 112, l, r.F['g'], WHITE)
    r.centro(d, 1300, r.url if len(r.url) <= 34 else 'lectnex.com.br', r.F['mono'], ORANGE)
    im.save(saida, 'PNG', optimize=True)


def main():
    opc = {sys.argv[i + 1] for i, a in enumerate(sys.argv[:-1]) if a in ('--base', '--saida', '--quadros', '--tela')}
    args = [a for a in sys.argv[1:] if not a.startswith('--') and a not in opc]
    val = lambda k, p=None: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else p
    f = escolher(args[0] if args else 'auto')
    pasta = val('--saida', '.')
    os.makedirs(pasta, exist_ok=True)
    tela = val('--tela') or os.path.join(pasta, 'tela.png')
    if not val('--tela'):
        printar(val('--base', 'https://lectnex.com.br'), f[1], f[2], tela)
    r = Reel(f, tela)
    if '--quadros' in sys.argv:
        for t in map(float, val('--quadros').split(',')):
            r.quadro(t).save(os.path.join(pasta, f'q_{t:05.2f}.png'))
        return
    legenda, x = textos(f)
    open(os.path.join(pasta, 'legenda.txt'), 'w', encoding='utf-8').write(legenda)
    open(os.path.join(pasta, 'x.txt'), 'w', encoding='utf-8').write(x)
    json.dump({'chave': f[0], 'nome': f'Reels de ferramenta: {f[0]}'}, open(os.path.join(pasta, 'meta.json'), 'w'))
    capa(r, os.path.join(pasta, 'capa.png'))
    saida = os.path.join(pasta, 'reel.mp4')
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-crf', '21', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', saida],
                         stdin=subprocess.PIPE)
    for i in range(int(TOTAL * FPS)):
        p.stdin.write(r.quadro(i / FPS).tobytes())
    p.stdin.close()
    p.wait()
    try:
        from trilha import juntar, trilha
        juntar(saida, trilha(TOTAL, pops=[A], sinal=B, final=B, saida=saida + '.wav'))
        os.remove(saida + '.wav')
    except Exception as e:
        print(f'::warning::Reel sem áudio ({e})')
    print(f'Reels de ferramenta ({f[0]}): {saida} ({os.path.getsize(saida) // 1024} KB)')


if __name__ == '__main__':
    main()
