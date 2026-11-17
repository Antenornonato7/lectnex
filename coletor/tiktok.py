"""TikTok: publica os Reels do dia na conta da Lectnex (Content Posting API, Direct Post).

Segredos: TIKTOK_CLIENT_KEY e TIKTOK_CLIENT_SECRET (app "Lectnex Publicador" no TikTok for Developers).
Fluxo de conexão (uma vez): python3 coletor/tiktok.py link  → manda no Telegram o link de autorização;
  o TikTok volta para lectnex.com.br/tiktok-callback.html com o código; o dono roda o workflow "TikTok" com acao=conectar e o código.
Os tokens (acesso 24 h, renovação 365 dias) ficam no branch ao-vivo em tiktok/token.bin, cifrados com AES-GCM
(chave = SHA-256 do client secret): quem lê o repositório não consegue usar.
Enquanto o app não passar pela auditoria do TikTok, os posts saem como "só eu" (SELF_ONLY).
"""
import base64
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
import instagram as ig  # noqa: E402  (GitHub do branch ao-vivo, Telegram do dono, note)

API = 'https://open.tiktokapis.com/v2'
REDIRECT = 'https://lectnex.com.br/tiktok-callback.html'
ESCOPOS = 'user.info.basic,video.publish,video.upload'
ARQ = 'tiktok/token.bin'


def chave():
    return hashlib.sha256(os.environ['TIKTOK_CLIENT_SECRET'].strip().encode()).digest()


def ler_token():
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    try:
        j = ig.gh('GET', f'{ig.GH}/contents/{ARQ}?ref=ao-vivo')
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None, None
        raise
    bruto = base64.b64decode(j['content'])
    return json.loads(AESGCM(chave()).decrypt(bruto[:12], bruto[12:], None)), j['sha']


def gravar_token(tok, sha):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    nonce = os.urandom(12)
    ig.gh_gravar(ARQ, nonce + AESGCM(chave()).encrypt(nonce, json.dumps(tok).encode(), None), sha, 'tiktok: token')


def oauth(params):
    dados = urllib.parse.urlencode({'client_key': os.environ['TIKTOK_CLIENT_KEY'].strip(),
                                    'client_secret': os.environ['TIKTOK_CLIENT_SECRET'].strip(), **params}).encode()
    req = urllib.request.Request(f'{API}/oauth/token/', data=dados, headers={'Content-Type': 'application/x-www-form-urlencoded'})
    try:
        j = json.loads(urllib.request.urlopen(req, timeout=60).read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'TikTok OAuth HTTP {e.code}: {e.read().decode()[:200]}') from None
    if j.get('error'):
        raise RuntimeError(f'TikTok OAuth: {j.get("error")}: {j.get("error_description")}')
    j['obtido'] = int(time.time())
    return j


def acesso():
    tok, sha = ler_token()
    if not tok:
        raise RuntimeError('TikTok não conectado (rode o workflow TikTok com acao=link e depois conectar)')
    if time.time() > tok['obtido'] + tok.get('expires_in', 86400) - 600:
        tok = oauth({'grant_type': 'refresh_token', 'refresh_token': tok['refresh_token']})
        gravar_token(tok, sha)
    return tok['access_token']


def api(caminho, token, corpo=None):
    req = urllib.request.Request(f'{API}/{caminho}', data=json.dumps(corpo or {}).encode(), method='POST',
                                 headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json; charset=UTF-8'})
    try:
        j = json.loads(urllib.request.urlopen(req, timeout=60).read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'TikTok HTTP {e.code}: {e.read().decode()[:250]}') from None
    if (j.get('error') or {}).get('code') not in (None, 'ok'):
        raise RuntimeError(f'TikTok: {j["error"].get("code")}: {j["error"].get("message")}')
    return j.get('data') or {}


def publicar(video_url, legenda, privacidade=None):
    """Direct Post por upload do arquivo. Devolve (publish_id, privacidade usada).
    App ainda não auditado: o TikTok só aceita SELF_ONLY; se recusar o público, tenta de novo como privado."""
    tok = acesso()
    info = api('post/publish/creator_info/query/', tok)
    opcoes = info.get('privacy_level_options') or ['SELF_ONLY']
    privacidade = privacidade or ('PUBLIC_TO_EVERYONE' if 'PUBLIC_TO_EVERYONE' in opcoes else opcoes[0])
    video = urllib.request.urlopen(video_url, timeout=120).read()
    n = len(video)
    corpo = lambda priv: {
        'post_info': {'title': legenda[:2200], 'privacy_level': priv, 'disable_duet': False, 'disable_comment': False,
                      'disable_stitch': False, 'brand_content_toggle': False, 'brand_organic_toggle': False},
        'source_info': {'source': 'FILE_UPLOAD', 'video_size': n, 'chunk_size': n, 'total_chunk_count': 1}}
    try:
        d = api('post/publish/video/init/', tok, corpo(privacidade))
    except RuntimeError as e:
        if privacidade == 'SELF_ONLY' or 'unaudited' not in str(e).lower():
            raise
        privacidade = 'SELF_ONLY'
        d = api('post/publish/video/init/', tok, corpo(privacidade))
    req = urllib.request.Request(d['upload_url'], data=video, method='PUT',
                                 headers={'Content-Type': 'video/mp4', 'Content-Length': str(n), 'Content-Range': f'bytes 0-{n - 1}/{n}'})
    try:
        urllib.request.urlopen(req, timeout=300).read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'TikTok upload HTTP {e.code}: {e.read().decode()[:200]}') from None
    return d.get('publish_id'), privacidade


def link():
    estado = hashlib.sha256(os.urandom(16)).hexdigest()[:16]
    url = 'https://www.tiktok.com/v2/auth/authorize/?' + urllib.parse.urlencode({
        'client_key': os.environ['TIKTOK_CLIENT_KEY'].strip(), 'scope': ESCOPOS, 'response_type': 'code',
        'redirect_uri': REDIRECT, 'state': estado})
    ig.tg('sendMessage', chat_id=ig.admin(), disable_web_page_preview=True, parse_mode='HTML',
          text='🎵 <b>Conectar o TikTok da Lectnex</b>\n\n1. Abra o link abaixo <b>logado na conta TikTok da Lectnex</b> e autorize.\n'
               '2. A página do site mostra um código: siga as instruções dela (Actions → TikTok → conectar).\n\n' + url)
    ig.note('notice', 'Link de autorização do TikTok enviado no Telegram.')


def conectar(code):
    tok = oauth({'grant_type': 'authorization_code', 'code': code.strip(), 'redirect_uri': REDIRECT})
    _, sha = ler_token()
    gravar_token(tok, sha)
    ig.note('notice', f'TikTok conectado (escopos: {tok.get("scope")}).')
    try:
        ig.tg('sendMessage', chat_id=ig.admin(), text='✅ TikTok conectado. Os Reels aprovados passam a sair também no TikTok.')
    except Exception:
        pass


def teste():
    tok = acesso()
    info = api('post/publish/creator_info/query/', tok)
    ig.note('notice', f'TikTok: @{info.get("creator_username")} · privacidade permitida: {info.get("privacy_level_options")}')


def teste_post():
    """Publica o Reels do dia (Kit) como "só eu", para conferir a publicação sem aparecer para o público."""
    import datetime as dt
    dia = os.environ.get('KIT_DIA') or dt.datetime.now(ig.BRT).date().isoformat()
    kit, _ = ig.gh_ler(f'kit/{dia}/kit.json')
    rl = ((kit or {}).get('reels') or {}).get('reel')
    if not rl:
        raise RuntimeError(f'Sem Reels no kit de {dia}')
    pid, priv = publicar(ig.RAW + f'kit/{dia}/reel.mp4', rl.get('legenda', ''), 'SELF_ONLY')
    ig.note('notice', f'TikTok: Reels de {dia} enviado como {priv} (publish_id {pid}). Confira no app do TikTok, aba de vídeos privados.')
    try:
        ig.tg('sendMessage', chat_id=ig.admin(), text=f'🎵 Teste do TikTok: o Reels de hoje foi enviado para a conta @lectnex como PRIVADO (só você vê). Confira no app do TikTok.')
    except Exception:
        pass


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'teste'
    if cmd == 'link':
        link()
    elif cmd == 'teste-post':
        teste_post()
    elif cmd == 'conectar':
        conectar(os.environ.get('TIKTOK_CODE') or sys.argv[2])
    else:
        teste()
