"""Posta no servidor Discord da Lectnex (canais pelo nome), com o mesmo bot do montador (segredo DISCORD_BOT_TOKEN).

Nunca derruba quem chama: sem token, ou se o Discord recusar, só avisa no log.
Uso no código:  import discord_post as dc; dc.postar('fechamento', html=texto_do_telegram)
Uso no terminal: python3 coletor/discord_post.py <canal> <arquivo de texto ou -> [imagem.png]
"""
import html as _html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import uuid

API = 'https://discord.com/api/v10'
GUILD = os.environ.get('DISCORD_GUILD_ID', '1565140434445934722')
TOKEN = os.environ.get('DISCORD_BOT_TOKEN', '').strip()
_canais = None


def _req(metodo, caminho, corpo=None, arquivo=None):
    cab = {'Authorization': f'Bot {TOKEN}', 'User-Agent': 'DiscordBot (https://lectnex.com.br, 1.0)'}
    if arquivo:  # multipart: payload_json + files[0]
        b = uuid.uuid4().hex
        nome = os.path.basename(arquivo)
        dados = (f'--{b}\r\nContent-Disposition: form-data; name="payload_json"\r\nContent-Type: application/json\r\n\r\n'
                 f'{json.dumps({**corpo, "attachments": [{"id": 0, "filename": nome}]})}\r\n'
                 f'--{b}\r\nContent-Disposition: form-data; name="files[0]"; filename="{nome}"\r\nContent-Type: image/png\r\n\r\n').encode()
        dados += open(arquivo, 'rb').read() + f'\r\n--{b}--\r\n'.encode()
        cab['Content-Type'] = f'multipart/form-data; boundary={b}'
    else:
        dados = json.dumps(corpo).encode() if corpo is not None else None
        cab['Content-Type'] = 'application/json'
    req = urllib.request.Request(API + caminho, data=dados, method=metodo, headers=cab)
    for tentativa in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r) if r.status != 204 else None
        except urllib.error.HTTPError as e:
            if e.code == 429 and tentativa < 2:
                time.sleep(float(json.loads(e.read() or b'{}').get('retry_after', 2)) + 0.5)
                continue
            raise RuntimeError(f'HTTP {e.code} {e.read()[:200].decode(errors="replace")}')


def canal(nome):
    global _canais
    if _canais is None:
        _canais = {c['name']: c['id'] for c in _req('GET', f'/guilds/{GUILD}/channels')}
    return _canais.get(nome)


def html_para_md(t):
    """Texto no formato do Telegram (HTML simples) → markdown do Discord."""
    t = re.sub(r'<a href="([^"]+)">(.*?)</a>', lambda m: f'[{m.group(2)}](\x00{m.group(1)}\x01)', t, flags=re.S)
    t = re.sub(r'</?b>', '**', t)
    t = re.sub(r'</?i>', '*', t)
    t = re.sub(r'<[^>]+>', '', t)  # outras tags somem (o link já virou marcador)
    return _html.unescape(t).replace('\x00', '<').replace('\x01', '>')


def postar(nome, html=None, md=None, imagem_url=None, arquivo=None):
    if not TOKEN:
        print('::notice::Discord: sem DISCORD_BOT_TOKEN, não postado.')
        return False
    try:
        cid = canal(nome)
        if not cid:
            print(f'::warning::Discord: canal #{nome} não existe.')
            return False
        texto = md if md is not None else html_para_md(html or '')
        if len(texto) > 1990:
            texto = texto[:1980].rsplit('\n', 1)[0] + '\n…'
        corpo = {'content': texto, 'allowed_mentions': {'parse': []}}
        if imagem_url:
            corpo['embeds'] = [{'image': {'url': imagem_url}, 'color': 0x009988}]
        else:
            corpo['flags'] = 4  # sem prévia automática dos links
        m = _req('POST', f'/channels/{cid}/messages', corpo, arquivo if arquivo and os.path.exists(arquivo) else None)
        # em canal de anúncios, publica para quem segue de outro servidor
        print(f'::notice::Discord: postado em #{nome} ({m["id"]})')
        return True
    except Exception as e:
        print(f'::warning::Discord: falha ao postar em #{nome}: {e}')
        return False


def msg_agenda(cal, data_iso, flag=None):
    """Agenda do dia (importância >= 2), no mesmo tom do site."""
    flag = flag or {}
    evs = [e for e in (cal or {}).get('eventos', []) if e.get('data') == data_iso and (e.get('importancia') or 1) >= 2]
    if not evs:
        return None
    evs.sort(key=lambda e: (e.get('hora') is None, e.get('hora') or ''))
    dd = '/'.join(reversed(data_iso.split('-')[1:]))
    linhas = [f'📅 **Agenda de hoje · {dd}**']
    for e in evs[:10]:
        imp = ' ⚠️' if (e.get('importancia') or 1) >= 3 else ''
        cons = f' · consenso {e["consenso"]}' if e.get('consenso') else ''
        linhas.append(f'`{e.get("hora") or "dia"}` {flag.get(e.get("pais"), "")} {e["evento"]}{cons}{imp}')
    linhas += ['', '⚠️ = alto impacto · [Calendário completo](<https://lectnex.com.br/#cal-wrap>)', '*Educacional. Não é recomendação.*']
    return '\n'.join(linhas)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit('Uso: discord_post.py <canal> <arquivo de texto ou -> [imagem]')
    txt = sys.stdin.read() if sys.argv[2] == '-' else (open(sys.argv[2], encoding='utf-8').read() if os.path.exists(sys.argv[2]) else sys.argv[2])
    postar(sys.argv[1], md=txt, arquivo=sys.argv[3] if len(sys.argv) > 3 else None)
