"""Gera e manda agora, no Telegram privado do dono, o reel do dia (ou da semana) com capa e legenda.
Usa os pregões gravados em data/dias/. Uso: python3 scripts/reel_enviar.py [dia|semana] [AAAA-MM-DD]
"""
import datetime as dt
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from kit import tg_album, tg_texto, tg_video  # noqa: E402

BRT = dt.timezone(dt.timedelta(hours=-3))
tipo = sys.argv[1] if len(sys.argv) > 1 else 'dia'
dia = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else dt.datetime.now(BRT).date().isoformat()
tmp = os.environ.get('RUNNER_TEMP', '.')
mp4, capa, leg = (os.path.join(tmp, f'reel-{tipo}.{x}') for x in ('mp4', 'png', 'txt'))
if tipo == 'semana':
    cmd = ['python3', 'scripts/reel_semana.py', mp4, '--data', dia, '--forcar', '--capa', capa, '--legenda', leg]
    nome = 'Reel da semana'
else:
    arq = f'data/dias/{dia}.json'
    if not os.path.exists(arq):
        tg_texto(f'⚠️ Não encontrei o pregão de {dia} no arquivo: o reel não foi gerado.', html=False)
        sys.exit(f'::error::Sem {arq}')
    cmd = ['python3', 'scripts/reel_dia.py', arq, mp4, '--capa', capa, '--legenda', leg]
    nome = 'Reel do dia'
subprocess.run(cmd, check=True)
if not os.path.exists(mp4):
    tg_texto(f'⚠️ {nome} de {dia}: não houve dados suficientes para gerar o vídeo.', html=False)
    sys.exit(0)
d = dt.date.fromisoformat(dia)
tg_video(open(mp4, 'rb').read(), f'🎬 <b>{nome}</b> · {d:%d/%m} · legenda e capa logo abaixo')
if os.path.exists(capa):
    from PIL import Image
    import io
    buf = io.BytesIO()
    Image.open(capa).convert('RGB').save(buf, 'JPEG', quality=90)
    tg_album([buf.getvalue()], f'🖼️ <b>Capa: {nome}</b>. No Instagram, em "Editar capa", toque em "Adicionar da galeria" e escolha esta imagem.')
if os.path.exists(leg):
    tg_texto(f'📋 Legenda ({nome}):', html=False)
    tg_texto(open(leg, encoding='utf-8').read(), html=False)
print(f'{nome} de {dia} enviado.')
