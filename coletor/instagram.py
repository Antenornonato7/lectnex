"""Instagram com aprovação no Telegram: o sistema propõe o post, o dono aprova com um toque e ele é publicado no feed.

Fluxo
  1. propor   — converte as imagens para JPEG, hospeda no branch 'ao-vivo' (URL pública que a Meta busca), grava o pedido em
                ig/fila.json e manda no Telegram PRIVADO a prévia com os botões [Publicar no Instagram] [Descartar].
  2. processar — lê os toques nos botões (getUpdates do bot; só vale o chat do dono) e publica pela API oficial do Instagram
                 (Instagram API with Instagram Login, graph.instagram.com). Roda dentro do laço de notícias (a cada ~2,5 min).
                 Pedidos com mais de 36 h expiram.
  3. renovar  — renova o token de longa duração (60 dias). Roda toda segunda pelo Relógio.

Segredos (GitHub → Settings → Secrets → Actions): INSTAGRAM_TOKEN. Dois tipos aceitos:
  - token da Página do Facebook ligada ao Instagram (começa com EAA; permissões instagram_basic, instagram_content_publish,
    pages_show_list, pages_read_engagement, business_management). É o caminho atual: a Página Lectnex está ligada à @lectnex.oficial.
  - token do Instagram API with Instagram Login (instagram_business_basic + instagram_business_content_publish). Opcional: INSTAGRAM_USER_ID (senão é lido de /me).
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
IG_IG = 'https://graph.instagram.com/v25.0'   # token do "Instagram API with Instagram Login" (começa com IG)
IG_FB = 'https://graph.facebook.com/v25.0'    # token da Página do Facebook ligada ao Instagram (começa com EAA)


def pela_pagina():
    """True quando o segredo é um token do Facebook (Página Lectnex ligada à @lectnex.oficial).
    Esse caminho usa a mesma API de publicação, só que em graph.facebook.com."""
    return os.environ.get('INSTAGRAM_TOKEN', '').strip().startswith('EAA')
FILA = 'ig/fila.json'
TIPOS = {'grafico': 'Gráfico do dia (notícia × preço)', 'carrossel': 'Carrossel da semana', 'reel': 'Reels do dia',
         'story': 'Story do fechamento', 'reel-semana': 'Reels da semana', 'simulador': 'Simulador: pregão da semana',
         'ranking': 'Ranking da semana (carrossel)', 'agenda': 'Agenda da semana'}


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
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'Telegram {metodo} HTTP {e.code}: {e.read().decode()[:200]}') from None


def admin():
    return os.environ.get('TELEGRAM_ADMIN_CHAT_ID', '').strip()


def esc(s):
    return (s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


# ---------- Instagram ----------
def ig(metodo, caminho, **params):
    params['access_token'] = os.environ['INSTAGRAM_TOKEN'].strip()
    dados = urllib.parse.urlencode(params).encode()
    url = f'{IG_FB if pela_pagina() else IG_IG}/{caminho}' + ('' if metodo == 'POST' else '?' + dados.decode())
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


_UID = None


def ig_user():
    global _UID
    if _UID:
        return _UID
    _UID = os.environ.get('INSTAGRAM_USER_ID', '').strip()
    if not _UID and pela_pagina():
        conta = None
        try:                                                                 # token da Página: o "me" é a própria Página
            conta = (ig('GET', 'me', fields='instagram_business_account').get('instagram_business_account') or {}).get('id')
        except RuntimeError:
            pass                                                             # token de usuário: o campo não existe no "me"
        if not conta:                                                        # token de usuário: procura nas Páginas dele
            for pg in ig('GET', 'me/accounts', fields='name,instagram_business_account').get('data', []):
                conta = (pg.get('instagram_business_account') or {}).get('id')
                if conta:
                    break
        if not conta:
            raise RuntimeError('Nenhuma conta do Instagram ligada à Página encontrada com esse token')
        _UID = str(conta)
    elif not _UID:
        _UID = str(ig('GET', 'me', fields='user_id')['user_id'])
    return _UID


def esperar(cid, tentativas=30):
    for _ in range(tentativas):
        st = ig('GET', cid, fields='status_code').get('status_code')
        if st == 'FINISHED':
            return
        if st in ('ERROR', 'EXPIRED'):
            raise RuntimeError(f'Contêiner {st}')
        time.sleep(6)
    raise RuntimeError('Contêiner não ficou pronto em 3 min')


def subir_video(uid, video_url, **params):
    """Reels e stories em vídeo: envio direto do arquivo para a Meta (upload resumível), sem depender de um link público
    com o tipo de arquivo certo (o raw do GitHub entrega vídeo como application/octet-stream)."""
    c = ig('POST', f'{uid}/media', upload_type='resumable', **params)
    corpo = urllib.request.urlopen(video_url, timeout=120).read()
    req = urllib.request.Request(c['uri'], data=corpo, method='POST', headers={
        'Authorization': 'OAuth ' + os.environ['INSTAGRAM_TOKEN'].strip(), 'offset': '0', 'file_size': str(len(corpo))})
    try:
        urllib.request.urlopen(req, timeout=300).read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'Envio do vídeo recusado (HTTP {e.code}): {e.read().decode()[:200]}') from None
    esperar(c['id'], 60)
    return c['id']


def publicar(p):
    uid = ig_user()
    tipo = p.get('tipo', '')
    if p.get('video'):
        if tipo == 'story':
            cid = subir_video(uid, p['video'], media_type='STORIES')
        else:
            cid = subir_video(uid, p['video'], media_type='REELS', caption=p.get('legenda', ''), share_to_feed='true')
    elif tipo == 'story':
        cid = ig('POST', f'{uid}/media', image_url=p['imagens'][0], media_type='STORIES')['id']
    elif len(p['imagens']) == 1:
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


# ---------- Página do Facebook (mesma chave, permissões pages_manage_posts e pages_manage_metadata) ----------
FB = 'https://graph.facebook.com/v25.0'
_PG = None


def fb(metodo, caminho, token, **params):
    params['access_token'] = token
    dados = urllib.parse.urlencode(params).encode()
    url = f'{FB}/{caminho}' + ('' if metodo == 'POST' else '?' + dados.decode())
    req = urllib.request.Request(url, data=dados if metodo == 'POST' else None, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        corpo = e.read().decode()[:300]
        try:
            corpo = json.loads(corpo)['error'].get('message', corpo)
        except Exception:
            pass
        raise RuntimeError(f'Facebook HTTP {e.code}: {corpo}') from None


def fb_pagina():
    """(id da Página, token da Página). Com token de usuário, o token da Página vem de me/accounts."""
    global _PG
    if _PG:
        return _PG
    tok = os.environ.get('INSTAGRAM_TOKEN', '').strip()
    if not tok.startswith('EAA'):
        raise RuntimeError('Página do Facebook: o INSTAGRAM_TOKEN não é uma chave do Facebook')
    try:
        eu = fb('GET', 'me', tok, fields='id,name,instagram_business_account')
        if eu.get('instagram_business_account'):
            _PG = (eu['id'], tok)
            return _PG
    except RuntimeError:
        pass
    for pg in fb('GET', 'me/accounts', tok, fields='id,name,access_token,instagram_business_account').get('data', []):
        if pg.get('instagram_business_account') or pg.get('name', '').lower().startswith('lectnex'):
            _PG = (pg['id'], pg['access_token'])
            return _PG
    raise RuntimeError('Página Lectnex não encontrada com essa chave')


def publicar_facebook(p):
    """Mesmo post na Página do Facebook. Devolve o link ou levanta erro."""
    pid, ptok = fb_pagina()
    tipo, leg = p.get('tipo', ''), p.get('legenda', '')
    if p.get('video'):
        ini = fb('POST', f'{pid}/video_reels', ptok, upload_phase='start')
        corpo = urllib.request.urlopen(p['video'], timeout=120).read()
        req = urllib.request.Request(ini['upload_url'], data=corpo, method='POST',
                                     headers={'Authorization': 'OAuth ' + ptok, 'offset': '0', 'file_size': str(len(corpo))})
        urllib.request.urlopen(req, timeout=300).read()
        if tipo == 'story':
            fb('POST', f'{pid}/video_stories', ptok, upload_phase='finish', video_id=ini['video_id'])
            return f'https://www.facebook.com/{pid}'
        fb('POST', f'{pid}/video_reels', ptok, upload_phase='finish', video_id=ini['video_id'], video_state='PUBLISHED', description=leg)
        return f'https://www.facebook.com/reel/{ini["video_id"]}'
    if tipo == 'story':
        foto = fb('POST', f'{pid}/photos', ptok, url=p['imagens'][0], published='false')['id']
        fb('POST', f'{pid}/photo_stories', ptok, photo_id=foto)
        return f'https://www.facebook.com/{pid}'
    if len(p['imagens']) == 1:
        r = fb('POST', f'{pid}/photos', ptok, url=p['imagens'][0], message=leg)
        return f'https://www.facebook.com/{r.get("post_id") or r["id"]}'
    fotos = [fb('POST', f'{pid}/photos', ptok, url=u, published='false')['id'] for u in p['imagens'][:10]]
    params = {f'attached_media[{i}]': json.dumps({'media_fbid': f}) for i, f in enumerate(fotos)}
    r = fb('POST', f'{pid}/feed', ptok, message=leg, **params)
    return f'https://www.facebook.com/{r["id"]}'


def facebook_perfil():
    """Coloca a logo como foto da Página e a capa (assets/brand/fb-capa.jpg) — imagens servidas pelo próprio site."""
    pid, ptok = fb_pagina()
    fb('POST', f'{pid}/picture', ptok, picture='https://lectnex.com.br/assets/brand/icon-512.png')
    foto = fb('POST', f'{pid}/photos', ptok, url='https://lectnex.com.br/assets/brand/fb-capa.jpg', published='false')['id']
    fb('POST', pid, ptok, cover=foto)
    note('notice', 'Página do Facebook: foto de perfil e capa atualizadas.')


def facebook_pendentes(dias=2):
    """Manda no Telegram, com botão "Publicar no Facebook", os posts dos últimos dias que saíram só no Instagram."""
    f, sha = fila_ler()
    limite = dt.datetime.now(BRT) - dt.timedelta(days=dias)
    n = 0
    for x in f['pedidos']:
        if x.get('status') != 'publicado' or x.get('link_fb') or dt.datetime.fromisoformat(x['criado']) < limite:
            continue
        nome = x.get('nome') or TIPOS.get(x['tipo'], x['tipo'])
        if x.get('video'):
            tg('sendVideo', chat_id=admin(), video=x['video'], caption=f'Prévia: {nome}')
        elif x.get('imagens'):
            tg('sendPhoto', chat_id=admin(), photo=x['imagens'][0], caption=f'Prévia: {nome}')
        r = tg('sendMessage', chat_id=admin(), parse_mode='HTML', disable_web_page_preview=True,
               text=f'📘 <b>{esc(nome)}</b> já está no Instagram' + (f' ({x["link"]})' if x.get('link') else '') + '.\nToque para publicar também na Página do Facebook.',
               reply_markup={'inline_keyboard': [[{'text': '✅ Publicar no Facebook', 'callback_data': f'ig:fb:{x["id"]}'}]]})
        x['fb_pendente'] = True
        x['msg_fb'] = r['result']['message_id']
        n += 1
    if n:
        fila_gravar(f, sha)
    note('notice', f'{n} post(s) do Instagram propostos para a Página do Facebook.')


def facebook_propor(arq_texto, imagem_url, pid=None):
    """Post só para a Página do Facebook (ex.: apresentação), com botão de aprovação no Telegram."""
    texto = open(arq_texto, encoding='utf-8').read().strip()
    pid = pid or dt.datetime.now(BRT).strftime('%Y%m%d-%H%M') + '-facebook'
    x = {'id': pid, 'tipo': 'facebook', 'nome': 'Post na Página do Facebook', 'legenda': texto, 'imagens': [imagem_url],
         'status': 'publicado', 'so_facebook': True, 'fb_pendente': True, 'criado': dt.datetime.now(BRT).isoformat(timespec='minutes')}
    tg('sendPhoto', chat_id=admin(), photo=imagem_url, caption='Prévia: post na Página do Facebook')
    r = tg('sendMessage', chat_id=admin(), parse_mode='HTML', disable_web_page_preview=True,
           text=f'📘 <b>Post na Página do Facebook</b>\n\n{esc(texto[:900])}\n\nToque para publicar na Página Lectnex.',
           reply_markup={'inline_keyboard': [[{'text': '✅ Publicar no Facebook', 'callback_data': f'ig:fb:{pid}'}]]})
    x['msg_fb'] = r['result']['message_id']
    f, sha = fila_ler()
    f['pedidos'] = [y for y in f['pedidos'] if y['id'] != pid] + [x]
    f['pedidos'] = f['pedidos'][-40:]
    fila_gravar(f, sha)
    note('notice', f'Post do Facebook proposto: {pid}')


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


def enviar_previa(x):
    rot = {'reel': 'Publicar como Reels', 'reel-semana': 'Publicar como Reels', 'story': 'Publicar no Story'}.get(x['tipo'], 'Publicar no Instagram')
    texto = (f'📸 <b>{esc(x.get("nome") or TIPOS.get(x["tipo"], x["tipo"]))}</b>' + (f' ({len(x["imagens"])} imagens)' if len(x.get('imagens') or []) > 1 else '') +
             (f'\n\n<b>Legenda:</b>\n{esc(x["legenda"][:700])}' + ('…' if len(x['legenda']) > 700 else '') if x.get('legenda') else '') +
             f'\n\nToque em <b>{rot}</b> para postar agora (vale por 36 h).')
    botoes = {'inline_keyboard': [[{'text': f'✅ {rot}', 'callback_data': f'ig:pub:{x["id"]}'}, {'text': '🗑️ Descartar', 'callback_data': f'ig:del:{x["id"]}'}]]}
    if x.get('video'):
        tg('sendVideo', chat_id=admin(), video=x['video'], caption=f'Prévia: {TIPOS.get(x["tipo"], x["tipo"])}')
    elif x.get('imagens'):
        tg('sendPhoto', chat_id=admin(), photo=x['imagens'][0], caption=f'Prévia: {TIPOS.get(x["tipo"], x["tipo"])}')
    r = tg('sendMessage', chat_id=admin(), text=texto, parse_mode='HTML', disable_web_page_preview=True, reply_markup=botoes)
    x['msg_id'] = r['result']['message_id']


STORIES_KIT = {'leitura': 'Story da Leitura do Dia', 'termo': 'Story do Termo do dia', 'fechamento': 'Story do fechamento',
               'placar': 'Story do placar da semana', 'antes': 'Story Antes do dado'}


def kit_instagram(dia=None, so=None):
    """Propõe no Telegram, com botão, peças do Kit do dia (branch ao-vivo): post do gráfico, Reels e stories.
    so: lista de chaves (ex.: ['leitura', 'termo']); sem ela, propõe gráfico, Reels e story do fechamento.
    Peça já proposta ou publicada não é proposta de novo."""
    dia = dia or dt.datetime.now(BRT).date().isoformat()
    kit, _ = gh_ler(f'kit/{dia}/kit.json')
    if not kit:
        note('warning', f'Sem kit em kit/{dia}/'); return
    agora, d8 = dt.datetime.now(BRT), dia.replace('-', '')
    so = so or ['grafico', 'reel', 'reel-quiz', 'reel-ferramenta', 'reel-semana', 'fechamento']
    pecas = {pc['chave']: pc for pc in kit.get('pecas', [])}
    novos = []
    for chave in so:
        if chave == 'grafico' and 'grafico' in pecas:
            novos.append({'id': f'{d8}-kit-grafico', 'tipo': 'grafico', 'legenda': pecas['grafico'].get('legenda', ''), 'imagens': [RAW + f'kit/{dia}/grafico.jpg']})
        elif chave in (kit.get('reels') or {}):
            rl = kit['reels'][chave]
            novos.append({'id': f'{d8}-kit-{chave}', 'tipo': 'reel' if chave == 'reel' else 'reel-semana', 'legenda': rl.get('legenda', ''),
                          'nome': rl.get('nome'), 'imagens': [], 'video': RAW + f'kit/{dia}/{chave}.mp4', 'x': rl.get('x', '')})
        elif chave in pecas and pecas[chave].get('formato') == 'story':
            novos.append({'id': f'{d8}-kit-story-{chave}', 'tipo': 'story', 'nome': STORIES_KIT.get(chave, pecas[chave].get('nome')), 'legenda': '',
                          'imagens': [RAW + f'kit/{dia}/{chave}.jpg']})
    f, sha = fila_ler()
    ja = {x['id'] for x in f['pedidos'] if x.get('status') in ('aguardando', 'publicado')}
    if any(x.get('tipo') == 'grafico' and x['id'].startswith(d8) for x in f['pedidos'] if x.get('status') in ('aguardando', 'publicado')):
        ja.add(f'{d8}-kit-grafico')  # o gráfico proposto pelo fechamento (19h10) já está na fila
    novos = [n for n in novos if n['id'] not in ja]
    for n in novos:
        n.update(status='aguardando', criado=agora.isoformat(timespec='minutes'))
        enviar_previa(n)
        f['pedidos'].append(n)
        try:  # texto pronto para o X (postado à mão, sem pagar a API)
            xt = n.pop('x', '') or (texto_x_grafico(n['legenda']) if n['tipo'] == 'grafico' else '')
            if xt:
                enviar_x(xt, n['imagens'][0] if n.get('imagens') else None)
        except Exception as e:
            note('warning', f'Texto do X não enviado: {e}')
    f['pedidos'] = f['pedidos'][-40:]
    if novos:
        fila_gravar(f, sha)
    note('notice', f'{len(novos)} peça(s) do kit propostas no Telegram' + (': ' + ', '.join(n.get('nome') or n['tipo'] for n in novos) if novos else ''))


def texto_x_grafico(leg):
    """Post do X a partir da legenda do gráfico do dia: 1ª frase + a manchete que mais mexeu + link + Discord (até ~280 caracteres)."""
    linhas = [l.strip() for l in (leg or '').splitlines() if l.strip() and not l.strip().startswith('#')]
    if not linhas:
        return ''
    abre = linhas[0].split(':')[0].rstrip('.') + ' 👇'
    top = next((l for l in linhas[1:] if l[:2].rstrip('.').isdigit()), '')
    top = top.split('·', 1)[-1].strip() if top else ''
    corpo = abre + ('\n\n' + (top[:120] + ('…' if len(top) > 120 else '')) if top else '')
    return corpo + '\n\nGráfico com as manchetes no horário:\nhttps://lectnex.com.br/hoje.html\n\nComunidade: https://discord.gg/kM6YcQA82P'


def enviar_x(texto, imagem=None):
    """Manda no Telegram privado um post pronto para o X: a imagem (se houver) e o texto sozinho para copiar."""
    tg('sendMessage', chat_id=admin(), text='🐦 <b>Post para o X</b>' + (' (salve a imagem acima e anexe)' if imagem else '') + ': copie a próxima mensagem.',
       parse_mode='HTML')
    if imagem:
        try:
            tg('sendPhoto', chat_id=admin(), photo=imagem)
        except Exception:
            pass
    tg('sendMessage', chat_id=admin(), text=texto, disable_web_page_preview=True)


ORIGENS = {'convite-simulador': 'convite no simulador', 'convite-risco': 'convite nas calculadoras', 'convite-leitura': 'convite nas páginas de leitura',
           'site': 'formulários do site (rodapé e páginas)', 'lista-pro': 'página da Lectnex Pro'}


def _metricas(mid):
    met = {}
    for lista in ('reach,saved,shares,views', 'reach,saved,shares', 'reach'):
        try:
            for x in ig('GET', f'{mid}/insights', metric=lista).get('data', []):
                met[x['name']] = (x.get('values') or [{}])[0].get('value', x.get('total_value', {}).get('value'))
            break
        except Exception:
            continue
    return met


def placar_formatos(uid, dias=30):
    """Placar dos formatos (combinado em 19/11/2026): junta cada publicação dos últimos `dias` ao formato que a gerou (pelo link
    gravado na fila de aprovação) e calcula alcance, salvamentos e compartilhamentos médios por formato.
    Cliques no link por post não existem na API do Instagram: salvamento e compartilhamento são o melhor sinal de interesse."""
    f, _ = fila_ler()
    formato = {}
    for p in f.get('pedidos', []):
        if p.get('link'):
            formato[p['link'].rstrip('/')] = p.get('nome') or TIPOS.get(p.get('tipo'), p.get('tipo') or 'Outros')
    desde = dt.datetime.now(BRT) - dt.timedelta(days=dias)
    grupos, url, pags = {}, None, 0
    params = dict(fields='id,permalink,media_product_type,timestamp', limit=50)
    while pags < 4:
        r = ig('GET', url or f'{uid}/media', **({} if url else params)) if not url else json.loads(urllib.request.urlopen(url, timeout=40).read())
        dados = r.get('data', [])
        velho = False
        for m in dados:
            if dt.datetime.fromisoformat(m['timestamp'].replace('+0000', '+00:00')) < desde:
                velho = True
                continue
            nome = formato.get((m.get('permalink') or '').rstrip('/')) or {'REELS': 'Reels (manual)', 'FEED': 'Post (manual)'}.get(m.get('media_product_type'), 'Outros')
            met = _metricas(m['id'])
            g = grupos.setdefault(nome, {'n': 0, 'alcance': 0, 'salvos': 0, 'compart': 0})
            g['n'] += 1
            g['alcance'] += met.get('reach') or 0
            g['salvos'] += met.get('saved') or 0
            g['compart'] += met.get('shares') or 0
        url = (r.get('paging') or {}).get('next')
        pags += 1
        if velho or not url:
            break
    res = []
    for nome, g in grupos.items():
        n = g['n']
        res.append({'formato': nome, 'posts': n, 'alcance': round(g['alcance'] / n), 'salvos': round(g['salvos'] / n, 1),
                    'compart': round(g['compart'] / n, 1), 'interesse': round((g['salvos'] + g['compart']) / max(1, g['alcance']) * 1000, 1)})
    return sorted(res, key=lambda x: -x['alcance'])


def texto_placar(res, mes):
    if not res:
        return []
    txt = ['', f'🏁 <b>Placar dos formatos · {mes}</b> (média por publicação)']
    for i, x in enumerate(res[:8], 1):
        txt.append(f'{i}. {esc(x["formato"])} ({x["posts"]}×): alcance <b>{x["alcance"]}</b> · {x["salvos"]} salv. · {x["compart"]} compart.')
    com = [x for x in res if x['posts'] >= 2]
    if len(com) >= 2:
        top = max(com, key=lambda x: x['interesse'])
        fraco = min(com, key=lambda x: x['alcance'])
        txt.append(f'💡 Mais salvo/compartilhado por alcance: <b>{esc(top["formato"])}</b>. Mais fraco: {esc(fraco["formato"])}: candidato a trocar no mês que vem.')
    txt.append('<i>Clique no link por post não existe na API do Instagram: salvamento e compartilhamento medem o interesse.</i>')
    return txt


def relatorio_redes():
    """Relatório semanal no Telegram privado (domingo): seguidores no Instagram, Facebook e Discord com a variação da semana,
    e os posts dos últimos 7 dias ordenados por alcance, para saber o que repetir."""
    agora = dt.datetime.now(BRT)
    hist, sha = gh_ler('ig/redes.json')
    hist = hist or {}
    atual, linhas = {}, []
    uid = ig_user()
    try:
        perfil = ig('GET', uid, fields='followers_count,media_count')
        atual['instagram'] = perfil.get('followers_count')
    except Exception as e:
        linhas.append(f'Instagram: sem dados ({str(e)[:80]})')
    try:
        pid, ptok = fb_pagina()
        pg = fb('GET', pid, ptok, fields='followers_count,fan_count')
        atual['facebook'] = pg.get('followers_count') or pg.get('fan_count')
    except Exception as e:
        linhas.append(f'Facebook: sem dados ({str(e)[:80]})')
    try:
        tok = os.environ.get('DISCORD_BOT_TOKEN', '').strip()
        if tok:
            guild = os.environ.get('DISCORD_GUILD_ID', '1565140434445934722')
            req = urllib.request.Request(f'https://discord.com/api/v10/guilds/{guild}?with_counts=true',
                                         headers={'Authorization': f'Bot {tok}', 'User-Agent': 'LectnexBot (lectnex.com.br, 1.0)'})
            atual['discord'] = json.loads(urllib.request.urlopen(req, timeout=30).read()).get('approximate_member_count')
    except Exception as e:
        linhas.append(f'Discord: sem dados ({str(e)[:80]})')
    try:  # lista de espera da Lectnex Pro e newsletter (Buttondown)
        bk = os.environ.get('BUTTONDOWN_API_KEY', '').strip()
        if bk:
            def bd(q):
                req = urllib.request.Request(f'https://api.buttondown.com/v1/subscribers?{q}', headers={'Authorization': f'Token {bk}', 'X-API-Version': '2026-04-01'})
                return json.loads(urllib.request.urlopen(req, timeout=30).read()).get('count')
            atual['newsletter'] = bd('type=regular')
            atual['lista_pro'] = bd('tag=lista-pro')
            for t in ('pro-academia', 'pro-ferramentas', 'pro-comunidade'):
                atual[t] = bd(f'tag={t}')
            for t in ORIGENS:
                atual['o:' + t] = bd(f'tag={t}')
    except Exception as e:
        linhas.append(f'Buttondown: sem dados ({str(e)[:80]})')
    ant = hist.get('ultimo', {})
    nomes = {'instagram': 'Instagram', 'facebook': 'Facebook', 'discord': 'Discord', 'newsletter': 'Newsletter', 'lista_pro': '👑 Lista Pro'}
    topo = []
    for k, n in nomes.items():
        if atual.get(k) is None:
            continue
        dlt = atual[k] - ant[k] if ant.get(k) is not None else None
        topo.append(f'• {n}: <b>{atual[k]}</b>' + (f' ({"+" if dlt >= 0 else ""}{dlt} na semana)' if dlt is not None else ''))
    votos = {k: atual.get(k) for k in ('pro-academia', 'pro-ferramentas', 'pro-comunidade') if atual.get(k) is not None}
    if votos and sum(votos.values()):
        rot = {'pro-academia': 'trilhas', 'pro-ferramentas': 'ferramentas', 'pro-comunidade': 'comunidade'}
        topo.append('  ↳ quer mais: ' + ' · '.join(f'{rot[k]} {v}' for k, v in sorted(votos.items(), key=lambda x: -x[1])))
    orig = [(t, atual.get('o:' + t)) for t in ORIGENS if atual.get('o:' + t) is not None]
    if orig and sum(v for _, v in orig):
        topo += ['', '<b>De onde vêm os inscritos</b> (total · na semana)']
        for t, v in sorted(orig, key=lambda x: -((x[1] or 0) - (ant.get('o:' + x[0]) or 0) if ant.get('o:' + x[0]) is not None else x[1] or 0)):
            dl = v - ant['o:' + t] if ant.get('o:' + t) is not None else None
            topo.append(f'• {ORIGENS[t]}: <b>{v}</b>' + (f' · {"+" if dl >= 0 else ""}{dl}' if dl is not None else ''))
        melhor = max(orig, key=lambda x: (x[1] or 0) - (ant.get('o:' + x[0]) or 0))
        if ant and (melhor[1] or 0) - (ant.get('o:' + melhor[0]) or 0) > 0:
            topo.append(f'💡 Quem mais trouxe inscritos nesta semana: {ORIGENS[melhor[0]]}.')
    # posts da semana por alcance
    posts = []
    try:
        desde = agora - dt.timedelta(days=7)
        for m in ig('GET', f'{uid}/media', fields='id,caption,media_product_type,timestamp,permalink,like_count,comments_count', limit=30).get('data', []):
            quando = dt.datetime.fromisoformat(m['timestamp'].replace('+0000', '+00:00'))
            if quando < desde:
                continue
            met = {}
            for lista in ('reach,saved,shares,views', 'reach,saved,shares', 'reach'):
                try:
                    for x in ig('GET', f'{m["id"]}/insights', metric=lista).get('data', []):
                        met[x['name']] = (x.get('values') or [{}])[0].get('value', x.get('total_value', {}).get('value'))
                    break
                except Exception:
                    continue
            posts.append((met.get('reach') or 0, m, met))
    except Exception as e:
        linhas.append(f'Posts: sem dados ({str(e)[:80]})')
    posts.sort(key=lambda x: -x[0])
    tipo = {'REELS': 'Reels', 'FEED': 'Post', 'STORY': 'Story'}
    txt = ['📊 <b>Redes da Lectnex: semana até ' + agora.strftime('%d/%m') + '</b>', '', '<b>Seguidores</b>'] + (topo or ['• sem dados'])
    if posts:
        txt += ['', f'<b>Instagram: {len(posts)} publicações em 7 dias, por alcance</b>']
        for i, (alc, m, met) in enumerate(posts[:5], 1):
            cap = esc((m.get('caption') or '').split('\n')[0][:60])
            extras = ' · '.join(x for x in (f'{met["views"]} views' if met.get('views') else '', f'{met.get("saved") or 0} salv.',
                                            f'{met.get("shares") or 0} compart.', f'{m.get("comments_count") or 0} coment.') if x)
            txt.append(f'{i}. {tipo.get(m.get("media_product_type"), "Post")} · alcance <b>{alc}</b> · {extras}\n   <a href="{m["permalink"]}">{cap or "ver"}</a>')
        melhor = posts[0][1].get('media_product_type')
        reels = [p for p in posts if p[1].get('media_product_type') == 'REELS']
        feed = [p for p in posts if p[1].get('media_product_type') != 'REELS']
        if reels and feed:
            mr, mf = sum(p[0] for p in reels) / len(reels), sum(p[0] for p in feed) / len(feed)
            txt += ['', f'💡 Alcance médio: Reels {mr:.0f} × posts {mf:.0f}. ' + ('Reels estão rendendo mais: priorize os desafios.' if mr > mf else 'Os posts estão rendendo mais que os Reels nesta semana.')]
        elif melhor:
            txt += ['', '💡 Repita o formato do 1º lugar nesta semana.']
    if (agora + dt.timedelta(days=7)).month != agora.month or os.environ.get('PLACAR_FORCAR'):
        # último domingo do mês: placar dos formatos dos últimos 30 dias (fica pronto antes da troca de formatos do dia 1º)
        try:
            res = placar_formatos(uid)
            mes = agora.strftime('%m/%Y')
            txt += texto_placar(res, mes)
            hist.setdefault('formatos', []).append({'data': agora.date().isoformat(), 'mes': mes, 'placar': res})
            hist['formatos'] = hist['formatos'][-12:]
        except Exception as e:
            linhas.append(f'Placar dos formatos: sem dados ({str(e)[:80]})')
    txt += linhas and ['', '<i>' + esc(' · '.join(linhas)) + '</i>'] or []
    tg('sendMessage', chat_id=admin(), text='\n'.join(txt)[:4090], parse_mode='HTML', disable_web_page_preview=True)
    hist['ultimo'] = {k: v for k, v in atual.items() if v is not None}
    hist.setdefault('historico', []).append({'data': agora.date().isoformat(), **hist['ultimo']})
    hist['historico'] = hist['historico'][-60:]
    gh_gravar('ig/redes.json', json.dumps(hist, ensure_ascii=False, indent=1).encode(), sha, msg='redes: semana')
    note('notice', 'Relatório das redes enviado: ' + ', '.join(f'{k}={v}' for k, v in atual.items()))


def reenviar():
    """Manda de novo, com os botões, os pedidos ainda válidos (menos de 36 h) que foram propostos sem o INSTAGRAM_TOKEN."""
    f, sha = fila_ler()
    agora = dt.datetime.now(BRT)
    feitos = 0
    for x in f['pedidos']:
        if x.get('status') != 'aguardando' or (agora - dt.datetime.fromisoformat(x['criado'])).total_seconds() > 36 * 3600:
            continue
        enviar_previa(x)
        feitos += 1
    if feitos:
        fila_gravar(f, sha)
    note('notice', f'{feitos} pedido(s) reenviado(s) com o botão de publicar.')


def responder(cq, texto):
    """Resposta ao toque no botão. Se o toque é antigo (o laço roda a cada poucos minutos), o Telegram recusa a resposta:
    isso não pode impedir a publicação."""
    try:
        tg('answerCallbackQuery', callback_query_id=cq['id'], text=texto)
    except Exception:
        pass


def processar():
    if not (os.environ.get('TELEGRAM_BOT_TOKEN') and admin()):
        return
    f, sha = fila_ler()
    pend = [p for p in f['pedidos'] if p['status'] == 'aguardando']
    if not pend and not any(p.get('fb_pendente') for p in f['pedidos']):
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
            responder(cq, 'Só o dono pode aprovar.')
            continue
        partes = (cq.get('data') or '').split(':', 2)
        if len(partes) != 3 or partes[0] != 'ig':
            continue
        p = next((x for x in f['pedidos'] if x['id'] == partes[2]), None)
        if p and partes[1] == 'fb' and p['status'] == 'publicado' and not p.get('link_fb'):
            pass
        elif not p or p['status'] != 'aguardando':
            responder(cq, 'Este post não está mais aguardando.')
            continue
        mid = (cq.get('message') or {}).get('message_id')
        if partes[1] == 'fb':  # só na Página do Facebook (post que já saiu no Instagram)
            responder(cq, 'Publicando no Facebook…')
            try:
                p['link_fb'] = publicar_facebook(p)
                p.pop('erro_fb', None)
                p.pop('fb_pendente', None)
                txt = f'✅ Publicado na Página do Facebook.\n{p["link_fb"]}'
            except Exception as e:
                p['erro_fb'] = str(e)[:200]
                txt = f'⚠️ Não consegui publicar no Facebook: {esc(str(e)[:200])}\nO botão continua valendo para tentar de novo.'
            try:
                if p.get('link_fb'):
                    tg('editMessageReplyMarkup', chat_id=admin(), message_id=mid, reply_markup={'inline_keyboard': []})
                tg('sendMessage', chat_id=admin(), text=txt, parse_mode='HTML', reply_to_message_id=mid, disable_web_page_preview=True)
            except Exception:
                pass
            continue
        if partes[1] == 'del':
            p['status'] = 'descartado'
            responder(cq, 'Descartado.')
            try:
                tg('editMessageReplyMarkup', chat_id=admin(), message_id=mid, reply_markup={'inline_keyboard': []})
                tg('sendMessage', chat_id=admin(), text='🗑️ Post descartado.', reply_to_message_id=mid)
            except Exception:
                pass
            continue
        responder(cq, 'Publicando no Instagram…')
        try:
            link = publicar(p)
            p['status'], p['publicado'], p['link'] = 'publicado', agora.isoformat(timespec='minutes'), link
            note('notice', f'Instagram: {p["id"]} publicado')
            try:  # mesmo post na Página do Facebook (não impede o Instagram se falhar)
                p['link_fb'] = publicar_facebook(p)
                fbmsg = f'\n✅ Facebook: {p["link_fb"]}'
            except Exception as e:
                p['erro_fb'] = str(e)[:200]
                fbmsg = f'\n⚠️ Facebook: {str(e)[:150]}'
            if p.get('video') and p.get('tipo') != 'story' and os.environ.get('TIKTOK_CLIENT_KEY'):
                try:  # Reels também no TikTok: vai como rascunho para a caixa de entrada do app; o dono publica de lá
                    import tiktok
                    p['tiktok'] = tiktok.rascunho(p['video'])
                    fbmsg += '\n🎵 TikTok: rascunho na caixa de entrada do app (abra o TikTok e publique; a legenda própria do TikTok segue abaixo)'
                    try:
                        tiktok.enviar_legenda(p.get('legenda', ''), reply_to=mid)
                    except Exception:
                        pass
                except Exception as e:
                    p['erro_tiktok'] = str(e)[:200]
                    fbmsg += f'\n⚠️ TikTok: {str(e)[:150]}'
            try:
                tg('editMessageReplyMarkup', chat_id=admin(), message_id=mid, reply_markup={'inline_keyboard': []})
                tg('sendMessage', chat_id=admin(), text='✅ Publicado no Instagram.' + (f'\n{link}' if link else '') + fbmsg, reply_to_message_id=mid, disable_web_page_preview=True)
            except Exception:
                pass
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
    if pela_pagina():
        # Token de Página gerado a partir de um token de usuário de longa duração não expira. Token de usuário estendido
        # vale 60 dias: avisa no Telegram quando faltarem 14 dias ou menos.
        try:
            ig_user()
            fim = 0
            try:
                fim = ig('GET', 'debug_token', input_token=tok).get('data', {}).get('expires_at') or 0
            except Exception:
                pass
            dias = (fim - time.time()) / 86400 if fim else None
            note('notice', 'Instagram pela Página do Facebook: token válido' + (f', expira em {dias:.0f} dias.' if dias is not None else ' (a Meta não informou data de expiração).'))
            if dias is not None and dias <= 14 and os.environ.get('TELEGRAM_BOT_TOKEN') and admin():
                tg('sendMessage', chat_id=admin(), text=f'⚠️ A chave do Instagram (INSTAGRAM_TOKEN) expira em {dias:.0f} dia(s). Gere uma nova no Explorador da '
                   'Graph API (app Lectnex Publicador → estender → escolher a Página Lectnex) e atualize o segredo no GitHub.')
        except Exception as e:
            note('warning', f'Token da Página não funcionou: {e}')
            if os.environ.get('TELEGRAM_BOT_TOKEN') and admin():
                tg('sendMessage', chat_id=admin(), text='⚠️ O token da Página do Facebook (Instagram) parou de funcionar. Gere um novo e atualize o segredo '
                   'INSTAGRAM_TOKEN no GitHub. Detalhe: ' + esc(str(e)[:120]), parse_mode='HTML')
        return
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
    if pela_pagina():
        uid = ig_user()
        u = ig('GET', uid, fields='username,name')
        u.update(user_id=uid, account_type='ligada à Página do Facebook')
    else:
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
    elif cmd == 'reenviar':
        reenviar()
    elif cmd == 'facebook-apresentacao':
        facebook_propor('ig/apresentacao-facebook.txt', 'https://lectnex.com.br/assets/discord/convite-fundo.jpg', 'facebook-apresentacao')
    elif cmd == 'facebook-hoje':
        facebook_pendentes()
    elif cmd == 'facebook-perfil':
        facebook_perfil()
    elif cmd == 'facebook-teste':
        pid, _ = fb_pagina()
        note('notice', f'Página do Facebook encontrada: {pid}')
    elif cmd == 'redes':
        relatorio_redes()
    elif cmd == 'kit':
        kit_instagram(os.environ.get('KIT_DIA') or None, [c for c in os.environ.get('KIT_PECAS', '').replace(',', ' ').split() if c] or None)
