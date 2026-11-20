"""Trilha original dos reels (sintetizada aqui, sem direito autoral de terceiros), com "pop" quando cada manchete aparece,
sinal no resultado e um sobe-som curto na chamada final.
trilha(segundos, pops=[t...], sinal=t, final=t, saida='trilha.wav', estilo=None)  ·  juntar(video, wav) põe o áudio no MP4 (AAC).

Estilos: 'lofi' (82 BPM, acordes de sétima, chiado de vinil), 'tensao' (pulso de mercado, 120 BPM, para dias de movimento forte:
estilo_do_dia escolhe sozinho) e 'batida' (a trilha original, 100 BPM).
O estilo muda de tempos em tempos (combinado em 19/11/2026: o áudio troca junto com os formatos, todo mês). Para trocar:
acrescente o mês em ESTILO_DO_MES. TRILHA_ESTILO no ambiente força um estilo (teste).
"""
import os
import subprocess
import wave

import numpy as np

SR = 44100
ESTILO_DO_MES = {'2026-11': 'lofi', '2026-12': 'lofi'}
PADRAO = 'lofi'
nota = lambda m: 440 * 2 ** ((m - 69) / 12)


def _env(n, ataque=0.005, queda=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(ataque, 1e-4)) * np.exp(-t / queda)


def _por(buf, t, som, ganho=1.0):
    i = int(t * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(som))
    buf[i:j] += som[: j - i] * ganho


def estilo_atual():
    import datetime as dt
    return os.environ.get('TRILHA_ESTILO', '').strip() or ESTILO_DO_MES.get(dt.date.today().strftime('%Y-%m'), PADRAO)


def _lp(x, a):
    """Passa-baixa de 1 polo (só para trechos curtos)."""
    y, acc = np.zeros_like(x), 0.0
    aa = np.broadcast_to(np.asarray(a, dtype=float), x.shape)
    for i in range(len(x)):
        acc += aa[i] * (x[i] - acc)
        y[i] = acc
    return y


def _lofi(seg, pops, sinal, final, rng, semente):
    n = int(seg * SR)
    b = np.zeros(n)
    bt = 60 / 82
    progs = [[[57, 60, 64, 67], [53, 57, 60, 64], [55, 59, 62, 65], [52, 55, 59, 62]],   # Am7 Fmaj7 G7 Em7
             [[50, 53, 57, 60], [55, 59, 62, 65], [48, 52, 55, 59], [57, 60, 64, 67]]]   # Dm7 G7 Cmaj7 Am7
    acordes = progs[semente % len(progs)]
    cn = int(bt * 4 * SR)
    tt = np.arange(cn) / SR
    for k in range(int(seg / (bt * 4)) + 1):
        s = np.zeros(cn)
        for m in acordes[k % 4]:
            f = nota(m)
            s += (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt)) * (1 + 0.15 * np.sin(2 * np.pi * 4 * tt))
        _por(b, k * bt * 4, s * _env(cn, 0.02, 2.5), 0.08)
    kn = int(0.3 * SR)
    kt = np.arange(kn) / SR
    kick = np.sin(2 * np.pi * (45 + 60 * np.exp(-kt * 25)) * kt) * _env(kn, 0.002, 0.15)
    sn = int(0.2 * SR)
    snare = _lp(rng.standard_normal(sn), 0.3) * _env(sn, 0.002, 0.07)
    for i in range(int(seg / bt) + 1):
        if i * bt >= 0.3:
            _por(b, i * bt + (0.02 if i % 2 else 0), kick if i % 2 == 0 else snare, 0.5 if i % 2 == 0 else 0.25)
    b += rng.standard_normal(n) * 0.18 * (rng.random(n) > 0.9993)   # chiado de vinil
    pn = int(0.15 * SR)
    pt = np.arange(pn) / SR
    for p in pops:
        _por(b, p, np.sin(2 * np.pi * nota(81) * pt) * _env(pn, 0.001, 0.05), 0.18)
    if sinal is not None:
        sn2 = int(0.8 * SR)
        st = np.arange(sn2) / SR
        _por(b, sinal, (np.sin(2 * np.pi * nota(76) * st) + np.sin(2 * np.pi * nota(83) * st)) * _env(sn2, 0.005, 0.4), 0.2)
    if final is not None:
        fn = int(1.4 * SR)
        ft = np.arange(fn) / SR
        _por(b, final, sum(np.sin(2 * np.pi * nota(m) * ft) for m in (69, 72, 76, 79)) * _env(fn, 0.01, 0.7), 0.07)
    return b


def _tensao(seg, pops, sinal, final, rng):
    """Pulso de mercado: baixo em colcheias a 120 BPM, bumbo seco e sobe-som antes do resultado (dias de movimento forte)."""
    n = int(seg * SR)
    b = np.zeros(n)
    bt = 60 / 120 / 2
    bn = int(bt * SR)
    tt = np.arange(bn) / SR
    for i in range(int(seg / bt) + 1):
        f = nota([40, 40, 40, 43][(i // 8) % 4])
        _por(b, i * bt, _lp(2 * ((f * tt) % 1) - 1, 0.08) * _env(bn, 0.003, 0.12), 0.35)
    kn = int(0.4 * SR)
    kt = np.arange(kn) / SR
    kick = np.sin(2 * np.pi * (40 + 80 * np.exp(-kt * 30)) * kt) * _env(kn, 0.001, 0.2)
    for i in range(int(seg / (bt * 2)) + 1):
        _por(b, i * bt * 2, kick, 0.6)
    t = np.arange(n) / SR
    b += sum(np.sin(2 * np.pi * nota(m) * t) for m in (52, 55, 59)) * 0.03 * (0.6 + 0.4 * np.sin(2 * np.pi * 0.2 * t))
    hn = int(0.08 * SR)
    for p in pops:
        _por(b, p, rng.standard_normal(hn) * _env(hn, 0.001, 0.02), 0.25)
    if sinal is not None:
        rn = int(1.2 * SR)
        rt = np.arange(rn) / SR
        _por(b, max(0, sinal - 1.2), _lp(rng.standard_normal(rn), 0.05 + 0.4 * rt / 1.2) * (rt / 1.2) ** 2, 0.6)
        hn2 = int(1.5 * SR)
        ht = np.arange(hn2) / SR
        _por(b, sinal, (np.sin(2 * np.pi * (35 + 40 * np.exp(-ht * 8)) * ht) + _lp(rng.standard_normal(hn2), 0.1)) * _env(hn2, 0.001, 0.5), 0.8)
    if final is not None:
        fn = int(1.2 * SR)
        ft = np.arange(fn) / SR
        _por(b, final, sum(np.sin(2 * np.pi * nota(m) * ft) for m in (64, 67, 71, 76)) * _env(fn, 0.01, 0.6), 0.15)
    return b


def estilo_do_dia(ativo, variacao):
    """Áudio com a cara do dia: dia de movimento forte (dólar ≥ 1% ou Ibovespa ≥ 1,5%) ganha o pulso de mercado; o resto, o estilo do mês."""
    if os.environ.get('TRILHA_ESTILO', '').strip():
        return estilo_atual()
    forte = variacao is not None and abs(variacao) >= (1.0 if ativo == 'dolar' else 1.5)
    return 'tensao' if forte else estilo_atual()


def trilha(seg, pops=(), sinal=None, final=None, saida='trilha.wav', bpm=100, semente=7, estilo=None):
    estilo = estilo or estilo_atual()
    n = int(seg * SR)
    rng = np.random.default_rng(semente)
    if estilo == 'lofi':
        return _salvar(_lofi(seg, pops, sinal, final, rng, semente), saida)
    if estilo == 'tensao':
        return _salvar(_tensao(seg, pops, sinal, final, rng), saida)
    buf = np.zeros(n)
    t = np.arange(n) / SR
    beat = 60 / bpm
    # bumbo (seno grave com queda de altura) em cada tempo; chimbal (ruído filtrado) no contratempo
    kn = int(0.35 * SR)
    kt = np.arange(kn) / SR
    bumbo = np.sin(2 * np.pi * (48 + 70 * np.exp(-kt * 30)) * kt) * _env(kn, 0.002, 0.12)
    hn = int(0.06 * SR)
    ruido = rng.standard_normal(hn)
    chimbal = np.diff(np.concatenate([[0], ruido])) * _env(hn, 0.001, 0.015)
    k = 0
    while k * beat < seg:
        if k * beat >= 0.4:
            _por(buf, k * beat, bumbo, 0.45)
            _por(buf, k * beat + beat / 2, chimbal, 0.12)
        k += 1
    # acorde de fundo (lá menor → fá → dó → sol), um a cada 2 compassos, entrando e saindo devagar
    acordes = [(220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (130.81, 196.0, 261.63), (196.0, 246.94, 293.66)]
    dur = beat * 8
    pad = np.zeros(n)
    for i in range(int(seg / dur) + 1):
        a, b = int(i * dur * SR), min(n, int((i + 1) * dur * SR))
        if a >= n:
            break
        tt = t[a:b] - t[a]
        f = acordes[i % len(acordes)]
        onda = sum(np.sin(2 * np.pi * x * tt) + 0.3 * np.sin(4 * np.pi * x * tt) for x in f) / 3
        pad[a:b] += onda * np.minimum(1, tt / 0.8) * np.minimum(1, (tt[-1] - tt + 1e-3) / 0.8)
    pad *= 0.16 * (0.85 + 0.15 * np.sin(2 * np.pi * t / (beat * 2)))
    buf += pad
    # pop: varredura curta para cima
    pn = int(0.12 * SR)
    pt = np.arange(pn) / SR
    pop = np.sin(2 * np.pi * (520 * pt + 4200 * pt ** 2)) * _env(pn, 0.002, 0.05)
    for p in pops:
        _por(buf, p, pop, 0.9)
    if sinal is not None:  # sinal do resultado: dó + sol, curto e brilhante
        sn = int(1.2 * SR)
        st = np.arange(sn) / SR
        som = (np.sin(2 * np.pi * 523.25 * st) + 0.6 * np.sin(2 * np.pi * 783.99 * st) + 0.25 * np.sin(2 * np.pi * 1046.5 * st)) * _env(sn, 0.004, 0.45)
        _por(buf, sinal, som, 0.32)
    if final is not None:  # sobe-som de ruído suave antes da chamada
        rn = int(0.9 * SR)
        sobe = np.convolve(rng.standard_normal(rn), np.ones(40) / 40, 'same') * np.linspace(0, 1, rn) ** 2
        _por(buf, max(0, final - 0.9), sobe, 0.5)
    return _salvar(buf, saida)


def _salvar(buf, saida):
    # entrada e saída suaves, normalização com folga
    fade = int(0.6 * SR)
    buf[:fade] *= np.linspace(0, 1, fade)
    buf[-fade:] *= np.linspace(1, 0, fade)
    buf = buf / (np.max(np.abs(buf)) or 1) * 0.6
    with wave.open(saida, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((buf * 32767).astype('<i2').tobytes())
    return saida


def juntar(video, wav):
    """Põe o áudio no vídeo (substitui o arquivo). Se falhar, o vídeo fica sem som, como antes."""
    tmp = video + '.som.mp4'
    r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', video, '-i', wav, '-c:v', 'copy', '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', '44100', '-c:a', 'aac', '-b:a', '160k',
                        '-shortest', '-movflags', '+faststart', tmp])
    if r.returncode == 0:
        os.replace(tmp, video)
        return True
    return False
