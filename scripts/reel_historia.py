"""Reel do dia no padrão "um gráfico, uma conclusão" (aprovado em 19/11/2026), 1080×1920, 12,5 s, trilha lofi:
o título-conclusão entra palavra a palavra, a linha do pregão se desenha sobre a referência de ontem, a manchete com a maior
reação em 30 min aparece num cartão e a chamada fecha. Substitui o reel_dia como o Reels diário do Kit.

Uso: python3 scripts/reel_historia.py mercado.json saida.mp4 [--capa capa.png] [--story story.png] [--legenda leg.txt] [--x x.txt] [--quadros 1.4,5,11]
"""
import datetime as dt
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from grafico_dia import escolher, minutos, pct, titulo_conclusao  # noqa: E402
from og_leitura import BG, CARD, DIAS, LINE, MUTED, ORANGE, TEAL_L, VERDE, VERMELHO, WHITE, fonte, quebrar  # noqa: E402
from reel_dia import eback, ease, mix  # noqa: E402

W, H, M, FPS = 1080, 1920, 80, 30
B, R, MO = 'InterDisplay-Bold.otf', 'Inter-Medium.otf', 'JetBrainsMono-Bold.ttf'
T_TIT, T_LINHA, T_FIM, TOTAL = 1.6, 7.5, 9.0, 12.5
PERGUNTAS = ['Você estava posicionado nesse movimento? Conta aqui 👇', 'Essa manchete mexeu com o seu trade? 👇',
             'Você teria comprado ou vendido depois dessa notícia? 👇', 'Amanhã continua ou devolve? Deixe seu palpite 👇']


class Historia:
    def __init__(self, m):
        self.m = m
        self.k, self.campo, self.mks, self.vdia = escolher(m)
        s = m[self.k]
        self.pts = [(minutos(h), v) for h, v in s['pontos'] if self.k == 'ibov' or minutos(h) <= 18 * 60 + 25]
        self.ant = s.get('anterior') or self.pts[0][1]
        self.dia = dt.date.fromisoformat(m['data'])
        self.cor = VERDE if self.vdia >= 0 else VERMELHO
        self.nome = 'Ibovespa' if self.k == 'ibov' else 'dólar'
        self.titulo = titulo_conclusao(m, self.k, self.vdia)
        self.top = max(self.mks, key=lambda x: abs(x[self.campo])) if self.mks else None
        outro = m.get('dolar' if self.k == 'ibov' else 'ibov') or {}
        self.sub = ''
        if outro.get('pontos'):
            vo = (outro['pontos'][-1][1] / (outro.get('anterior') or outro['pontos'][0][1]) - 1) * 100
            self.sub = f'{"Dólar" if self.k == "ibov" else "Ibovespa"} {pct(vo)} no mesmo dia'
        self.fmt = (lambda v: f'{v:,.0f}'.replace(',', '.')) if self.k == 'ibov' else (lambda v: f'R$ {v:.2f}'.replace('.', ','))
        self.gx0, self.gx1, self.gy0, self.gy1 = M, W - M - 190, 720, 1400
        ys = [v for _, v in self.pts] + [self.ant]
        self.lo, self.hi = min(ys), max(ys)
        self.pad = (self.hi - self.lo) * 0.12 or self.ant * 0.002
        self.base = Image.new('RGB', (W, H), BG)
        d0 = ImageDraw.Draw(self.base)
        for x in range(0, W, 60):
            d0.line([(x, 0), (x, H)], fill='#0A1422')
        for y in range(0, H, 60):
            d0.line([(0, y), (W, y)], fill='#0A1422')

    def X(self, t):
        return self.gx0 + (t - self.pts[0][0]) / max(1, self.pts[-1][0] - self.pts[0][0]) * (self.gx1 - self.gx0)

    def Y(self, v):
        return self.gy1 - (v - self.lo + self.pad) / (self.hi - self.lo + 2 * self.pad) * (self.gy1 - self.gy0)

    def quadro(self, t):
        im = self.base.copy()
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, W * min(1, t / TOTAL), 10], fill=TEAL_L)
        fb = fonte(B, 44)
        d.text((M, 230), 'Lect', font=fb, fill=WHITE)
        d.text((M + d.textlength('Lect', font=fb), 230), 'nex', font=fb, fill=TEAL_L)
        tag = f'GRÁFICO DO DIA · {self.dia:%d/%m}'
        d.text((W - M - d.textlength(tag, font=fonte(MO, 26)), 244), tag, font=fonte(MO, 26), fill=MUTED)
        ft = fonte(B, 92)
        ls = quebrar(d, self.titulo, ft, W - 2 * M, 3)
        tot = sum(len(l.split()) for l in ls)
        prog, k = ease(t / 1.2) * tot, 0
        for i, l in enumerate(ls):
            x = M
            for w in l.split():
                a = max(0, min(1, prog - k))
                d.text((x, 330 + i * 104 + (1 - a) * 14), w, font=ft, fill=mix(WHITE, a))
                x += d.textlength(w + ' ', font=ft)
                k += 1
        d.text((M, 340 + len(ls) * 104), self.sub, font=fonte(R, 40), fill=mix(MUTED, ease((t - 1.0) / 0.5)))
        if t >= T_TIT:
            self._grafico(d, t)
        if t >= T_FIM:
            c = ease((t - T_FIM) / 0.5)
            d.rectangle([M, 1730, W - M, 1830], fill=mix(TEAL_L, c))
            tx = 'Todo pregão em lectnex.com.br'
            d.text(((W - d.textlength(tx, font=fonte(B, 46))) / 2, 1752), tx, font=fonte(B, 46), fill=BG)
        d.text((M, 1860), 'Fonte: Yahoo Finance (5 min) · educacional, não é recomendação', font=fonte(MO, 22), fill=MUTED)
        return im

    def _grafico(self, d, t):
        a = ease((t - T_TIT) / 0.4)
        fm = fonte(MO, 26)
        d.line([(self.gx0, self.Y(self.ant)), (self.gx1, self.Y(self.ant))], fill=mix(LINE, a), width=3)
        d.text((self.gx1 + 16, self.Y(self.ant) - 16), 'ontem\n' + self.fmt(self.ant), font=fm, fill=mix(MUTED, a))
        for h in range(10, 19, 2):
            if self.pts[0][0] <= h * 60 <= self.pts[-1][0]:
                d.text((self.X(h * 60) - 20, self.gy1 + 16), f'{h}h', font=fm, fill=mix(MUTED, a))
        k = ease(min(1, (t - T_TIT) / (T_LINHA - T_TIT)))
        tf = self.pts[0][0] + (self.pts[-1][0] - self.pts[0][0]) * k
        vis = [(self.X(tt), self.Y(v)) for tt, v in self.pts if tt <= tf]
        vv = [v for tt, v in self.pts if tt <= tf]
        if len(vis) > 1:
            d.line(vis, fill=self.cor, width=8, joint='curve')
        if vis:
            x, y = vis[-1]
            d.ellipse([x - 11, y - 11, x + 11, y + 11], fill=self.cor)
            d.text((self.gx1 + 16, y - 34), self.fmt(vv[-1]), font=fonte(MO, 36 if self.k == 'dolar' else 32), fill=WHITE)
            d.text((self.gx1 + 16, y + 8), pct((vv[-1] / self.ant - 1) * 100), font=fonte(MO, 30), fill=self.cor)
        if self.top:
            tm = minutos(self.top['hora'])
            if tf >= tm:
                e = eback((tf - tm) / 25)
                antes = [v for tt, v in self.pts if tt <= tm] or [self.pts[0][1]]
                x, y = self.X(tm), self.Y(antes[-1])
                d.ellipse([x - 12 * e, y - 12 * e, x + 12 * e, y + 12 * e], fill=ORANGE)
                by = 1500
                d.line([(x, y), (x, by)], fill=ORANGE, width=3)
                d.rectangle([M, by, W - M, by + 190], fill=CARD, outline=ORANGE, width=3)
                d.text((M + 26, by + 22), f'{self.top["hora"]} · {self.nome} {pct(self.top[self.campo])} em 30 min', font=fonte(MO, 30), fill=ORANGE)
                for i, l in enumerate(quebrar(d, self.top['titulo'], fonte(B, 40), W - 2 * M - 52, 2)):
                    d.text((M + 26, by + 72 + i * 50), l, font=fonte(B, 40), fill=WHITE)


def capa(h, saida):
    """Capa: o título-conclusão e o gráfico já completo (a grade do perfil mostra o meio)."""
    im = h.quadro(T_LINHA + 0.3)
    im.save(saida, 'PNG', optimize=True)


def story(h, saida):
    """Story do fechamento no padrão novo: o gráfico completo e, embaixo, espaço para a enquete (figurinha posta no app)."""
    im = h.quadro(T_LINHA + 1.0)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 10], fill=TEAL_L)
    d.rectangle([M, 1730, W - M, 1830], outline=TEAL_L, width=3)
    tx = 'Amanhã continua ou devolve? Vote aqui'
    f = fonte(B, 40)
    d.text(((W - d.textlength(tx, font=f)) / 2, 1756), tx, font=f, fill=TEAL_L)
    im.save(saida, 'PNG', optimize=True)


def legenda(h):
    q = PERGUNTAS[h.dia.toordinal() % len(PERGUNTAS)]
    linhas = [f'{h.titulo} {"📈" if h.vdia >= 0 else "📉"}', '']
    if h.top:
        linhas.append(f'A maior reação veio às {h.top["hora"]}: {pct(h.top[h.campo])} em 30 minutos depois de "{h.top["titulo"]}".')
    linhas += [q, '', '💬 Comunidade de traders no Discord: discord.gg/kM6YcQA82P', '👑 Lista de fundadores da Lectnex Pro (grátis): lectnex.com.br/pro',
               'Conteúdo educacional, não é recomendação. Todo pregão em lectnex.com.br.',
               '#ibovespa #dolar #daytrade #miniindice #minidolar #b3 #mercadofinanceiro']
    return '\n'.join(linhas)


def texto_x(h):
    partes = [f'📊 {h.titulo}.']
    if h.top:
        partes.append(f'Maior reação: {h.top["hora"]}, {pct(h.top[h.campo])} em 30 min após "{h.top["titulo"][:110]}".')
    partes.append('O gráfico de todo pregão: https://lectnex.com.br/hoje.html')
    return '\n\n'.join(partes)


def main():
    opc = {sys.argv[i + 1] for i, a in enumerate(sys.argv[:-1]) if a in ('--capa', '--legenda', '--quadros', '--x', '--story')}
    args = [a for a in sys.argv[1:] if not a.startswith('--') and a not in opc]
    m = json.load(open(args[0], encoding='utf-8'))
    if not (m.get('ibov') or m.get('dolar')):
        print('Sem série do dia: reel não gerado.')
        return
    h = Historia(m)
    saida = args[1] if len(args) > 1 else 'reel-historia.mp4'
    val = lambda o: sys.argv[sys.argv.index(o) + 1] if o in sys.argv else None
    if val('--quadros'):
        for t in map(float, val('--quadros').split(',')):
            h.quadro(t).save(f'{os.path.splitext(saida)[0]}-q{t}.png')
        return
    if val('--story'):
        story(h, val('--story'))
    if val('--capa'):
        capa(h, val('--capa'))
    if val('--legenda'):
        open(val('--legenda'), 'w', encoding='utf-8').write(legenda(h))
    if val('--x'):
        open(val('--x'), 'w', encoding='utf-8').write(texto_x(h))
    tmp = saida + '.tmp.mp4'
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-crf', '21', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', tmp], stdin=subprocess.PIPE)
    for i in range(int(TOTAL * FPS)):
        p.stdin.write(h.quadro(i / FPS).tobytes())
    p.stdin.close()
    p.wait()
    if p.returncode != 0:
        raise SystemExit('ffmpeg falhou')
    os.replace(tmp, saida)
    try:
        from trilha import juntar, trilha
        wav = trilha(TOTAL, pops=[0.2, T_TIT], sinal=T_LINHA, final=T_FIM, saida=saida + '.wav')
        juntar(saida, wav)
        os.remove(wav)
    except Exception as e:
        print(f'::warning::Reel sem áudio ({e.__class__.__name__}: {e})')
    print(f'Reel do dia: {saida} ({os.path.getsize(saida) // 1024} KB)')


if __name__ == '__main__':
    main()
