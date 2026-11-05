"""Trilha original dos reels (sintetizada aqui, sem direito autoral de terceiros): batida leve a 100 BPM, acorde de fundo,
"pop" quando cada manchete aparece, sinal no resultado e um sobe-som curto na chamada final.
trilha(segundos, pops=[t...], sinal=t, final=t, saida='trilha.wav')  ·  juntar(video, wav) põe o áudio no MP4 (AAC).
"""
import os
import subprocess
import wave

import numpy as np

SR = 44100


def _env(n, ataque=0.005, queda=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(ataque, 1e-4)) * np.exp(-t / queda)


def _por(buf, t, som, ganho=1.0):
    i = int(t * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(som))
    buf[i:j] += som[: j - i] * ganho


def trilha(seg, pops=(), sinal=None, final=None, saida='trilha.wav', bpm=100, semente=7):
    n = int(seg * SR)
    buf = np.zeros(n)
    rng = np.random.default_rng(semente)
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
