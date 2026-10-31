"""Conta os inscritos confirmados da newsletter (Buttondown) e grava data/newsletter.json.

O site só mostra "Junte-se a N traders" quando N >= 25 (prova social sem número constrangedor).
Precisa de chave com permissão de leitura de inscritos; sem ela, avisa e não altera nada.
"""
import json, os, sys, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta

KEY = os.environ.get('BUTTONDOWN_API_KEY', '').strip()
SAIDA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'newsletter.json')


def main():
    if not KEY:
        print('::warning title=Inscritos::Sem chave do Buttondown.'); return
    req = urllib.request.Request('https://api.buttondown.com/v1/subscribers?type=regular', headers={
        'Authorization': f'Token {KEY}', 'X-API-Version': '2026-04-01'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            j = json.load(r)
    except urllib.error.HTTPError as e:
        print(f'::warning title=Inscritos ({e.code})::{e.read().decode()[:300]} — dê à chave permissão de leitura de inscritos.'); return
    n = j.get('count')
    if n is None:
        print('::warning title=Inscritos::Resposta sem contagem.'); return
    json.dump({'inscritos': int(n), 'atualizado_em': datetime.now(timezone(timedelta(hours=-3))).isoformat(timespec='minutes')},
              open(SAIDA, 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'::notice title=Inscritos::{n} inscritos confirmados')


if __name__ == '__main__':
    main()
