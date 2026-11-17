"""Desafio semanal do Simulador de pregão no Discord (#ranking-simulador).

semana  → (segunda 09h35) escolhe o "pregão da semana" (um dia gravado em data/dias, alternando WIN e WDO) e posta o link.
ranking → (sexta 18h30) lê os resultados colados no canal desde o post, confere o código de cada um e publica o ranking.
quem    → mostra o id do robô (o site usa para montar a menção no texto "Copiar para o Discord").

O site gera, no fim do pregão da semana, um texto com o código "LX·<resultado>·<operações>·<verificação>". Quem bateu o limite de
perda não recebe código (fica fora do ranking). A verificação é um FNV-1a de "lectnex|dia|ativo|resultado|operações" em base 36,
igual ao do simulador.html: não é segurança, só evita digitar um número qualquer.
Os textos colados mencionam o robô, então o Discord entrega o conteúdo mesmo sem a permissão "Message Content".
Estado no branch ao-vivo: discord/simulador.json.
"""
import datetime as dt
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
import discord_post as dc  # noqa: E402
from instagram import BRT, gh_gravar, gh_ler, note  # noqa: E402

CANAL = 'ranking-simulador'
ESTADO = 'discord/simulador.json'
SITE = 'https://lectnex.com.br/simulador.html'
CODIGO = re.compile(r'LX·([+\-−]?\d+)·(\d+)·([0-9a-z]{6})', re.I)


def verif(dia, ativo, r, ops):
    h = 0x811c9dc5
    for ch in f'lectnex|{dia}|{ativo}|{r}|{ops}'.encode():
        h ^= ch
        h = (h * 0x01000193) & 0xffffffff
    s, n = '', h
    while n:
        n, k = divmod(n, 36)
        s = '0123456789abcdefghijklmnopqrstuvwxyz'[k] + s
    return (s or '0').rjust(6, '0')[-6:]


def canal_ranking():
    cid = dc.canal(CANAL)
    if cid:
        return cid
    chs = dc._req('GET', f'/guilds/{dc.GUILD}/channels')
    ref = next((c for c in chs if c['name'] == 'desafio-diario'), None) or next((c for c in chs if c['name'] == 'fechamento'), None)
    eu = dc._req('GET', '/users/@me')['id']
    c = dc._req('POST', f'/guilds/{dc.GUILD}/channels', {
        'name': CANAL, 'type': 0, 'parent_id': (ref or {}).get('parent_id'), 'rate_limit_per_user': 30,
        'permission_overwrites': [{'id': eu, 'type': 1, 'allow': str(sum(1 << b for b in (6, 10, 11, 13, 14, 15, 16))), 'deny': '0'}],
        'topic': 'Desafio semanal do Simulador de pregão: jogue o pregão da semana e cole aqui o texto "Copiar para o Discord". Ranking na sexta. Dinheiro fictício, educacional.'})
    dc._canais = None
    return c['id']


def semana():
    hoje = dt.datetime.now(BRT).date()
    est, sha = gh_ler(ESTADO)
    est = est or {}
    sem = f'{hoje.isocalendar()[0]}-W{hoje.isocalendar()[1]:02d}'
    if est.get('semana') == sem:
        return note('notice', 'Simulador: pregão da semana já postado.')
    raiz = os.path.join(os.path.dirname(__file__), '..')
    dias = json.load(open(os.path.join(raiz, 'data', 'dias', 'indice.json'), encoding='utf-8')).get('dias', [])
    usados = set(est.get('usados', []))
    candidatos = [d for d in dias[:-1] if d not in usados] or dias[:-1] or dias  # nunca o dia mais recente (todo mundo lembra)
    dia = candidatos[hoje.isocalendar()[1] % len(candidatos)]
    ativo = 'win' if hoje.isocalendar()[1] % 2 == 0 else 'wdo'
    cid = canal_ranking()
    link = f'{SITE}?dia={dia}&ativo={ativo}&semana=1'
    msg = dc._req('POST', f'/channels/{cid}/messages', {'content': (
        f'🎮 **Pregão da semana** ({"WIN · mini índice" if ativo == "win" else "WDO · mini dólar"})\n'
        f'Jogue o mesmo dia que todo mundo, às cegas: <{link}>\n\n'
        '**Como entrar no ranking:** no fim do pregão, toque em **COPIAR PARA O DISCORD** e cole aqui. '
        'Vale o seu melhor resultado da semana; quem bate o limite de perda fica de fora. **Ranking na sexta às 18h30.**\n'
        '*Dinheiro fictício. Conteúdo educacional, não é recomendação.*'), 'flags': 4})
    for rota in (f'/channels/{cid}/messages/pins/{msg["id"]}', f'/channels/{cid}/pins/{msg["id"]}'):
        try:
            dc._req('PUT', rota)
            break
        except Exception:
            continue
    est.update(semana=sem, dia=dia, ativo=ativo, msg=msg['id'], canal=cid, publicado=False, usados=sorted(usados | {dia})[-60:])
    gh_gravar(ESTADO, json.dumps(est, ensure_ascii=False, indent=1).encode(), sha, msg='discord: pregão da semana')
    try:
        dc.postar('avisos', md=f'🎮 Saiu o **pregão da semana** no simulador. Jogue e entre no ranking em #{CANAL}: <{link}>')
    except Exception:
        pass
    note('notice', f'Simulador: pregão da semana {dia} ({ativo}).')
    try:
        post_redes(dia, ativo, link)
    except Exception as e:
        note('warning', f'Simulador: post das redes não gerado ({e.__class__.__name__}: {str(e)[:120]})')


def post_redes(dia, ativo, link):
    """Imagem "Você teria lucrado neste pregão?" no Telegram privado com botão de publicar (Instagram + Facebook) e o texto do X."""
    import tempfile
    import instagram as ig
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
    from simulador_post import gerar, textos
    pasta = tempfile.mkdtemp()
    img, arq = os.path.join(pasta, 'post.jpg'), os.path.join(pasta, 'legenda.txt')
    gerar(dia, ativo, img)
    leg, x = textos(ativo, link.replace('&semana=1', ''))
    open(arq, 'w', encoding='utf-8').write(leg)
    with open(img, 'rb') as f:
        _foto(ig, f.read(), 'Prévia: post do Simulador (pregão da semana)')
    if os.environ.get('INSTAGRAM_TOKEN', '').strip():
        ig.propor('simulador', arq, [img])
    else:
        ig.tg('sendMessage', chat_id=ig.admin(), text=leg, disable_web_page_preview=True)
    ig.enviar_x(x)


def _foto(ig, dados, legenda):
    """sendPhoto com arquivo (multipart): o Telegram recebe a imagem sem precisar de URL pública."""
    import uuid
    import urllib.request
    b = uuid.uuid4().hex
    corpo = (f'--{b}\r\nContent-Disposition: form-data; name="chat_id"\r\n\r\n{ig.admin()}\r\n'
             f'--{b}\r\nContent-Disposition: form-data; name="caption"\r\n\r\n{legenda}\r\n'
             f'--{b}\r\nContent-Disposition: form-data; name="photo"; filename="post.jpg"\r\nContent-Type: image/jpeg\r\n\r\n').encode() + dados + f'\r\n--{b}--\r\n'.encode()
    tok = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
    req = urllib.request.Request(f'https://api.telegram.org/bot{tok}/sendPhoto', data=corpo, headers={'Content-Type': f'multipart/form-data; boundary={b}'})
    urllib.request.urlopen(req, timeout=60).read()


def mensagens(cid, depois):
    tudo, ult = [], depois
    for _ in range(20):
        lote = dc._req('GET', f'/channels/{cid}/messages?after={ult}&limit=100') or []
        if not lote:
            break
        tudo += lote
        ult = max(lote, key=lambda m: int(m['id']))['id']
        if len(lote) < 100:
            break
    return tudo


def ranking():
    est, sha = gh_ler(ESTADO)
    if not est or est.get('publicado') or not est.get('msg'):
        return note('notice', 'Simulador: nada para ranquear.')
    melhores = {}
    for m in mensagens(est['canal'], est['msg']):
        if m['author'].get('bot'):
            continue
        for r, ops, h in CODIGO.findall(m.get('content') or ''):
            r = int(r.replace('−', '-'))
            if verif(est['dia'], est['ativo'], r, int(ops)) != h.lower():
                continue
            u = m['author']
            if u['id'] not in melhores or r > melhores[u['id']]['r']:
                melhores[u['id']] = {'nome': u.get('global_name') or u.get('username'), 'r': r, 'ops': int(ops)}
    top = sorted(melhores.values(), key=lambda x: (-x['r'], x['ops']))[:10]
    med = ['🥇', '🥈', '🥉'] + ['▫️'] * 7
    brl = lambda v: ('+' if v > 0 else '−' if v < 0 else '') + 'R$ ' + f'{abs(v):,}'.replace(',', '.')
    d = dt.date.fromisoformat(est['dia'])
    linhas = [f'🏁 **Ranking do pregão da semana** ({est["ativo"].upper()}, pregão de {d:%d/%m})']
    linhas += [f'{med[i]} **{x["nome"]}**: {brl(x["r"])} em {x["ops"]} operação(ões)' for i, x in enumerate(top)] or ['Ninguém postou resultado nesta semana.']
    linhas += ['', 'Segunda sai o próximo pregão. Jogue também os outros dias em <' + SITE + '>.', '*Dinheiro fictício. Educacional.*']
    dc._req('POST', f'/channels/{est["canal"]}/messages', {'content': '\n'.join(linhas)[:1990], 'flags': 4, 'allowed_mentions': {'parse': []}})
    est['publicado'] = True
    est.setdefault('historico', []).append({'semana': est['semana'], 'dia': est['dia'], 'ativo': est['ativo'], 'participantes': len(melhores), 'top': top[:3]})
    est['historico'] = est['historico'][-30:]
    gh_gravar(ESTADO, json.dumps(est, ensure_ascii=False, indent=1).encode(), sha, msg='discord: ranking do simulador')
    note('notice', f'Simulador: ranking com {len(melhores)} participante(s).')


if __name__ == '__main__':
    if not dc.TOKEN:
        print('::notice::Sem DISCORD_BOT_TOKEN.'); sys.exit(0)
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'semana'
    try:
        if cmd == 'quem':
            note('notice', 'Robô: ' + dc._req('GET', '/users/@me')['id'])
        elif cmd == 'post':
            est, _ = gh_ler(ESTADO)
            post_redes(est['dia'], est['ativo'], f'{SITE}?dia={est["dia"]}&ativo={est["ativo"]}')
        elif cmd == 'ranking':
            ranking()
        else:
            semana()
    except Exception as e:
        print(f'::warning::Simulador Discord: {e.__class__.__name__}: {str(e)[:200]}')
