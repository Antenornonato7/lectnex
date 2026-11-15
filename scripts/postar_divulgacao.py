"""Post automático de cada divulgação nova, logo depois que a página dela entra no ar.

Lê $RUNNER_TEMP/novas-divulgacoes.json (escrito por scripts/divulgacao_paginas.py) e posta:
- no Discord, em #agenda-e-alertas (segredo DISCORD_BOT_TOKEN);
- no X, quando a conta estiver ligada (segredos X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET).
  Cada post com link custa ~US$ 0,20 na API paga do X; sem os segredos, não posta e não gasta nada.
Nunca derruba o workflow.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'coletor'))


def pct(v):
    return '—' if v is None else ('+' if v > 0 else '−' if v < 0 else '') + f'{abs(v):.2f}%'.replace('.', ',')


def texto(n, rede):
    sup = {'acima': ' ▲ acima do consenso', 'abaixo': ' ▼ abaixo do consenso'}.get(n.get('surpresa'), '')
    cons = f' (consenso {n["consenso"]})' if n.get('consenso') else ''
    gap = rede == 'discord' and n.get('win_abertura')
    reac = f'WIN {pct(n.get("win"))}{"*" if gap else ""} · dólar {pct(n.get("wdo"))} em {n["janela"]}' + (' (* inclui o gap da abertura)' if gap else '')
    if rede == 'discord':
        return '\n'.join([f'📊 **{n["evento"]} saiu {n.get("resultado") or "—"}**{cons}{sup}', reac,
                          f'[Gráfico, histórico e reação completa](<{n["url"]}>)', '*Educacional. Não é recomendação.*'])
    t = f'{n["evento"]} saiu {n.get("resultado") or "—"}{cons}.\n{reac}.\n\nGráfico e histórico: {n["url"]}'
    return t[:280]


def x_postar(t):
    chaves = [os.environ.get(k, '').strip() for k in ('X_API_KEY', 'X_API_SECRET', 'X_ACCESS_TOKEN', 'X_ACCESS_SECRET')]
    if not all(chaves):
        print('::notice::X: conta não ligada (faltam os segredos X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET).')
        return
    try:
        from requests_oauthlib import OAuth1Session
        s = OAuth1Session(chaves[0], client_secret=chaves[1], resource_owner_key=chaves[2], resource_owner_secret=chaves[3])
        r = s.post('https://api.x.com/2/tweets', json={'text': t}, timeout=30)
        print(f'::notice::X: postado ({r.status_code})' if r.status_code < 300 else f'::warning::X recusou ({r.status_code}): {r.text[:200]}')
    except Exception as e:
        print(f'::warning::X: {e}')


if __name__ == '__main__':
    arq = os.path.join(os.environ.get('RUNNER_TEMP', '.'), 'novas-divulgacoes.json')
    if not os.path.exists(arq):
        print('Nenhuma divulgação nova para postar.')
        raise SystemExit
    import discord_post as dc
    for n in json.load(open(arq, encoding='utf-8')):
        dc.postar('agenda-e-alertas', md=texto(n, 'discord'))
        x_postar(texto(n, 'x'))
