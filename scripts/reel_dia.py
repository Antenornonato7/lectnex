"""Reel do dia (1080×1920, 15 s, sem áudio): o gráfico do Ibovespa ou do dólar se desenhando ao longo do pregão, as 3 manchetes
que mais mexeram aparecendo no horário e o fechamento no fim. Mesmos dados do post do gráfico do dia (campo 'mercado' do ao-vivo).
Uso: python3 scripts/reel_dia.py mercado.json [saida.mp4] [--quadros t1,t2]   (--quadros salva PNGs para conferir)
"""
import datetime as dt
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from grafico_dia import escolher, minutos, pct  # noqa: E402
from og_leitura import BG, CARD, DIAS, LINE, MUTED, ORANGE, TEAL_L, VERDE, VERMELHO, WHITE, fonte, quebrar  # noqa: E402

W, H, FPS = 1080, 1920, 30
A, B, C, D, TOTAL = 1.6, 9.6, 12.4, 15.0, 15.0  # gancho | gráfico | resultado | chamada
M = 72
ease = lambda x: 1 - (1 - max(0.0, min(1.0, x))) ** 3
eback = lambda x: (lambda t: 1 + 2.2 * (t - 1) ** 3 + 1.2 * (t - 1) ** 2)(max(0.0, min(1.0, x)))


def hexrgb(c):
    c = c.lstrip('#')
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def mix(c, a, b=BG):
    c, b = (hexrgb(c) if isinstance(c, str) else c), (hexrgb(b) if isinstance(b, str) else b)
    a = max(0.0, min(1.0, a))
    return tuple(int(b[i] + (c[i] - b[i]) * a) for i in range(3))


class Reel:
    def __init__(self, m):
        self.k, self.campo, self.mks, self.vdia = escolher(m)
        s = m[self.k]
        self.pts, self.base = s['pontos'], s.get('anterior') or s['pontos'][0][1]
        self.xs = [minutos(p[0]) for p in self.pts]
        self.x0, self.x1 = min(600, self.xs[0]), max(1080, self.xs[-1])
        ys = [p[1] for p in self.pts] + [self.base]
        lo, hi = min(ys), max(ys)
        pad = (hi - lo) * 0.12 or self.base * 0.002
        self.lo, self.hi = lo - pad, hi + pad
        self.dia = dt.date.fromisoformat(m['data'])
        self.nome = 'Ibovespa' if self.k == 'ibov' else 'dólar'
        self.cor = VERDE if self.vdia >= 0 else VERMELHO
        self.gx0, self.gx1, self.gy0, self.gy1 = M + 10, W - M - 10, 560, 1130
        # roteiro do gráfico: desenha até cada manchete, pausa ~1,8 s mostrando o cartão, e segue até o fechamento
        self.roteiro = []  # (t_ini, t_fim, min_ini, min_fim, cartao)
        dur, pausa = B - A - 0.4, 1.8 if len(self.mks) <= 3 else 1.4
        marcos = [minutos(mk['hora']) for mk in self.mks]
        paradas = [max(self.xs[0], min(self.xs[-1], x)) for x in marcos]
        desenho = dur - pausa * len(paradas)
        pontos = [self.xs[0]] + paradas + [self.xs[-1]]
        trechos = [max(0.0, pontos[i + 1] - pontos[i]) for i in range(len(pontos) - 1)]
        tot = sum(trechos) or 1
        tempos = [max(0.35, desenho * tr / tot) for tr in trechos]
        esc = desenho / sum(tempos) if sum(tempos) > desenho else 1
        t = A
        for i, tr in enumerate(trechos):
            td = tempos[i] * esc
            self.roteiro.append((t, t + td, pontos[i], pontos[i + 1], i))  # cartão i = manchetes já vistas
            t += td
            if i < len(paradas):
                self.roteiro.append((t, t + pausa, pontos[i + 1], pontos[i + 1], i + 1))
                t += pausa
        self.F = {k: fonte(*v) for k, v in {'h1': ('InterDisplay-Bold.otf', 104), 'h2': ('InterDisplay-Bold.otf', 76), 'big': ('InterDisplay-Bold.otf', 220),
                                            'mono': ('JetBrainsMono-Bold.ttf', 34), 'monos': ('JetBrainsMono-Bold.ttf', 26), 'tit': ('Inter-Medium.otf', 42),
                                            'med': ('Inter-Medium.otf', 40), 'pq': ('Inter-Medium.otf', 26), 'num': ('InterDisplay-Bold.otf', 34),
                                            'marca': ('InterDisplay-Bold.otf', 46)}.items()}

    def X(self, t):
        return self.gx0 + (t - self.x0) / (self.x1 - self.x0) * (self.gx1 - self.gx0)

    def Y(self, v):
        return self.gy0 + (1 - (v - self.lo) / (self.hi - self.lo)) * (self.gy1 - self.gy0)

    def preco(self, t):
        antes = [p for p in self.pts if minutos(p[0]) <= t] or self.pts[:1]
        return antes[-1][1]

    def fundo(self, a=1.0):
        im = Image.new('RGB', (W, H), BG)
        d = ImageDraw.Draw(im)
        for y in range(0, H, 60):
            d.line([(0, y), (W, y)], fill=mix('#0A1422', a))
        for x in range(0, W, 60):
            d.line([(x, 0), (x, H)], fill=mix('#0A1422', a))
        d.rectangle([0, 0, W, 10], fill=ORANGE)
        try:
            ic = Image.open('assets/brand/icon-192.png').convert('RGBA').resize((60, 60))
            im.paste(ic, (W // 2 - 140, 150), ic)
        except Exception:
            pass
        d.text((W // 2 - 64, 155), 'Lect', font=self.F['marca'], fill=WHITE)
        d.text((W // 2 - 64 + d.textlength('Lect', font=self.F['marca']), 155), 'nex', font=self.F['marca'], fill=TEAL_L)
        return im, d

    def centro(self, d, y, txt, f, cor):
        d.text(((W - d.textlength(txt, font=f)) / 2, y), txt, font=f, fill=cor)

    def grafico(self, d, prog, a=1.0):
        """Desenha o gráfico até a fração 'prog' do pregão. Devolve o horário (min) até onde chegou."""
        tf = self.xs[0] + (self.xs[-1] - self.xs[0]) * prog
        d.rectangle([M - 16, self.gy0 - 40, W - M + 16, self.gy1 + 60], fill=mix(CARD, a), outline=mix(LINE, a), width=2)
        for h in range(10, 19, 2):
            x = self.X(h * 60)
            d.line([(x, self.gy0), (x, self.gy1)], fill=mix('#13233A', a))
            d.text((x - 16, self.gy1 + 16), f'{h}h', font=self.F['monos'], fill=mix(MUTED, a))
        yb = self.Y(self.base)
        for x in range(int(self.gx0), int(self.gx1), 16):
            d.line([(x, yb), (x + 8, yb)], fill=mix('#475569', a), width=2)
        vis = [(self.X(minutos(p[0])), self.Y(p[1])) for p in self.pts if minutos(p[0]) <= tf]
        if len(vis) >= 2:
            cor_ag = VERDE if self.preco(tf) >= self.base else VERMELHO
            d.polygon(vis + [(vis[-1][0], self.gy1), (vis[0][0], self.gy1)], fill=mix(cor_ag, 0.13 * a, CARD))
            d.line(vis, fill=mix(cor_ag, a), width=6, joint='curve')
            x, y = vis[-1]
            d.ellipse([x - 11, y - 11, x + 11, y + 11], fill=mix(cor_ag, a), outline=BG, width=3)
            v = (self.preco(tf) / self.base - 1) * 100
            t = pct(v)
            d.text((self.gx0 + 10, self.gy0 - 30), t, font=self.F['mono'], fill=mix(cor_ag, a))
        return tf

    def marcadores(self, d, tf, t_atual):
        for i, mk in enumerate(self.mks, 1):
            tm = minutos(mk['hora'])
            if tm > tf:
                continue
            x, y = self.X(tm), self.Y(self.preco(tm))
            perto = sum(1 for mk2 in self.mks[:i - 1] if abs(self.X(minutos(mk2['hora'])) - x) < 62)
            if perto:  # manchetes quase no mesmo horário: empilha os números para cima
                y0 = y
                y = max(self.gy0 + 34, y - 70 * perto)
                d.line([(x, y0), (x, y)], fill=ORANGE, width=3)
            for yy in range(self.gy0, self.gy1, 12):
                d.line([(x, yy), (x, yy + 6)], fill=ORANGE, width=2)
            r = 30
            d.ellipse([x - r, y - r, x + r, y + r], fill=ORANGE, outline=BG, width=5)
            d.text((x - d.textlength(str(i), font=self.F['num']) / 2, y - 21), str(i), font=self.F['num'], fill=BG)

    def card(self, d, mk, i, a):
        y0 = 1260 + (1 - eback(a)) * 60
        alt = 300
        d.rectangle([M - 16, y0, W - M + 16, y0 + alt], fill=mix(CARD, a), outline=mix(ORANGE, a), width=3)
        d.ellipse([M + 10, y0 + 30, M + 70, y0 + 90], fill=mix(ORANGE, a))
        d.text((M + 40 - d.textlength(str(i), font=self.F['num']) / 2, y0 + 39), str(i), font=self.F['num'], fill=BG)
        d.text((M + 92, y0 + 42), f'{mk["hora"]} · {mk["fonte"]}', font=self.F['monos'], fill=mix(MUTED, a))
        yy = y0 + 110
        for l in quebrar(d, mk['titulo'], self.F['tit'], W - 2 * M - 20, 2):
            d.text((M + 10, yy), l, font=self.F['tit'], fill=mix(WHITE, a))
            yy += 54
        r = mk[self.campo]
        t = f'{pct(r)} em 30 min'
        d.text((W - M - d.textlength(t, font=self.F['mono']), y0 + alt - 58), t, font=self.F['mono'], fill=mix(VERDE if r > 0 else VERMELHO, a))

    def quadro(self, t):
        if t < A:  # gancho
            im, d = self.fundo()
            s = eback(t / 0.4)
            self.centro(d, 640, 'O que mexeu no', fonte('InterDisplay-Bold.otf', 96 * (0.85 + 0.15 * s)), mix(WHITE, s))
            self.centro(d, 760, f'{self.nome} hoje?', fonte('InterDisplay-Bold.otf', 130 * (0.85 + 0.15 * s)), mix(ORANGE, s))
            if t > 0.6:
                self.centro(d, 980, f'{DIAS[self.dia.weekday()]} {self.dia:%d/%m} · notícia × preço', self.F['mono'], mix(TEAL_L, ease((t - 0.6) / 0.3)))
            return im
        if t < B:  # gráfico se desenhando + manchetes, com pausa em cada uma
            im, d = self.fundo()
            self.centro(d, 300, f'{"IBOVESPA" if self.k == "ibov" else "DÓLAR"} · {DIAS[self.dia.weekday()]} {self.dia:%d/%m}', self.F['mono'], TEAL_L)
            self.centro(d, 360, 'Cada manchete no horário em que saiu', self.F['med'], MUTED)
            seg = next((r for r in self.roteiro if r[0] <= t < r[1]), self.roteiro[-1] if t >= self.roteiro[-1][1] else self.roteiro[0])
            t0, t1, m0, m1, n = seg
            tf = m0 + (m1 - m0) * ease((t - t0) / max(0.01, t1 - t0)) if m1 > m0 else m1
            self.grafico(d, (tf - self.xs[0]) / max(1, self.xs[-1] - self.xs[0]))
            self.marcadores(d, tf, t)
            if n:
                ini = next(r[0] for r in self.roteiro if r[4] == n)
                self.card(d, self.mks[n - 1], n, min(1.0, (t - ini) / 0.35))
            elif not self.mks:
                self.centro(d, 1340, 'Sem manchetes com reação medida hoje', self.F['med'], MUTED)
            return im
        if t < C:  # resultado
            im, d = self.fundo()
            k = t - B
            self.grafico(d, 1.0, 0.35)
            self.centro(d, 300, f'{self.nome.upper()} NO FECHAMENTO', self.F['mono'], TEAL_L)
            v = self.vdia * ease(k / 1.0)
            self.centro(d, 1240, pct(v), fonte('InterDisplay-Bold.otf', 220 * (0.9 + 0.1 * eback(k / 0.5))), self.cor)
            ult = self.pts[-1][1]
            txt = f'{ult:,.0f} pontos'.replace(',', '.') if self.k == 'ibov' else f'R$ {ult:.3f}'.replace('.', ',')
            if k > 0.8:
                self.centro(d, 1500, txt, self.F['h2'], mix(WHITE, ease((k - 0.8) / 0.3)))
            return im
        # chamada
        im, d = self.fundo()
        k = t - C
        a = ease(k / 0.35)
        self.centro(d, 640, 'Todo pregão:', fonte('InterDisplay-Bold.otf', 84), mix(WHITE, a))
        self.centro(d, 750, 'notícia × preço', fonte('InterDisplay-Bold.otf', 110), mix(ORANGE, a))
        if k > 0.5:
            e = eback((k - 0.5) / 0.4)
            bw, bh = 760 * (0.85 + 0.15 * e), 140 * (0.85 + 0.15 * e)
            x0, y0 = (W - bw) / 2, 960 + (140 - bh) / 2
            d.rectangle([x0, y0, x0 + bw, y0 + bh], fill=ORANGE)
            f = fonte('InterDisplay-Bold.otf', 66 * (0.85 + 0.15 * e))
            self.centro(d, y0 + (bh - 80 * (0.85 + 0.15 * e)) / 2, 'lectnex.com.br', f, BG)
        if k > 1.0:
            c = ease((k - 1.0) / 0.3)
            self.centro(d, 1150, 'Grátis · link na bio', self.F['med'], mix(MUTED, c))
            for i, l in enumerate(('Variação do último preço antes da manchete até 30 min depois.',
                                   'O movimento seguinte não prova que a notícia foi a causa.',
                                   'Cotações de 5 min (Yahoo Finance) · conteúdo educacional')):
                self.centro(d, 1500 + i * 40, l, self.F['pq'], mix((100, 112, 130), c))
        return im


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    m = json.load(open(args[0], encoding='utf-8'))
    if not (m.get('ibov') or m.get('dolar')):
        print('Sem série do dia: reel não gerado.')
        return
    r = Reel(m)
    if '--quadros' in sys.argv:
        pasta = args[1] if len(args) > 1 else '.'
        for t in map(float, sys.argv[sys.argv.index('--quadros') + 1].split(',')):
            r.quadro(t).save(os.path.join(pasta, f'reel_{t:05.2f}.png'))
        return
    saida = args[1] if len(args) > 1 else 'reel-dia.mp4'
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-crf', '20', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', saida + '.tmp.mp4'],
                         stdin=subprocess.PIPE)
    for i in range(int(TOTAL * FPS)):
        p.stdin.write(r.quadro(i / FPS).tobytes())
    p.stdin.close()
    p.wait()
    if p.returncode == 0:
        os.replace(saida + '.tmp.mp4', saida)
        print(f'Reel do dia: {saida} ({os.path.getsize(saida) // 1024} KB)')


if __name__ == '__main__':
    main()
