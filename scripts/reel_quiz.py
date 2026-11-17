"""Reels-desafio "SUBIU ou CAIU?" (1080×1920, ~19 s): 3 manchetes REAIS do dia, uma por vez, com contagem 3-2-1 para a pessoa
chutar se o Ibovespa (ou o dólar) subiu ou caiu nos 30 minutos seguintes; depois a resposta com o mini gráfico. Termina pedindo
"quantas você acertou?" nos comentários. Formato de jogo: prende até o fim, gera comentário e replay (o que o algoritmo mais premia).
Mesmos dados do Reels do dia (mercado.json do fechamento).

Uso: python3 scripts/reel_quiz.py mercado.json saida.mp4 [--capa capa.png] [--legenda leg.txt] [--x x.txt] [--quadros 1,4,6]
"""
import json
import os
import re
import subprocess
import sys

from PIL import ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from grafico_dia import minutos, pct  # noqa: E402
from og_leitura import CARD, DIAS, LINE, MUTED, ORANGE, TEAL_L, VERDE, VERMELHO, WHITE, fonte, quebrar  # noqa: E402
from reel_dia import FPS, H, M, W, Reel, ease, eback, mix  # noqa: E402

GANCHO, RODADA, FIM = 1.8, 5.0, 2.4
CONTA0, CONTA1 = 0.5, 3.4  # contagem dentro da rodada; depois, a resposta
DISCORD = 'discord.gg/kM6YcQA82P'
DICA = re.compile(r'\b(alta|baixa|sob[ea]|subiu|ca[ií]|caiu|recua|avança|dispara|despenca|salta|tomba|valoriza|desvaloriza|ganho|perda|queda)', re.I)


class Quiz(Reel):
    def __init__(self, m):
        super().__init__(m)
        # manchetes que já entregam a resposta ("dólar sobe", "Ibovespa cai") deixam o desafio sem graça: ficam de fora
        todas = [mk for mk in m.get('marcadores', []) if mk.get(self.campo) is not None and abs(mk[self.campo]) >= 0.05]
        vistos, unicas = set(), []
        for mk in sorted(todas, key=lambda x: -abs(x[self.campo])):  # mesma manchete em 2 fontes: fica uma
            chave = mk.get('titulo', '')[:40].lower()
            if chave not in vistos and not any(abs(minutos(mk['hora']) - minutos(u['hora'])) < 20 for u in unicas):
                vistos.add(chave); unicas.append(mk)
        todas = unicas
        boas = [mk for mk in todas if not DICA.search(mk.get('titulo', ''))]
        escolha = sorted(boas if len(boas) >= 2 else todas, key=lambda x: -abs(x[self.campo]))[:3]
        self.mks = sorted(escolha, key=lambda x: x['hora'])
        self.total = GANCHO + RODADA * len(self.mks) + FIM
        self.Fq = {'g': fonte('InterDisplay-Bold.otf', 118), 'm': fonte('InterDisplay-Bold.otf', 72), 'b': fonte('InterDisplay-Bold.otf', 64),
                   'tit': fonte('InterDisplay-Bold.otf', 54), 'cont': fonte('InterDisplay-Bold.otf', 150), 'res': fonte('InterDisplay-Bold.otf', 120)}

    def gancho(self, t):
        im, d = self.fundo()
        s = eback(t / 0.4)
        self.centro(d, 470, f'DESAFIO · {DIAS[self.dia.weekday()]} {self.dia:%d/%m}', self.F['mono'], mix(TEAL_L, s))
        self.centro(d, 580, f'{len(self.mks)} manchetes reais de hoje.', self.Fq['m'], mix(WHITE, s))
        self.centro(d, 690, f'O {self.nome}', self.Fq['m'], mix(WHITE, ease((t - 0.25) / 0.3)))
        e = eback((t - 0.5) / 0.4)
        f = fonte('InterDisplay-Bold.otf', int(150 * (0.8 + 0.2 * e)))
        self.centro(d, 830, 'SUBIU', f, mix(VERDE, ease((t - 0.5) / 0.3)))
        self.centro(d, 990, 'ou', self.Fq['m'], mix(MUTED, ease((t - 0.6) / 0.3)))
        self.centro(d, 1090, 'CAIU?', f, mix(VERMELHO, ease((t - 0.7) / 0.3)))
        self.centro(d, 1340, 'Responda antes da contagem acabar', self.F['med'], mix(MUTED, ease((t - 1.0) / 0.3)))
        return im

    def mini(self, d, mk, a, y0=1290, alt=300):
        """Mini gráfico de 30 min antes a 30 min depois da manchete."""
        tm = minutos(mk['hora'])
        pts = [(minutos(p[0]), p[1]) for p in self.pts if tm - 30 <= minutos(p[0]) <= tm + 30]
        if len(pts) < 3:
            return
        lo, hi = min(v for _, v in pts), max(v for _, v in pts)
        pad = (hi - lo) * 0.15 or hi * 0.001
        x0, x1 = M + 20, W - M - 20
        X = lambda t: x0 + (t - (tm - 30)) / 60 * (x1 - x0)
        Y = lambda v: y0 + (hi + pad - v) / (hi - lo + 2 * pad) * alt
        d.rectangle([M - 16, y0 - 20, W - M + 16, y0 + alt + 20], fill=mix(CARD, a), outline=mix(LINE, a), width=2)
        cor = VERDE if mk[self.campo] > 0 else VERMELHO
        vis = [p for p in pts if p[0] <= tm + 30 * ease(a)]
        antes = [(X(t), Y(v)) for t, v in vis if t <= tm]
        depois = [(X(t), Y(v)) for t, v in vis if t >= tm]
        if len(antes) > 1:
            d.line(antes, fill=mix((120, 130, 150), a), width=6, joint='curve')
        if len(depois) > 1:
            d.line(depois, fill=mix(cor, a), width=8, joint='curve')
        for yy in range(y0 - 10, y0 + alt + 10, 14):
            d.line([(X(tm), yy), (X(tm), yy + 7)], fill=mix(ORANGE, a), width=3)
        d.text((X(tm) + 10, y0 - 10), f'{mk["hora"]} manchete', font=self.F['monos'], fill=mix(ORANGE, a))

    def rodada(self, i, t):
        im, d = self.fundo()
        mk = self.mks[i]
        a = ease(t / 0.35)
        sobe = mk[self.campo] > 0
        self.centro(d, 250, f'RODADA {i + 1}/{len(self.mks)}', self.F['mono'], mix(TEAL_L, a))
        self.centro(d, 305, f'{"IBOVESPA" if self.k == "ibov" else "DÓLAR"} nos 30 min seguintes', self.F['med'], mix(MUTED, a))
        # cartão da manchete
        y0 = 400 + (1 - eback(t / 0.4)) * 50
        linhas = quebrar(d, mk['titulo'], self.Fq['tit'], W - 2 * M - 40, 4)
        alt = 130 + 68 * len(linhas)
        d.rectangle([M - 16, y0, W - M + 16, y0 + alt], fill=mix(CARD, a), outline=mix(ORANGE, a), width=4)
        d.text((M + 14, y0 + 30), f'{mk["hora"]} · {mk.get("fonte", "")}'[:48], font=self.F['monos'], fill=mix(MUTED, a))
        for j, l in enumerate(linhas):
            d.text((M + 14, y0 + 84 + j * 68), l, font=self.Fq['tit'], fill=mix(WHITE, a))
        # botões SUBIU / CAIU
        by, bh, bw = 980, 170, (W - 2 * M - 30) / 2
        rev = max(0.0, t - CONTA1)
        for k, (rot, cor, certo) in enumerate((('▲ SUBIU', VERDE, sobe), ('▼ CAIU', VERMELHO, not sobe))):
            x = M + k * (bw + 30)
            if rev <= 0:
                d.rectangle([x, by, x + bw, by + bh], fill=mix(CARD, a), outline=mix(cor, a), width=5)
                c = mix(cor, a)
            elif certo:
                e = eback(rev / 0.35)
                g = 10 * (1 - e)
                d.rectangle([x - 12 + g, by - 12 + g, x + bw + 12 - g, by + bh + 12 - g], fill=cor)
                c = (12, 26, 42)
            else:
                d.rectangle([x, by, x + bw, by + bh], fill=mix(CARD, 0.5), outline=mix(LINE, 1), width=3)
                c = mix(MUTED, 0.5)
            d.text((x + (bw - d.textlength(rot, font=self.Fq['b'])) / 2, by + (bh - 74) / 2), rot, font=self.Fq['b'], fill=c)
        if rev <= 0:  # contagem 3-2-1 + barra
            k = (t - CONTA0) / (CONTA1 - CONTA0)
            if k >= 0:
                n = 3 - min(2, int(k * 3))
                s = eback((k * 3) % 1 / 0.3)
                f = fonte('InterDisplay-Bold.otf', int(170 * (0.75 + 0.25 * s)))
                self.centro(d, 1250, str(n), f, ORANGE)
                bx = W - 2 * M
                d.rectangle([M, 1500, M + bx, 1516], fill=mix(LINE, 1))
                d.rectangle([M, 1500, M + bx * (1 - min(1, k)), 1516], fill=ORANGE)
                self.centro(d, 1560, 'Chuta nos comentários antes de ver!', self.F['med'], MUTED)
        else:
            r = mk[self.campo]
            e = eback(rev / 0.4)
            self.centro(d, 1210, f'{pct(r)} em 30 min', fonte('InterDisplay-Bold.otf', int(96 * (0.8 + 0.2 * e))), VERDE if r > 0 else VERMELHO)
            self.mini(d, mk, min(1.0, rev / 1.1), y0=1360, alt=280)
        return im

    def fim(self, t):
        im, d = self.fundo()
        a = ease(t / 0.35)
        self.centro(d, 480, 'Quantas você acertou?', self.Fq['m'], mix(WHITE, a))
        e = eback(t / 0.45)
        n = ' · '.join(str(i) for i in range(len(self.mks) + 1))
        self.centro(d, 600, n, fonte('InterDisplay-Bold.otf', int(140 * (0.8 + 0.2 * e))), mix(ORANGE, a))
        self.centro(d, 800, 'Comenta aqui', self.Fq['b'], mix(WHITE, ease((t - 0.3) / 0.3)))
        if t > 0.7:
            c = ease((t - 0.7) / 0.35)
            d.rectangle([M + 40, 1000, W - M - 40, 1140], fill=mix(TEAL_L, c))
            self.centro(d, 1036, 'Todo pregão: lectnex.com.br', fonte('InterDisplay-Bold.otf', 54), mix((12, 26, 42), c))
            dc = (88, 101, 242)
            d.rectangle([M + 40, 1170, W - M - 40, 1300], fill=mix(dc, c))
            self.centro(d, 1188, 'Desafio diário no Discord', fonte('InterDisplay-Bold.otf', 44), mix(WHITE, c, dc))
            self.centro(d, 1244, DISCORD, self.F['monos'], mix(WHITE, c, dc))
            self.centro(d, 1350, 'Seja fundador da Lectnex Pro · lectnex.com.br/pro', self.F['monos'], mix(ORANGE, c))
            self.centro(d, 1560, 'Variação de 30 min após a manchete · não prova causa', self.F['pq'], mix((100, 112, 130), c))
            self.centro(d, 1600, 'Cotações de 5 min (Yahoo Finance) · conteúdo educacional', self.F['pq'], mix((100, 112, 130), c))
        return im

    def quadro(self, t):
        if t < GANCHO:
            return self.gancho(t)
        t -= GANCHO
        i = int(t // RODADA)
        if i < len(self.mks):
            return self.rodada(i, t - i * RODADA)
        return self.fim(t - RODADA * len(self.mks))


def textos(q):
    legenda = '\n'.join([f'DESAFIO: {len(q.mks)} manchetes reais de hoje ({q.dia:%d/%m}). O {q.nome} subiu ou caiu nos 30 minutos seguintes? 🤔', '',
                         'Pause, chute e só depois veja a resposta. Comenta quantas você acertou 👇', '',
                         f'💬 Desafio todo dia na comunidade do Discord: {DISCORD}', '👑 Lista de fundadores da Lectnex Pro (grátis): lectnex.com.br/pro', 'Conteúdo educacional, não é recomendação. lectnex.com.br',
                         '#daytrade #miniindice #minidolar #ibovespa #trader #b3'])
    mk = next((x for x in q.mks if not DICA.search(x['titulo'])), q.mks[0])
    x = '\n\n'.join([f'Desafio de hoje 🎯 {mk["hora"]}: "{mk["titulo"][:120]}"',
                     f'O {q.nome} subiu ou caiu nos 30 min seguintes?', 'Responde antes de ver 👇 resposta no gráfico de hoje:',
                     'https://lectnex.com.br/hoje.html'])
    return legenda, x


def capa(q, saida):
    im, d = q.fundo()
    d.rectangle([0, 0, W, 10], fill=ORANGE)
    q.centro(d, 520, 'DESAFIO DO DIA', q.F['mono'], TEAL_L)
    q.centro(d, 640, 'SUBIU', fonte('InterDisplay-Bold.otf', 180), VERDE)
    q.centro(d, 840, 'ou', q.Fq['m'], MUTED)
    q.centro(d, 940, 'CAIU?', fonte('InterDisplay-Bold.otf', 180), VERMELHO)
    q.centro(d, 1200, f'{len(q.mks)} manchetes reais · {q.dia:%d/%m}', q.F['med'], WHITE)
    im.save(saida, 'PNG', optimize=True)


def main():
    opc = {sys.argv[i + 1] for i, a in enumerate(sys.argv[:-1]) if a in ('--capa', '--legenda', '--quadros', '--x')}
    args = [a for a in sys.argv[1:] if not a.startswith('--') and a not in opc]
    val = lambda k: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else None
    m = json.load(open(args[0], encoding='utf-8'))
    if not (m.get('ibov') or m.get('dolar')):
        print('Sem série do dia: desafio não gerado.'); return
    q = Quiz(m)
    if len(q.mks) < 2:
        print('Menos de 2 manchetes com reação: desafio não gerado.'); return
    if val('--quadros'):
        pasta = args[1] if len(args) > 1 else '.'
        for t in map(float, val('--quadros').split(',')):
            q.quadro(t).save(os.path.join(pasta, f'quiz_{t:05.2f}.png'))
        return
    saida = args[1] if len(args) > 1 else 'reel-quiz.mp4'
    legenda, x = textos(q)
    if val('--legenda'):
        open(val('--legenda'), 'w', encoding='utf-8').write(legenda)
    if val('--x'):
        open(val('--x'), 'w', encoding='utf-8').write(x)
    if val('--capa'):
        capa(q, val('--capa'))
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-crf', '21', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', saida],
                         stdin=subprocess.PIPE)
    for i in range(int(q.total * FPS)):
        p.stdin.write(q.quadro(i / FPS).tobytes())
    p.stdin.close()
    p.wait()
    try:  # pop a cada rodada, sinal em cada resposta
        from trilha import juntar, trilha
        pops = [GANCHO + i * RODADA for i in range(len(q.mks))]
        juntar(saida, trilha(q.total, pops=pops, sinal=GANCHO + CONTA1, final=q.total - FIM, saida=saida + '.wav'))
        os.remove(saida + '.wav')
    except Exception as e:
        print(f'::warning::Desafio sem áudio ({e})')
    print(f'Desafio SUBIU ou CAIU: {saida} ({os.path.getsize(saida) // 1024} KB, {q.total:.1f} s)')


if __name__ == '__main__':
    main()
