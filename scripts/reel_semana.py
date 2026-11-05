"""Reel da semana (1080×1920, 20 s, sem áudio): o Ibovespa da semana se desenhando dia a dia, a manchete que mais mexeu
em cada pregão, o resultado da semana (Ibovespa e dólar) e o placar "o histórico acertou?". Roda no fechamento de sexta.
Lê data/dias/AAAA-MM-DD.json (gravados pelo fechamento), data/placar-termometro.json e data/placar-historico.json.
Uso: python3 scripts/reel_semana.py [saida.mp4] [--data AAAA-MM-DD] [--capa capa.png] [--legenda legenda.txt] [--quadros t1,t2 pasta] [--forcar]
"""
import datetime as dt
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from grafico_dia import minutos, pct  # noqa: E402
from og_leitura import CARD, LINE, MUTED, ORANGE, TEAL_L, VERDE, VERMELHO, WHITE, fonte, quebrar  # noqa: E402
from reel_dia import BG, M, eback, ease, mix  # noqa: E402

W, H, FPS = 1080, 1920, 30
A, B, C, TOTAL = 1.8, 14.0, 17.0, 20.0  # gancho | semana dia a dia | resultado | placar e chamada
BRT = dt.timezone(dt.timedelta(hours=-3))
SIG = ['SEG', 'TER', 'QUA', 'QUI', 'SEX']


def ler(p):
    try:
        return json.load(open(p, encoding='utf-8'))
    except Exception:
        return {}


class Semana:
    def __init__(self, hoje):
        self.ini = hoje - dt.timedelta(days=hoje.weekday())
        self.fim = self.ini + dt.timedelta(days=4)
        self.dias = []
        for i in range(5):
            d = self.ini + dt.timedelta(days=i)
            m = ler(f'data/dias/{d.isoformat()}.json')
            if (m.get('ibov') or {}).get('pontos'):
                mks = [x for x in m.get('marcadores', []) if x.get('ibov30') is not None]
                top = max(mks, key=lambda x: abs(x['ibov30'])) if mks else None
                self.dias.append({'d': d, 'm': m, 'top': top})
        if not self.dias:
            return
        # série contínua: cada pregão ocupa uma faixa igual no eixo x
        self.serie, self.cortes = [], []
        for j, di in enumerate(self.dias):
            pts = di['m']['ibov']['pontos']
            t0, t1 = minutos(pts[0][0]), minutos(pts[-1][0])
            self.cortes.append(len(self.serie))
            for p in pts:
                self.serie.append((j + (minutos(p[0]) - t0) / max(1, t1 - t0) * 0.96, p[1]))
        self.base = self.dias[0]['m']['ibov'].get('anterior') or self.serie[0][1]
        ys = [v for _, v in self.serie] + [self.base]
        pad = (max(ys) - min(ys)) * 0.1 or self.base * 0.002
        self.lo, self.hi = min(ys) - pad, max(ys) + pad
        self.vsem = (self.serie[-1][1] / self.base - 1) * 100
        d0, d1 = self.dias[0]['m'].get('dolar') or {}, self.dias[-1]['m'].get('dolar') or {}
        self.vdol = ((d1['pontos'][-1][1] / (d0.get('anterior') or d0['pontos'][0][1]) - 1) * 100) if d0.get('pontos') and d1.get('pontos') else None
        self.cor = VERDE if self.vsem >= 0 else VERMELHO
        self.n = len(self.dias)
        self.gx0, self.gx1, self.gy0, self.gy1 = M + 10, W - M - 10, 560, 1080
        # placar da semana
        pt = [x for x in ler('data/placar-termometro.json').get('dias', []) if self.ini.isoformat() <= x['data'] <= self.fim.isoformat()]
        ph = [e for e in ler('data/placar-historico.json').get('eventos', []) if self.ini.isoformat() <= e['data'] <= self.fim.isoformat()]
        conta = lambda lst, f: (sum(1 for x in lst for k in ('win', 'wdo') if f(x, k) is not None), sum(1 for x in lst for k in ('win', 'wdo') if f(x, k)))
        self.pterm = conta(pt, lambda x, k: x[k].get('acerto') if x.get(k) else None)
        self.phist = conta(ph, lambda e, k: (e.get('acerto') or {}).get(k))
        self.F = {k: fonte(*v) for k, v in {'mono': ('JetBrainsMono-Bold.ttf', 34), 'monos': ('JetBrainsMono-Bold.ttf', 26), 'tit': ('Inter-Medium.otf', 42),
                                            'med': ('Inter-Medium.otf', 40), 'pq': ('Inter-Medium.otf', 26), 'num': ('InterDisplay-Bold.otf', 40),
                                            'marca': ('InterDisplay-Bold.otf', 46)}.items()}

    def X(self, x):
        return self.gx0 + x / self.n * (self.gx1 - self.gx0)

    def Y(self, v):
        return self.gy0 + (1 - (v - self.lo) / (self.hi - self.lo)) * (self.gy1 - self.gy0)

    def fundo(self):
        im = Image.new('RGB', (W, H), BG)
        d = ImageDraw.Draw(im)
        for y in range(0, H, 60):
            d.line([(0, y), (W, y)], fill=mix('#0A1422', 1))
        for x in range(0, W, 60):
            d.line([(x, 0), (x, H)], fill=mix('#0A1422', 1))
        d.rectangle([0, 0, W, 10], fill=TEAL_L)
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

    def grafico(self, d, ate, a=1.0):
        d.rectangle([M - 16, self.gy0 - 40, W - M + 16, self.gy1 + 70], fill=mix(CARD, a), outline=mix(LINE, a), width=2)
        for j, di in enumerate(self.dias):
            x = self.X(j)
            if j:
                d.line([(x, self.gy0), (x, self.gy1)], fill=mix('#1E3350', a), width=2)
            lab = SIG[di['d'].weekday()]
            d.text((self.X(j + 0.48) - d.textlength(lab, font=self.F['monos']) / 2, self.gy1 + 20), lab, font=self.F['monos'],
                   fill=mix(WHITE if j < ate else MUTED, a))
        yb = self.Y(self.base)
        for x in range(int(self.gx0), int(self.gx1), 16):
            d.line([(x, yb), (x + 8, yb)], fill=mix('#475569', a), width=2)
        vis = [(self.X(x), self.Y(v)) for x, v in self.serie if x <= ate]
        if len(vis) >= 2:
            ult = [v for x, v in self.serie if x <= ate][-1]
            c = VERDE if ult >= self.base else VERMELHO
            d.polygon(vis + [(vis[-1][0], self.gy1), (vis[0][0], self.gy1)], fill=mix(c, 0.13 * a, CARD))
            d.line(vis, fill=mix(c, a), width=5, joint='curve')
            x, y = vis[-1]
            d.ellipse([x - 10, y - 10, x + 10, y + 10], fill=mix(c, a), outline=BG, width=3)
            d.text((self.gx0 + 10, self.gy0 - 30), pct((ult / self.base - 1) * 100) + ' na semana', font=self.F['mono'], fill=mix(c, a))
        for j, di in enumerate(self.dias):  # marcador da manchete do dia
            if not di['top'] or j + 0.5 > ate:
                continue
            pts = di['m']['ibov']['pontos']
            t0, t1, tm = minutos(pts[0][0]), minutos(pts[-1][0]), minutos(di['top']['hora'])
            xr = j + max(0.0, min(1.0, (tm - t0) / max(1, t1 - t0))) * 0.96
            perto = [v for x, v in self.serie if x <= xr]
            if not perto:
                continue
            x, y = self.X(xr), self.Y(perto[-1])
            d.ellipse([x - 22, y - 22, x + 22, y + 22], fill=mix(ORANGE, a), outline=BG, width=4)
            n = str(j + 1)
            d.text((x - d.textlength(n, font=self.F['monos']) / 2, y - 16), n, font=self.F['monos'], fill=BG)

    def card(self, d, j, a):
        di = self.dias[j]
        y0 = 1230 + (1 - eback(a)) * 50
        d.rectangle([M - 16, y0, W - M + 16, y0 + 340], fill=mix(CARD, a), outline=mix(ORANGE, a), width=3)
        vdia = (di['m']['ibov']['pontos'][-1][1] / (di['m']['ibov'].get('anterior') or di['m']['ibov']['pontos'][0][1]) - 1) * 100
        d.text((M + 10, y0 + 30), f'{["SEGUNDA", "TERÇA", "QUARTA", "QUINTA", "SEXTA"][di["d"].weekday()]} {di["d"]:%d/%m}', font=self.F['mono'], fill=mix(TEAL_L, a))
        t = f'Ibov {pct(vdia)}'
        d.text((W - M - d.textlength(t, font=self.F['mono']), y0 + 30), t, font=self.F['mono'], fill=mix(VERDE if vdia >= 0 else VERMELHO, a))
        if di['top']:
            mk = di['top']
            d.text((M + 10, y0 + 92), f'{mk["hora"]} · {mk["fonte"]}', font=self.F['monos'], fill=mix(MUTED, a))
            yy = y0 + 136
            for l in quebrar(d, mk['titulo'], self.F['tit'], W - 2 * M - 20, 2):
                d.text((M + 10, yy), l, font=self.F['tit'], fill=mix(WHITE, a))
                yy += 54
            r = mk['ibov30']
            t = f'{pct(r)} em 30 min'
            d.text((W - M - d.textlength(t, font=self.F['mono']), y0 + 282), t, font=self.F['mono'], fill=mix(VERDE if r > 0 else VERMELHO, a))
        else:
            d.text((M + 10, y0 + 140), 'Sem manchete com reação medida neste dia.', font=self.F['med'], fill=mix(MUTED, a))

    def quadro(self, t):
        im, d = self.fundo()
        if t < A:
            s = eback(t / 0.4)
            self.centro(d, 620, 'A semana do', fonte('InterDisplay-Bold.otf', 100 * (0.85 + 0.15 * s)), mix(WHITE, s))
            self.centro(d, 740, 'Ibovespa', fonte('InterDisplay-Bold.otf', 150 * (0.85 + 0.15 * s)), mix(ORANGE, s))
            self.centro(d, 920, 'em 20 segundos', fonte('InterDisplay-Bold.otf', 84 * (0.85 + 0.15 * s)), mix(WHITE, s))
            if t > 0.7:
                self.centro(d, 1090, f'{self.ini:%d/%m} a {self.fim:%d/%m}', self.F['mono'], mix(TEAL_L, ease((t - 0.7) / 0.3)))
            return im
        if t < B:
            por = (B - A) / self.n
            j = min(self.n - 1, int((t - A) / por))
            k = (t - A - j * por) / por
            self.centro(d, 300, 'IBOVESPA · A SEMANA DIA A DIA', self.F['mono'], TEAL_L)
            self.centro(d, 360, 'A manchete que mais mexeu em cada pregão', self.F['med'], MUTED)
            self.grafico(d, j + min(1.0, ease(k / 0.55)) * 0.999)
            self.card(d, j, min(1.0, max(0.0, (k - 0.35) / 0.25)))
            return im
        if t < C:
            k = t - B
            self.grafico(d, self.n, 0.3)
            self.centro(d, 300, 'RESULTADO DA SEMANA', self.F['mono'], TEAL_L)
            self.centro(d, 1180, 'Ibovespa', self.F['med'], MUTED)
            self.centro(d, 1230, pct(self.vsem * ease(k / 0.9)), fonte('InterDisplay-Bold.otf', 190 * (0.9 + 0.1 * eback(k / 0.5))), self.cor)
            if self.vdol is not None and k > 0.8:
                c = ease((k - 0.8) / 0.3)
                self.centro(d, 1480, f'Dólar {pct(self.vdol)}', fonte('InterDisplay-Bold.otf', 76), mix(VERDE if self.vdol >= 0 else VERMELHO, c))
            return im
        k = t - C
        a = ease(k / 0.35)
        self.centro(d, 520, 'O nosso placar da semana', fonte('InterDisplay-Bold.otf', 70), mix(WHITE, a))
        y = 660
        for rot, (n, ok) in (('Termômetro da manhã', self.pterm), ('Histórico nos eventos', self.phist)):
            if not n:
                continue
            d.rectangle([M + 40, y, W - M - 40, y + 150], fill=mix(CARD, a), outline=mix(LINE, a), width=2)
            d.text((M + 80, y + 50), rot, font=self.F['med'], fill=mix(MUTED, a))
            t2 = f'{ok} de {n}'
            f2 = fonte('InterDisplay-Bold.otf', 72)
            d.text((W - M - 80 - d.textlength(t2, font=f2), y + 34), t2, font=f2, fill=mix(VERDE if ok / n >= 0.5 else VERMELHO, a))
            y += 180
        if y == 660:
            self.centro(d, 700, 'Placar começa a contar nesta semana', self.F['med'], mix(MUTED, a))
            y += 100
        self.centro(d, y + 20, 'Com os erros também.', self.F['med'], mix(TEAL_L, a))
        if k > 0.8:
            e = eback((k - 0.8) / 0.4)
            bw, bh = 820 * (0.85 + 0.15 * e), 140 * (0.85 + 0.15 * e)
            x0, y0 = (W - bw) / 2, y + 130 + (140 - bh) / 2
            d.rectangle([x0, y0, x0 + bw, y0 + bh], fill=ORANGE)
            f = fonte('InterDisplay-Bold.otf', 60 * (0.85 + 0.15 * e))
            self.centro(d, y0 + (bh - 74 * (0.85 + 0.15 * e)) / 2, 'lectnex.com.br/placar', f, BG)
        if k > 1.3:
            c = ease((k - 1.3) / 0.3)
            for i, l in enumerate(('Reação de 30 min depois da manchete; o movimento não prova causa.',
                                   'Ibovespa e dólar à vista (Yahoo Finance) · conteúdo educacional')):
                self.centro(d, 1560 + i * 40, l, self.F['pq'], mix((100, 112, 130), c))
        return im

    def legenda(self):
        top = max((di for di in self.dias if di['top']), key=lambda di: abs(di['top']['ibov30']), default=None)
        l = [f'A semana do Ibovespa em 20 segundos ({self.ini:%d/%m} a {self.fim:%d/%m}): {pct(self.vsem)}'
             + (f' · dólar {pct(self.vdol)}' if self.vdol is not None else ''), '']
        if top:
            l.append(f'A manchete que mais mexeu: {SIG[top["d"].weekday()].lower()} às {top["top"]["hora"]}, {pct(top["top"]["ibov30"])} em 30 min.')
        n, ok = self.pterm
        if n:
            l.append(f'Nosso termômetro acertou {ok} de {n} nesta semana. Placar completo, com os erros, no link da bio.')
        l += ['Qual dia da semana você operou melhor? Comente.', '', 'Conteúdo educacional, não é recomendação.',
              '#ibovespa #dolar #daytrade #miniindice #minidolar #b3 #mercadofinanceiro']
        return '\n'.join(l)

    def capa(self, saida):
        im, d = self.fundo()
        self.centro(d, 470, f'RESUMO DA SEMANA · {self.ini:%d/%m} A {self.fim:%d/%m}', self.F['mono'], TEAL_L)
        self.centro(d, 560, 'A semana do', fonte('InterDisplay-Bold.otf', 100), WHITE)
        self.centro(d, 680, 'Ibovespa', fonte('InterDisplay-Bold.otf', 140), ORANGE)
        self.centro(d, 860, pct(self.vsem), fonte('InterDisplay-Bold.otf', 220), self.cor)
        gx0, gx1, gy0, gy1 = 160, W - 160, 1160, 1400
        X = lambda x: gx0 + x / self.n * (gx1 - gx0)
        Y = lambda v: gy0 + (1 - (v - self.lo) / (self.hi - self.lo)) * (gy1 - gy0)
        pts = [(X(x), Y(v)) for x, v in self.serie]
        d.polygon(pts + [(pts[-1][0], gy1), (pts[0][0], gy1)], fill=mix(self.cor, 0.15))
        d.line(pts, fill=self.cor, width=7, joint='curve')
        self.centro(d, 1450, 'em 20 segundos', self.F['med'], MUTED)
        im.save(saida, 'PNG', optimize=True)


def main():
    opc = {sys.argv[i + 1] for i, a in enumerate(sys.argv[:-1]) if a in ('--capa', '--legenda', '--quadros', '--data')}
    args = [a for a in sys.argv[1:] if not a.startswith('--') and a not in opc]
    hoje = dt.datetime.now(BRT).date()
    if '--data' in sys.argv:
        hoje = dt.date.fromisoformat(sys.argv[sys.argv.index('--data') + 1])
    if hoje.weekday() != 4 and '--forcar' not in sys.argv:
        print('Reel da semana só às sextas.')
        return
    s = Semana(hoje)
    if len(s.dias) < 2:
        print('Menos de 2 pregões na semana: reel da semana não gerado.')
        return
    if '--quadros' in sys.argv:
        pasta = args[0] if args else '.'
        for t in map(float, sys.argv[sys.argv.index('--quadros') + 1].split(',')):
            s.quadro(t).save(os.path.join(pasta, f'semana_{t:05.2f}.png'))
        return
    saida = args[0] if args else 'reel-semana.mp4'
    if '--capa' in sys.argv:
        s.capa(sys.argv[sys.argv.index('--capa') + 1])
    if '--legenda' in sys.argv:
        open(sys.argv[sys.argv.index('--legenda') + 1], 'w', encoding='utf-8').write(s.legenda())
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-crf', '20', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', saida + '.tmp.mp4'],
                         stdin=subprocess.PIPE)
    for i in range(int(TOTAL * FPS)):
        p.stdin.write(s.quadro(i / FPS).tobytes())
    p.stdin.close()
    p.wait()
    if p.returncode == 0:
        os.replace(saida + '.tmp.mp4', saida)
        print(f'Reel da semana: {saida} ({os.path.getsize(saida) // 1024} KB, {len(s.dias)} pregões)')


if __name__ == '__main__':
    main()
