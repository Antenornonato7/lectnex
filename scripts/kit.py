"""Kit do dia: tudo que vale postar no Instagram, numa mensagem só às 19h30 no Telegram PRIVADO do dono.

Cada peça enviada pelo story_leitura.enviar() (Leitura, Antes do dado, Termo do dia, fechamento, gráfico do dia, placar)
também é registrada aqui: a imagem vai para o branch 'ao-vivo' (kit/AAAA-MM-DD/) e os dados para kit/AAAA-MM-DD/kit.json.
Às 19h30 o 'enviar' manda um álbum com as peças do dia, na ordem sugerida, e um roteiro com o link de cada sticker
e a legenda do post de feed, pronta para copiar.

Uso: python3 scripts/kit.py enviar [AAAA-MM-DD]
"""
import base64
import datetime as dt
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request
import uuid

BRT = dt.timezone(dt.timedelta(hours=-3))
REPO = os.environ.get('GITHUB_REPOSITORY', 'Antenornonato7/lectnex')
GH = f'https://api.github.com/repos/{REPO}'
# ordem sugerida de postagem e nome curto de cada peça (pelo título em negrito da mensagem original)
PECAS = [('notícia × preço', 'grafico', 'Post do feed: gráfico do dia'), ('fechamento', 'fechamento', 'Story do fechamento'),
         ('placar', 'placar', 'Story do placar da semana'), ('antes do dado', 'antes', 'Story Antes do dado'),
         ('termo', 'termo', 'Story do Termo do dia'), ('story de hoje', 'leitura', 'Story da Leitura do Dia')]


def gh(metodo, url, dados=None):
    req = urllib.request.Request(url, method=metodo, data=json.dumps(dados).encode() if dados is not None else None,
                                 headers={'Authorization': f'Bearer {os.environ["GITHUB_TOKEN"]}', 'Accept': 'application/vnd.github+json',
                                          'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'lectnex-bot'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or b'{}')


def ler(caminho):
    try:
        j = gh('GET', f'{GH}/contents/{caminho}?ref=ao-vivo')
        return base64.b64decode(j['content']), j['sha']
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None, None
        raise


def gravar(caminho, conteudo, sha=None):
    corpo = {'message': 'kit do dia', 'branch': 'ao-vivo', 'content': base64.b64encode(conteudo).decode()}
    if sha:
        corpo['sha'] = sha
    gh('PUT', f'{GH}/contents/{caminho}', corpo)


def limpar(html):
    return re.sub(r'<[^>]+>', '', html or '').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').strip()


def registrar(caminho, legenda):
    """Chamado pelo story_leitura.enviar(). Nunca derruba o envio original."""
    if not os.environ.get('GITHUB_TOKEN') or 'prévia' in (legenda or '').lower():
        return
    try:
        from PIL import Image
        hoje = dt.datetime.now(BRT).date().isoformat()
        tit = limpar((re.search(r'<b>(.*?)</b>', legenda or '') or [None, ''])[1]).lower()
        chave, nome = next(((k, n) for p, k, n in PECAS if p in tit), (re.sub(r'\W+', '-', tit)[:20] or 'peca', limpar(tit)))
        link = limpar((re.search(r'<code>(.*?)</code>', legenda or '') or [None, ''])[1])
        im = Image.open(caminho).convert('RGB')
        formato = 'story' if im.height / im.width > 1.6 else 'feed'
        buf = io.BytesIO()
        im.save(buf, 'JPEG', quality=90, optimize=True)
        gravar(f'kit/{hoje}/{chave}.jpg', buf.getvalue(), ler(f'kit/{hoje}/{chave}.jpg')[1])
        cap = ''
        if formato == 'feed' and os.environ.get('IG_LEGENDA') and os.path.exists(os.environ['IG_LEGENDA']):
            cap = open(os.environ['IG_LEGENDA'], encoding='utf-8').read().strip()
        for _ in range(3):  # outra peça pode ter gravado o kit.json ao mesmo tempo
            bruto, sha = ler(f'kit/{hoje}/kit.json')
            kit = json.loads(bruto) if bruto else {'data': hoje, 'pecas': []}
            kit['pecas'] = [p for p in kit['pecas'] if p['chave'] != chave] + [
                {'chave': chave, 'nome': nome, 'formato': formato, 'link': link, 'legenda': cap, 'hora': dt.datetime.now(BRT).strftime('%H:%M')}]
            try:
                gravar(f'kit/{hoje}/kit.json', json.dumps(kit, ensure_ascii=False, indent=1).encode(), sha)
                break
            except urllib.error.HTTPError as e:
                if e.code not in (409, 422):
                    raise
        print(f'Kit do dia: {nome} registrado.')
    except Exception as e:
        print(f'::warning::Kit do dia: não registrei a peça ({e.__class__.__name__}: {str(e)[:80]})')


def tg_album(fotos, legenda):
    tok, chat = os.environ['TELEGRAM_BOT_TOKEN'].strip(), os.environ['TELEGRAM_ADMIN_CHAT_ID'].strip()
    b = uuid.uuid4().hex
    media = [{'type': 'photo', 'media': f'attach://f{i}'} for i in range(len(fotos))]
    media[0]['caption'], media[0]['parse_mode'] = legenda, 'HTML'
    partes = [('chat_id', chat), ('media', json.dumps(media, ensure_ascii=False))]
    corpo = b''.join(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in partes)
    for i, f in enumerate(fotos):
        corpo += f'--{b}\r\nContent-Disposition: form-data; name="f{i}"; filename="f{i}.jpg"\r\nContent-Type: image/jpeg\r\n\r\n'.encode() + f + b'\r\n'
    corpo += f'--{b}--\r\n'.encode()
    metodo = 'sendMediaGroup' if len(fotos) > 1 else 'sendPhoto'
    if len(fotos) == 1:  # sendPhoto não aceita 'media'
        corpo = b''.join(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in (('chat_id', chat), ('caption', legenda), ('parse_mode', 'HTML')))
        corpo += f'--{b}\r\nContent-Disposition: form-data; name="photo"; filename="f.jpg"\r\nContent-Type: image/jpeg\r\n\r\n'.encode() + fotos[0] + f'\r\n--{b}--\r\n'.encode()
    req = urllib.request.Request(f'https://api.telegram.org/bot{tok}/{metodo}', data=corpo, headers={'Content-Type': f'multipart/form-data; boundary={b}'})
    urllib.request.urlopen(req, timeout=90).read()


def tg_texto(texto, html=True):
    tok, chat = os.environ['TELEGRAM_BOT_TOKEN'].strip(), os.environ['TELEGRAM_ADMIN_CHAT_ID'].strip()
    dados = {'chat_id': chat, 'text': texto, 'disable_web_page_preview': True, **({'parse_mode': 'HTML'} if html else {})}
    req = urllib.request.Request(f'https://api.telegram.org/bot{tok}/sendMessage', data=json.dumps(dados).encode(), headers={'Content-Type': 'application/json'})
    urllib.request.urlopen(req, timeout=40).read()


def enviar(dia=None):
    dia = dia or dt.datetime.now(BRT).date().isoformat()
    bruto, _ = ler(f'kit/{dia}/kit.json')
    if not bruto:
        print('Kit do dia: nenhuma peça registrada hoje.')
        return
    kit = json.loads(bruto)
    ordem = {k: i for i, (_, k, _) in enumerate(PECAS)}
    pecas = sorted(kit['pecas'], key=lambda p: ordem.get(p['chave'], 99))
    fotos, ok = [], []
    for p in pecas[:10]:
        img, _ = ler(f'kit/{dia}/{p["chave"]}.jpg')
        if img:
            fotos.append(img)
            ok.append(p)
    if not ok:
        return
    d = dt.date.fromisoformat(dia)
    dias = ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo']
    feed = [p for p in ok if p['formato'] == 'feed']
    linhas = [f'🧰 <b>Kit do dia</b> · {dias[d.weekday()]} {d:%d/%m} · {len(ok)} peça{"s" if len(ok) > 1 else ""} para o Instagram', '']
    for i, p in enumerate(ok, 1):
        onde = 'feed' if p['formato'] == 'feed' else 'stories'
        extra = f' · sticker de link: <code>{p["link"]}</code>' if p.get('link') and onde == 'stories' else (' · legenda logo abaixo' if p.get('legenda') else '')
        linhas.append(f'{i}. <b>{p["nome"]}</b> ({onde}){extra}')
    linhas += ['', 'Ordem sugerida: o post de feed primeiro, depois os stories na ordem da lista. As imagens estão no álbum, na mesma ordem.']
    tg_album(fotos, '\n'.join(linhas)[:1020])
    for p in feed:
        if p.get('legenda'):
            tg_texto(f'📋 Legenda do feed ({p["nome"]}):', html=False)
            tg_texto(p['legenda'], html=False)
    print(f'Kit do dia enviado: {len(ok)} peça(s).')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'enviar':
        enviar(sys.argv[2] if len(sys.argv) > 2 else None)
