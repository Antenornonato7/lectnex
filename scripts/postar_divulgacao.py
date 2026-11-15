"""Post automático de cada divulgação nova, logo depois que a página dela entra no ar.

Lê $RUNNER_TEMP/novas-divulgacoes.json (escrito por scripts/divulgacao_paginas.py) e posta:
- no Discord, em #agenda-e-alertas (segredo DISCORD_BOT_TOKEN);
- texto pronto para o X no Telegram PRIVADO do dono, para ele postar à mão (sem pagar a API do X).
  Se um dia os segredos X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN e X_ACCESS_SECRET existirem, posta direto no X.
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


def telegram_para_x(t):
    """Manda o post pronto no Telegram privado: é só copiar e colar no X."""
    import html
    tok, chat = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip(), os.environ.get('TELEGRAM_ADMIN_CHAT_ID', '').strip()
    if not tok or not chat or chat.startswith('@'):
        print('::warning::Telegram privado não configurado: post do X não enviado.')
        return
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from kit import tg_texto
        tg_texto(f'𝕏 <b>Post pronto para o X</b> (toque no texto para copiar)\n\n<code>{html.escape(t)}</code>')
        print('::notice::Post do X enviado ao Telegram privado.')
    except Exception as e:
        print(f'::warning::Telegram: {e}')


def x_postar(t):
    chaves = [os.environ.get(k, '').strip() for k in ('X_API_KEY', 'X_API_SECRET', 'X_ACCESS_TOKEN', 'X_ACCESS_SECRET')]
    if not all(chaves):
        telegram_para_x(t)
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
