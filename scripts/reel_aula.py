"""Reels educativo diário "Dicionário do trader #N" (1080×1920, ~25-30 s): um termo do mercado explicado sem enrolação.
Gancho ("Você sabe o que é X?") → o que é (texto entrando palavra a palavra) → na prática (exemplo com números) → chamada para
seguir, salvar e entrar no Discord. Mesmo termo do Termo do dia (ligado à agenda; sem evento, rodízio do glossário).
A duração de cada parte acompanha o tamanho do texto (dá tempo de ler).

Uso: python3 scripts/reel_aula.py saida.mp4 [--data AAAA-MM-DD] [--termo "Nome"] [--capa c.png] [--legenda l.txt] [--x x.txt] [--quadros 1,5]
"""
import datetime as dt
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from og_leitura import CARD, LINE, MUTED, ORANGE, TEAL_L, WHITE, BG, fonte, quebrar  # noqa: E402
from reel_dia import FPS, H, M, W, ease, eback, mix  # noqa: E402
from termo_dia import BRT, escolher  # noqa: E402

DISCORD = 'discord.gg/kM6YcQA82P'
INICIO = dt.date(2026, 11, 17)  # dicionário #1
GANCHO, FIM = 2.4, 3.6
CAT = {'futuros': 'FUTUROS', 'juros': 'MACRO & JUROS', 'acoes': 'AÇÕES', 'risco': 'GESTÃO DE RISCO', 'opcoes': 'OPÇÕES', 'impostos': 'IMPOSTOS'}


def numero(dia):
    return max(1, sum(1 for i in range((dia - INICIO).days + 1) if (INICIO + dt.timedelta(days=i)).weekday() < 5))


class Aula:
    def __init__(self, t, dia):
        self.t, self.dia, self.n = t, dia, numero(dia)
        self.d, self.x = t['d'].strip(), (t.get('x') or '').strip()
        self.td = max(5.0, min(10.0, len(self.d) / 16))
        self.tx = max(7.0, min(17.0, len(self.x) / 17)) if self.x else 0
        self.total = GANCHO + self.td + self.tx + FIM
        self.base = Image.new('RGB', (W, H), BG)
        dr = ImageDraw.Draw(self.base)
        for x in range(0, W, 60):
            dr.line([(x, 0), (x, H)], fill=mix('#0A1422', 1))
        for y in range(0, H, 60):
            dr.line([(0, y), (W, y)], fill=mix('#0A1422', 1))
        try:
            logo = Image.open(os.path.join(os.path.dirname(__file__), '..', 'assets', 'brand', 'icon-192.png')).convert('RGBA').resize((60, 60))
            self.base.paste(logo, (M, 200), logo)
        except Exception:
            pass
        fb = fonte('InterDisplay-Bold.otf', 40)
        dr.text((M + 76, 208), 'Lect', font=fb, fill=WHITE)
        dr.text((M + 76 + dr.textlength('Lect', font=fb), 208), 'nex', font=fb, fill=TEAL_L)
        serie = f'DICIONÁRIO DO TRADER #{self.n}'
        fm = fonte('JetBrainsMono-Bold.ttf', 28)
        dr.text((W - M - dr.textlength(serie, font=fm), 220), serie, font=fm, fill=MUTED)

    def centro(self, d, y, txt, f, cor):
        d.text(((W - d.textlength(txt, font=f)) / 2, y), txt, font=f, fill=cor)

    def caber(self, d, txt, nome, tam, larg, alt, minimo=34):
        while tam > minimo:
            f = fonte(nome, tam)
            ls = quebrar(d, txt, f, larg, 30)
            if len(ls) * tam * 1.32 <= alt:
                return f, ls, int(tam * 1.32)
            tam -= 2
        f = fonte(nome, minimo)
        return f, quebrar(d, txt, f, larg, int(alt / (minimo * 1.32))), int(minimo * 1.32)

    def palavras(self, d, ls, f, lh, x0, y0, prog, cor):
        """Texto entrando palavra a palavra até 'prog' (0-1)."""
        tot = sum(len(l.split()) for l in ls)
        mostrar = prog * tot
        k = 0
        for i, l in enumerate(ls):
            x = x0
            for w in l.split():
                a = max(0.0, min(1.0, mostrar - k))
                if a > 0:
                    d.text((x, y0 + i * lh + (1 - a) * 10), w, font=f, fill=mix(cor, a))
                x += d.textlength(w + ' ', font=f)
                k += 1

    def barra(self, d, t):
        d.rectangle([0, 0, W, 12], fill=mix(LINE, 1))
        d.rectangle([0, 0, W * min(1, t / self.total), 12], fill=TEAL_L)

    def quadro(self, t):
        im = self.base.copy()
        d = ImageDraw.Draw(im)
        self.barra(d, t)
        nome = self.t['t']
        if t < GANCHO:
            s = eback(t / 0.45)
            self.centro(d, 560, 'Você sabe o que é', fonte('InterDisplay-Bold.otf', 78), mix(WHITE, ease(t / 0.3)))
            f, ls, lh = self.caber(d, nome + '?', 'InterDisplay-Bold.otf', int(150 * (0.85 + 0.15 * s)), W - 2 * M, 420, 70)
            for i, l in enumerate(ls):
                self.centro(d, 680 + i * lh, l, f, mix(ORANGE, ease((t - 0.2) / 0.3)))
            if t > 1.0:
                self.centro(d, 1240, 'Explico em 30 segundos', fonte('Inter-Medium.otf', 44), mix(MUTED, ease((t - 1.0) / 0.3)))
            return im
        t -= GANCHO
        fn = fonte('InterDisplay-Bold.otf', 64)
        if t < self.td:
            d.text((M, 330), CAT.get(self.t.get('c'), 'MERCADO') + ' · O QUE É', font=fonte('JetBrainsMono-Bold.ttf', 32), fill=TEAL_L)
            f2, l2, h2 = self.caber(d, nome, 'InterDisplay-Bold.otf', 88, W - 2 * M, 220, 56)
            for i, l in enumerate(l2):
                d.text((M, 390 + i * h2), l, font=f2, fill=ORANGE)
            y0 = 400 + len(l2) * h2 + 40
            f, ls, lh = self.caber(d, self.d, 'InterDisplay-Bold.otf', 66, W - 2 * M, 1500 - y0, 40)
            self.palavras(d, ls, f, lh, M, y0, min(1.0, t / (self.td * 0.55)), WHITE)
            return im
        t -= self.td
        if t < self.tx:
            d.text((M, 330), f'NA PRÁTICA · {nome.upper()}'[:46], font=fonte('JetBrainsMono-Bold.ttf', 32), fill=ORANGE)
            a = ease(t / 0.4)
            y0 = 400 + (1 - eback(t / 0.4)) * 40
            f, ls, lh = self.caber(d, self.x, 'Inter-Medium.otf', 60, W - 2 * M - 60, 1110, 34)
            alt = len(ls) * lh + 80
            d.rectangle([M - 16, y0, W - M + 16, y0 + alt], fill=mix(CARD, a), outline=mix(ORANGE, a), width=3)
            d.rectangle([M - 16, y0, M - 6, y0 + alt], fill=mix(ORANGE, a))
            self.palavras(d, ls, f, lh, M + 30, y0 + 40, min(1.0, t / (self.tx * 0.6)), WHITE)
            return im
        t -= self.tx
        a = ease(t / 0.35)
        self.centro(d, 470, 'Salve para revisar', fn, mix(WHITE, a))
        self.centro(d, 560, 'e mande para quem está começando', fonte('Inter-Medium.otf', 44), mix(MUTED, a))
        e = eback((t - 0.3) / 0.45)
        self.centro(d, 720, f'Amanhã: dicionário #{self.n + 1}', fonte('InterDisplay-Bold.otf', int(66 * (0.85 + 0.15 * e))), mix(ORANGE, ease((t - 0.3) / 0.3)))
        self.centro(d, 810, 'Siga para não perder', fonte('Inter-Medium.otf', 44), mix(WHITE, ease((t - 0.4) / 0.3)))
        if t > 0.8:
            c = ease((t - 0.8) / 0.35)
            d.rectangle([M + 40, 1000, W - M - 40, 1130], fill=mix(TEAL_L, c))
            self.centro(d, 1032, 'Glossário grátis: lectnex.com.br', fonte('InterDisplay-Bold.otf', 48), mix(BG, c, TEAL_L) if c else BG)
            dc = (88, 101, 242)
            d.rectangle([M + 40, 1160, W - M - 40, 1290], fill=mix(dc, c))
            self.centro(d, 1176, 'Tire dúvidas no Discord', fonte('InterDisplay-Bold.otf', 44), mix(WHITE, c, dc))
            self.centro(d, 1232, DISCORD, fonte('JetBrainsMono-Bold.ttf', 26), mix(WHITE, c, dc))
            self.centro(d, 1340, 'Seja fundador da Lectnex Pro · lectnex.com.br/pro', fonte('JetBrainsMono-Bold.ttf', 28), mix(ORANGE, c))
            self.centro(d, 1560, 'conteúdo educacional · não é recomendação', fonte('JetBrainsMono-Bold.ttf', 26), mix(MUTED, c))
        return im


def textos(a):
    t = a.t
    leg = '\n'.join([f'📚 Dicionário do trader #{a.n}: {t["t"]}', '', a.d, ''] + ([f'Na prática: {a.x}', ''] if a.x else []) +
                    ['💾 Salve para revisar e mande para quem está começando.', 'Todo dia útil um termo novo: siga para não perder.', '',
                     f'💬 Dúvidas? Comunidade no Discord: {DISCORD}', '👑 Seja fundador da Lectnex Pro (lista de espera): lectnex.com.br/pro', 'Glossário completo e grátis: lectnex.com.br/glossario', '',
                     'Conteúdo educacional, não é recomendação.',
                     '#educacaofinanceira #mercadofinanceiro #daytrade #bolsadevalores #investimentos #trader'])
    corpo = a.d if len(a.d) <= 170 else a.d[:167].rsplit(' ', 1)[0] + '…'
    x = f'📚 {t["t"]}, explicado em 1 frase:\n\n{corpo}\n\nExemplo com números 👇\nhttps://lectnex.com.br/glossario'
    return leg, x


def capa(a, saida):
    im = a.base.copy()
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 12], fill=ORANGE)
    a.centro(d, 520, f'DICIONÁRIO DO TRADER #{a.n}', fonte('JetBrainsMono-Bold.ttf', 34), TEAL_L)
    a.centro(d, 600, 'O que é', fonte('InterDisplay-Bold.otf', 84), WHITE)
    f, ls, lh = a.caber(d, a.t['t'] + '?', 'InterDisplay-Bold.otf', 150, W - 2 * M, 460, 70)
    for i, l in enumerate(ls):
        a.centro(d, 720 + i * lh, l, f, ORANGE)
    im.save(saida, 'PNG', optimize=True)


def main():
    opc = {sys.argv[i + 1] for i, x in enumerate(sys.argv[:-1]) if x in ('--data', '--termo', '--capa', '--legenda', '--x', '--quadros')}
    args = [x for x in sys.argv[1:] if not x.startswith('--') and x not in opc]
    val = lambda k: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else None
    raiz = os.path.join(os.path.dirname(__file__), '..')
    dia = dt.date.fromisoformat(val('--data')) if val('--data') else dt.datetime.now(BRT).date()
    termos = json.load(open(os.path.join(raiz, 'data', 'glossario.json'), encoding='utf-8'))['termos']
    if val('--termo'):
        t = next(x for x in termos if x['t'] == val('--termo'))
    else:
        eventos = json.load(open(os.path.join(raiz, 'data', 'calendario.json'), encoding='utf-8')).get('eventos', [])
        t, _ = escolher(dia, termos, eventos)
    a = Aula(t, dia)
    if val('--quadros'):
        pasta = args[0] if args else '.'
        for q in map(float, val('--quadros').split(',')):
            a.quadro(q).save(os.path.join(pasta, f'aula_{q:05.2f}.png'))
        return
    saida = args[0] if args else 'reel-aula.mp4'
    leg, x = textos(a)
    for k, v in (('--legenda', leg), ('--x', x)):
        if val(k):
            open(val(k), 'w', encoding='utf-8').write(v)
    if val('--capa'):
        capa(a, val('--capa'))
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-crf', '21', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', saida],
                         stdin=subprocess.PIPE)
    for i in range(int(a.total * FPS)):
        p.stdin.write(a.quadro(i / FPS).tobytes())
    p.stdin.close()
    p.wait()
    try:
        from trilha import juntar, trilha
        juntar(saida, trilha(a.total, pops=[GANCHO, GANCHO + a.td], sinal=None, final=a.total - FIM, saida=saida + '.wav', bpm=92))
        os.remove(saida + '.wav')
    except Exception as e:
        print(f'::warning::Aula sem áudio ({e})')
    print(f'Dicionário do trader #{a.n}: {t["t"]} → {saida} ({os.path.getsize(saida) // 1024} KB, {a.total:.1f} s)')


if __name__ == '__main__':
    main()
