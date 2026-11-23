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
    # o conteúdo da API de "contents" chega recodificado para arquivo binário; a de blobs devolve os bytes exatos
    bruto = base64.b64decode(ig.gh('GET', f'{ig.GH}/git/blobs/{j["sha"]}')['content'])
    try:
        return json.loads(AESGCM(chave()).decrypt(bruto[:12], bruto[12:], None)), j['sha']
    except Exception as e:   # InvalidTag: o arquivo foi cifrado com outro TIKTOK_CLIENT_SECRET
        ig.note('warning', f'TikTok: token não abriu ({e.__class__.__name__}: {str(e)[:120]}; {len(bruto)} bytes)')
        return {'_invalido': True}, j['sha']


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
    if tok.get('_invalido'):
        raise RuntimeError('o token salvo do TikTok não abre com o segredo atual (o TIKTOK_CLIENT_SECRET mudou?). Reconecte: workflow TikTok → link, depois conectar')
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


def rascunho(video_url):
    """Envia o vídeo como RASCUNHO para a caixa de entrada do TikTok (Upload, sem Direct Post): o dono recebe a notificação no app
    e publica de lá, escolhendo música e privacidade. Devolve o publish_id."""
    tok = acesso()
    video = urllib.request.urlopen(video_url, timeout=120).read()
    n = len(video)
    d = api('post/publish/inbox/video/init/', tok, {'source_info': {'source': 'FILE_UPLOAD', 'video_size': n, 'chunk_size': n, 'total_chunk_count': 1}})
    req = urllib.request.Request(d['upload_url'], data=video, method='PUT',
                                 headers={'Content-Type': 'video/mp4', 'Content-Length': str(n), 'Content-Range': f'bytes 0-{n - 1}/{n}'})
    try:
        urllib.request.urlopen(req, timeout=300).read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'TikTok upload HTTP {e.code}: {e.read().decode()[:200]}') from None
    return d.get('publish_id')


def legenda_tiktok(leg):
    """Legenda do TikTok a partir da do Instagram: gancho em 1 linha, a pergunta (puxa comentário), chamada para seguir e
    4-5 hashtags do nicho (no TikTok, poucas e específicas rendem mais que muitas)."""
    import re
    linhas = [l.strip() for l in (leg or '').splitlines() if l.strip() and not l.strip().startswith('#')]
    m = re.match(r'O que mexeu no (.+?) hoje \(([^)]+)\)', linhas[0]) if linhas else None
    if m:
        ativo, var = m.groups()
        cai = var.startswith(('−', '-'))
        gancho = f'{ativo[:1].upper() + ativo[1:]} {var} hoje {"📉" if cai else "📈"} Veja a notícia que mais {"derrubou" if cai else "puxou"} o preço 👀'
    else:
        gancho = (linhas[0] if linhas else 'O que mexeu no mercado hoje 👀')[:120]
    pergunta = next((l[:l.rindex('?') + 1] for l in linhas[1:] if '?' in l and not re.match(r'\d+\.\s', l)),
                    'Você teria visto essa notícia a tempo? Conta aqui 👇')
    dolar = 'dólar' in (leg or '').lower() and 'ibovespa' not in gancho.lower()
    tags = '#daytrade #minidolar #dolar #bolsadevalores #trader' if dolar else '#daytrade #miniindice #ibovespa #bolsadevalores #trader'
    return '\n'.join([gancho, '', pergunta, '', 'Siga para ver o resumo de todo pregão em 15s. Conteúdo educacional.', tags])


def enviar_legenda(leg, reply_to=None):
    """Manda a legenda do TikTok sozinha numa mensagem (toque longo → copiar) e a dica de som."""
    txt = legenda_tiktok(leg)
    kw = {'reply_to_message_id': reply_to} if reply_to else {}
    ig.tg('sendMessage', chat_id=ig.admin(), text='🎵 Legenda para o TikTok (copie a próxima mensagem). Dica: no app, toque em "Adicionar som" e escolha um da aba "Em alta" com volume baixo.', **kw)
    ig.tg('sendMessage', chat_id=ig.admin(), text=txt)
    return txt


def legenda_do_dia(dia):
    """Manda no Telegram a legenda do TikTok do kit do dia (sem subir vídeo)."""
    try:
        import json
        kit = json.loads(urllib.request.urlopen(ig.RAW + f'kit/{dia}/kit.json', timeout=30).read())
        pecas = {x['chave']: x.get('legenda', '') for x in kit.get('pecas', [])}
        leg = (kit.get('reels') or {}).get('reel', {}).get('legenda') or pecas.get('grafico', '')
        ig.note('notice', 'Legenda TikTok: ' + legenda_tiktok(leg).replace(chr(10), ' | '))
        enviar_legenda(leg)
    except Exception as e:
        ig.note('notice', f'Sem legenda do kit: {e}')


def teste_rascunho():
    import datetime as dt
    dia = os.environ.get('KIT_DIA') or dt.datetime.now(ig.BRT).date().isoformat()
    pid = rascunho(ig.RAW + f'kit/{dia}/reel.mp4')
    ig.note('notice', f'TikTok: Reels de {dia} enviado como rascunho (publish_id {pid}).')
    legenda_do_dia(dia)
    try:
        ig.tg('sendMessage', chat_id=ig.admin(), text='🎵 Teste do TikTok: o Reels de hoje foi para a caixa de entrada do TikTok da @lectnex como RASCUNHO. Abra o app do TikTok, veja a notificação, ajuste e publique.')
    except Exception:
        pass


def status(pid=None):
    """Situação de um envio (padrão: os últimos guardados em tiktok/envios.json ou o publish_id dado)."""
    tok = acesso()
    pids = [pid] if pid else [p for p in (os.environ.get('TIKTOK_PID') or '').split() if p]
    for p in pids:
        d = api('post/publish/status/fetch/', tok, {'publish_id': p})
        ig.note('notice', f'TikTok {p}: {json.dumps(d, ensure_ascii=False)[:400]}')


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


def reenviar(dias=3):
    """Manda como rascunho os Reels já publicados no Instagram que não chegaram ao TikTok (últimos `dias`), com a legenda."""
    import datetime as dt
    f, sha = ig.fila_ler()
    limite = (dt.datetime.now(ig.BRT) - dt.timedelta(days=dias)).isoformat(timespec='minutes')
    feitos = 0
    for p in f.get('pedidos', []):
        if p.get('video') and p.get('tipo') != 'story' and p.get('status') == 'publicado' and not p.get('tiktok') and (p.get('publicado') or p.get('criado') or '') >= limite:
            try:
                p['tiktok'] = rascunho(p['video']); p.pop('erro_tiktok', None); feitos += 1
                ig.tg('sendMessage', chat_id=ig.admin(), text=f'🎵 TikTok: "{p.get("nome") or p["id"]}" foi para a caixa de entrada do app como rascunho.')
                enviar_legenda(p.get('legenda', ''))
            except Exception as e:
                p['erro_tiktok'] = (str(e) or e.__class__.__name__)[:200]
                ig.note('warning', f'TikTok {p["id"]}: {p["erro_tiktok"]}')
    if feitos:
        ig.fila_gravar(f, sha)
    ig.note('notice', f'TikTok: {feitos} Reels reenviado(s) como rascunho.')


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
    elif cmd == 'status':
        status()
    elif cmd == 'legenda':
        import datetime as dt
        legenda_do_dia(os.environ.get('KIT_DIA') or dt.datetime.now(ig.BRT).date().isoformat())
    elif cmd == 'teste-rascunho':
        teste_rascunho()
    elif cmd == 'reenviar':
        reenviar()
    elif cmd == 'teste-post':
        teste_post()
    elif cmd == 'conectar':
        conectar(os.environ.get('TIKTOK_CODE') or sys.argv[2])
    else:
        teste()
