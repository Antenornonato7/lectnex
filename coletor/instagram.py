"""Instagram com aprovação no Telegram: o sistema propõe o post, o dono aprova com um toque e ele é publicado no feed.

Fluxo
  1. propor   — converte as imagens para JPEG, hospeda no branch 'ao-vivo' (URL pública que a Meta busca), grava o pedido em
                ig/fila.json e manda no Telegram PRIVADO a prévia com os botões [Publicar no Instagram] [Descartar].
  2. processar — lê os toques nos botões (getUpdates do bot; só vale o chat do dono) e publica pela API oficial do Instagram
                 (Instagram API with Instagram Login, graph.instagram.com). Roda dentro do laço de notícias (a cada ~2,5 min).
                 Pedidos com mais de 36 h expiram.
  3. renovar  — renova o token de longa duração (60 dias). Roda toda segunda pelo Relógio.

Segredos (GitHub → Settings → Secrets → Actions): INSTAGRAM_TOKEN (token de usuário do Instagram com
instagram_business_basic + instagram_business_content_publish). Opcional: INSTAGRAM_USER_ID (senão é lido de /me).
Sem INSTAGRAM_TOKEN, 'propor' ainda manda a prévia (sem botão) e nada é publicado.

Uso: python3 coletor/instagram.py propor <tipo> <legenda.txt> <img1.png> [img2.png ...]
     python3 coletor/instagram.py processar | renovar | teste
"""
import base64
import datetime as dt
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

BRT = dt.timezone(dt.timedelta(hours=-3))
REPO = os.environ.get('GITHUB_REPOSITORY', 'Antenornonato7/lectnex')
GH = f'https://api.github.com/repos/{REPO}'
RAW = f'https://raw.githubusercontent.com/{REPO}/ao-vivo/'
IG = 'https://graph.instagram.com/v25.0'
FILA = 'ig/fila.json'
TIPOS = {'grafico': 'Gráfico do dia (notícia × preço)', 'carrossel': 'Carrossel da semana'}


def note(k, m):
    print(f'::{k}::{m}')


# ---------- GitHub (branch ao-vivo) ----------
def gh(metodo, url, dados=None):
    req = urllib.request.Request(url, method=metodo, data=json.dumps(dados).encode() if dados is not None else None,
                                 headers={'Authorization': f'Bearer {os.environ["GITHUB_TOKEN"]}', 'Accept': 'application/vnd.github+json',
                                          'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'lectnex-bot'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or b'{}')


def gh_ler(caminho):
    try:
        j = gh('GET', f'{GH}/contents/{caminho}?ref=ao-vivo')
        return json.loads(base64.b64decode(j['content'])), j['sha']
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None, None
        raise


def gh_gravar(caminho, conteudo, sha=None, msg='instagram'):
    corpo = {'message': msg, 'branch': 'ao-vivo', 'content': base64.b64encode(conteudo).decode()}
    if sha:
        corpo['sha'] = sha
    return gh('PUT', f'{GH}/contents/{caminho}', corpo)


def fila_ler():
    f, sha = gh_ler(FILA)
    return f or {'offset': 0, 'pedidos': []}, sha


def fila_gravar(f, sha):
    gh_gravar(FILA, json.dumps(f, ensure_ascii=False, indent=1).encode(), sha, 'instagram: fila')


# ---------- Telegram ----------
def tg(metodo, **dados):
    tok = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
    req = urllib.request.Request(f'https://api.telegram.org/bot{tok}/{metodo}', data=json.dumps(dados).encode(),
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read())


def admin():
    return os.environ.get('TELEGRAM_ADMIN_CHAT_ID', '').strip()


def esc(s):
    return (s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


# ---------- Instagram ----------
def ig(metodo, caminho, **params):
    params['access_token'] = os.environ['INSTAGRAM_TOKEN'].strip()
    dados = urllib.parse.urlencode(params).encode()
    url = f'{IG}/{caminho}' + ('' if metodo == 'POST' else '?' + dados.decode())
    req = urllib.request.Request(url, data=dados if metodo == 'POST' else None, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        corpo = e.read().decode()[:300]
        try:
            corpo = json.loads(corpo)['error'].get('message', corpo)
        except Exception:
            pass
        raise RuntimeError(f'Instagram HTTP {e.code}: {corpo}') from None


def ig_user():
    return os.environ.get('INSTAGRAM_USER_ID', '').strip() or str(ig('GET', 'me', fields='user_id')['user_id'])


def esperar(cid):
    for _ in range(30):
        st = ig('GET', cid, fields='status_code').get('status_code')
        if st == 'FINISHED':
            return
        if st in ('ERROR', 'EXPIRED'):
            raise RuntimeError(f'Contêiner {st}')
        time.sleep(6)
    raise RuntimeError('Contêiner não ficou pronto em 3 min')


def publicar(p):
    uid = ig_user()
    if len(p['imagens']) == 1:
        cid = ig('POST', f'{uid}/media', image_url=p['imagens'][0], caption=p['legenda'])['id']
    else:
        filhos = [ig('POST', f'{uid}/media', image_url=u, is_carousel_item='true')['id'] for u in p['imagens'][:10]]
        for f in filhos:
            esperar(f)
        cid = ig('POST', f'{uid}/media', media_type='CAROUSEL', children=','.join(filhos), caption=p['legenda'])['id']
    esperar(cid)
    mid = ig('POST', f'{uid}/media_publish', creation_id=cid)['id']
    try:
        return ig('GET', mid, fields='permalink').get('permalink')
    except Exception:
        return None


# ---------- comandos ----------
def propor(tipo, legenda_arq, imagens):
    from PIL import Image
    legenda = open(legenda_arq, encoding='utf-8').read().strip()[:2200]
    pid = dt.datetime.now(BRT).strftime('%Y%m%d-%H%M') + '-' + tipo
    urls = []
    for i, arq in enumerate(imagens[:10], 1):
        buf = io.BytesIO()
        im = Image.open(arq).convert('RGB')
        if im.width > 1440:
            im = im.resize((1440, round(im.height * 1440 / im.width)))
        im.save(buf, 'JPEG', quality=92, optimize=True)
        caminho = f'ig/{pid}/{i}.jpg'
        gh_gravar(caminho, buf.getvalue(), msg=f'instagram: {pid}')
        urls.append(RAW + caminho)
    f, sha = fila_ler()
    f['pedidos'] = [x for x in f['pedidos'] if x['id'] != pid] + [{'id': pid, 'tipo': tipo, 'legenda': legenda, 'imagens': urls,
                                                                    'status': 'aguardando', 'criado': dt.datetime.now(BRT).isoformat(timespec='minutes')}]
    f['pedidos'] = f['pedidos'][-40:]
    fila_gravar(f, sha)
    tem_ig = bool(os.environ.get('INSTAGRAM_TOKEN', '').strip())
    if not tem_ig and tipo == 'grafico':
        print(f'Pedido {pid}: modo manual, a legenda vai no Kit do dia das 19h30.')
        return
    if not tem_ig:
        # modo manual: as imagens já chegaram no Telegram; aqui vai só a legenda limpa, fácil de copiar no celular
        tg('sendMessage', chat_id=admin(), text=f'📋 Legenda pronta para copiar ({TIPOS.get(tipo, tipo)}):')
        tg('sendMessage', chat_id=admin(), text=legenda, disable_web_page_preview=True)
        print(f'Pedido {pid}: modo manual, legenda enviada.')
        return
    texto = (f'📸 <b>Post para o feed: {esc(TIPOS.get(tipo, tipo))}</b>' + (f' ({len(urls)} imagens)' if len(urls) > 1 else '') +
             f'\n\n<b>Legenda:</b>\n{esc(legenda[:700])}' + ('…' if len(legenda) > 700 else '') +
             ('\n\nToque em <b>Publicar</b> para postar agora no Instagram (vale por 36 h).' if tem_ig else
              '\n\n<i>Publicação automática desligada: falta o segredo INSTAGRAM_TOKEN.</i>'))
    botoes = {'inline_keyboard': [[{'text': '✅ Publicar no Instagram', 'callback_data': f'ig:pub:{pid}'},
                                   {'text': '🗑️ Descartar', 'callback_data': f'ig:del:{pid}'}]]} if tem_ig else None
    r = tg('sendMessage', chat_id=admin(), text=texto, parse_mode='HTML', disable_web_page_preview=True, **({'reply_markup': botoes} if botoes else {}))
    f, sha = fila_ler()
    for x in f['pedidos']:
        if x['id'] == pid:
            x['msg_id'] = r['result']['message_id']
    fila_gravar(f, sha)
    print(f'Pedido {pid} proposto ({len(urls)} imagem/ns).')


def processar():
    if not (os.environ.get('TELEGRAM_BOT_TOKEN') and admin()):
        return
    f, sha = fila_ler()
    pend = [p for p in f['pedidos'] if p['status'] == 'aguardando']
    if not pend:
        return
    agora = dt.datetime.now(BRT)
    mudou = False
    for p in pend:
        if agora - dt.datetime.fromisoformat(p['criado']) > dt.timedelta(hours=36):
            p['status'] = 'expirado'
            mudou = True
            try:
                tg('editMessageReplyMarkup', chat_id=admin(), message_id=p.get('msg_id'), reply_markup={'inline_keyboard': []})
            except Exception:
                pass
    ups = tg('getUpdates', offset=f.get('offset', 0) + 1 if f.get('offset') else 0, timeout=0, allowed_updates=['callback_query']).get('result', [])
    for u in ups:
        f['offset'] = u['update_id']
        mudou = True
        cq = u.get('callback_query')
        if not cq:
            continue
        de = str((cq.get('from') or {}).get('id', ''))
        if de != admin():
            tg('answerCallbackQuery', callback_query_id=cq['id'], text='Só o dono pode aprovar.')
            continue
        partes = (cq.get('data') or '').split(':', 2)
        if len(partes) != 3 or partes[0] != 'ig':
            continue
        p = next((x for x in f['pedidos'] if x['id'] == partes[2]), None)
        if not p or p['status'] != 'aguardando':
            tg('answerCallbackQuery', callback_query_id=cq['id'], text='Este post não está mais aguardando.')
            continue
        mid = (cq.get('message') or {}).get('message_id')
        if partes[1] == 'del':
            p['status'] = 'descartado'
            tg('answerCallbackQuery', callback_query_id=cq['id'], text='Descartado.')
            tg('editMessageReplyMarkup', chat_id=admin(), message_id=mid, reply_markup={'inline_keyboard': []})
            tg('sendMessage', chat_id=admin(), text='🗑️ Post descartado.', reply_to_message_id=mid)
            continue
        tg('answerCallbackQuery', callback_query_id=cq['id'], text='Publicando no Instagram…')
        try:
            link = publicar(p)
            p['status'], p['publicado'], p['link'] = 'publicado', agora.isoformat(timespec='minutes'), link
            tg('editMessageReplyMarkup', chat_id=admin(), message_id=mid, reply_markup={'inline_keyboard': []})
            tg('sendMessage', chat_id=admin(), text='✅ Publicado no Instagram.' + (f'\n{link}' if link else ''), reply_to_message_id=mid)
            note('notice', f'Instagram: {p["id"]} publicado')
        except Exception as e:
            p['erro'] = str(e)[:200]
            tg('sendMessage', chat_id=admin(), text=f'⚠️ Não consegui publicar: {esc(str(e)[:200])}\nOs botões continuam valendo para tentar de novo.', parse_mode='HTML', reply_to_message_id=mid)
            note('warning', f'Instagram: falha ao publicar {p["id"]}: {e}')
    if mudou:
        fila_gravar(f, sha)


def renovar():
    if not os.environ.get('INSTAGRAM_TOKEN', '').strip():
        print('Sem INSTAGRAM_TOKEN: nada a renovar.')
        return
    tok = os.environ['INSTAGRAM_TOKEN'].strip()
    url = 'https://graph.instagram.com/refresh_access_token?' + urllib.parse.urlencode({'grant_type': 'ig_refresh_token', 'access_token': tok})
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            j = json.loads(r.read())
    except urllib.error.HTTPError as e:
        msg = e.read().decode()[:200]
        note('warning', f'Token do Instagram não renovado: HTTP {e.code}')
        if os.environ.get('TELEGRAM_BOT_TOKEN') and admin():
            tg('sendMessage', chat_id=admin(), text='⚠️ O token do Instagram não pôde ser renovado (pode ter expirado). Gere um novo no painel da Meta '
               'e atualize o segredo INSTAGRAM_TOKEN no GitHub. Detalhe: ' + esc(msg[:120]), parse_mode='HTML')
        return
    dias = round(j.get('expires_in', 0) / 86400)
    note('notice', f'Token do Instagram renovado: vale por mais {dias} dias')
    if j.get('access_token') and j['access_token'] != tok and os.environ.get('TELEGRAM_BOT_TOKEN') and admin():
        tg('sendMessage', chat_id=admin(), text='ℹ️ A Meta devolveu um token do Instagram diferente na renovação. Para evitar que ele expire, '
           'gere um token novo no painel da Meta e atualize o segredo INSTAGRAM_TOKEN no GitHub.')


def teste():
    """Confere o token e a conta, sem publicar nada."""
    u = ig('GET', 'me', fields='user_id,username,account_type')
    lim = ig('GET', f'{u["user_id"]}/content_publishing_limit', fields='quota_usage,config')
    print(f'Conta @{u.get("username")} ({u.get("account_type")}) · uso de publicação nas últimas 24 h: {lim}')
    note('notice', f'Instagram conectado: @{u.get("username")}')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'processar'
    if cmd == 'propor':
        propor(sys.argv[2], sys.argv[3], sys.argv[4:])
    elif cmd == 'processar':
        processar()
    elif cmd == 'renovar':
        renovar()
    elif cmd == 'teste':
        teste()
