"""Servidor Discord da Lectnex: lê o estado atual (modo "ler") — nunca apaga nada.

Uso: DISCORD_BOT_TOKEN=... python3 scripts/discord_servidor.py ler
O log do GitHub Actions deste repositório é público: aqui só saem nomes de canais e cargos e contagens,
nunca nomes de membros nem conteúdo de mensagens.
"""
import json
import os
import sys
import urllib.error
import urllib.request

API = 'https://discord.com/api/v10'
GUILD = os.environ.get('DISCORD_GUILD_ID', '1565140434445934722')
TOKEN = os.environ.get('DISCORD_BOT_TOKEN', '').strip()
TIPOS = {0: 'texto', 2: 'voz', 4: 'categoria', 5: 'anúncios', 13: 'palco', 15: 'fórum', 16: 'mídia'}
PERMS = {0: 'criar convite', 1: 'expulsar', 2: 'banir', 3: 'ADMINISTRADOR', 4: 'gerenciar canais', 5: 'gerenciar servidor',
         10: 'ver canais', 11: 'enviar mensagens', 13: 'gerenciar mensagens', 17: 'mencionar @everyone', 28: 'gerenciar cargos',
         29: 'gerenciar webhooks', 40: 'silenciar membros'}


def api(metodo, caminho, corpo=None):
    req = urllib.request.Request(API + caminho, method=metodo, data=json.dumps(corpo).encode() if corpo is not None else None,
                                 headers={'Authorization': f'Bot {TOKEN}', 'User-Agent': 'DiscordBot (https://lectnex.com.br, 1.0)',
                                          'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r) if r.status != 204 else None
    except urllib.error.HTTPError as e:
        raise SystemExit(f'::error::Discord {metodo} {caminho}: HTTP {e.code} {e.read()[:300].decode(errors="replace")}')


def perms_txt(v):
    v = int(v)
    return ', '.join(n for b, n in PERMS.items() if v >> b & 1) or '—'


def ler():
    eu = api('GET', '/users/@me')
    g = api('GET', f'/guilds/{GUILD}?with_counts=true')
    canais = api('GET', f'/guilds/{GUILD}/channels')
    cargos = sorted(api('GET', f'/guilds/{GUILD}/roles'), key=lambda r: -r['position'])
    print(f'Bot: {eu["username"]} · Servidor: {g["name"]} · ~{g.get("approximate_member_count")} membros '
          f'({g.get("approximate_presence_count")} online)')
    print(f'Comunidade: {"sim" if "COMMUNITY" in g.get("features", []) else "NÃO"} · verificação nível {g.get("verification_level")} '
          f'· filtro de mídia {g.get("explicit_content_filter")} · canal de regras {g.get("rules_channel_id")} · avisos {g.get("public_updates_channel_id")}')
    print('\n## Cargos (do mais alto ao mais baixo)')
    for r in cargos:
        print(f'- {r["name"]}{" (bot)" if r.get("managed") else ""}: {perms_txt(r["permissions"])}')
    print('\n## Canais')
    cats = {c['id']: c for c in canais if c['type'] == 4}
    for cat in [None] + sorted(cats.values(), key=lambda c: c['position']):
        filhos = sorted([c for c in canais if c['type'] != 4 and c.get('parent_id') == (cat['id'] if cat else None)], key=lambda c: c['position'])
        if cat is None and not filhos:
            continue
        print(f'### {cat["name"] if cat else "(sem categoria)"}' + (f' · {len(cat.get("permission_overwrites", []))} regra(s) de permissão' if cat else ''))
        for c in filhos:
            print(f'- #{c["name"]} [{TIPOS.get(c["type"], c["type"])}]' + (f' · modo lento {c["rate_limit_per_user"]}s' if c.get('rate_limit_per_user') else '')
                  + (f' · {len(c.get("permission_overwrites", []))} regra(s) próprias' if c.get('permission_overwrites') else ''))
    try:
        regras = api('GET', f'/guilds/{GUILD}/auto-moderation/rules')
        print(f'\n## AutoMod: {len(regras)} regra(s)' + ''.join(f'\n- {r["name"]} ({"ligada" if r["enabled"] else "desligada"})' for r in regras))
    except SystemExit as e:
        print(f'\n## AutoMod: não consegui ler ({e})')


if __name__ == '__main__':
    if not TOKEN:
        sys.exit('::error::Falta o segredo DISCORD_BOT_TOKEN.')
    modo = sys.argv[1] if len(sys.argv) > 1 else 'ler'
    if modo == 'ler':
        ler()
    else:
        sys.exit(f'Modo desconhecido: {modo}')
