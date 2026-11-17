"""Desafio diário SUBIU ou CAIU no Discord, com placar semanal.

postar mercado.json  → (fechamento, ~19h15) em #desafio-diario: as mesmas 3 manchetes do Reels-desafio, cada uma com 🟢 e 🔴 para votar.
revelar              → (21h40) lê os votos, mostra as respostas e quem acertou, soma os pontos da semana; no último pregão da
                       semana publica o ranking e zera.
Estado no branch ao-vivo: discord/desafio.json. Vale 1 ponto por rodada certa (quem vota nas duas cores não pontua).
"""
import datetime as dt
import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import discord_post as dc  # noqa: E402
from instagram import gh_gravar, gh_ler, note  # noqa: E402

CANAL = 'desafio-diario'
ESTADO = 'discord/desafio.json'
SOBE, CAI = '🟢', '🔴'
SITE = 'https://lectnex.com.br/hoje.html'


def canal_desafio():
    """Id de #desafio-diario; cria ao lado de #fechamento (só a equipe escreve, todos reagem) se ainda não existir."""
    cid = dc.canal(CANAL)
    if cid:
        return cid
    chs = dc._req('GET', f'/guilds/{dc.GUILD}/channels')
    ref = next((c for c in chs if c['name'] == 'fechamento'), None)
    eu = dc._req('GET', '/users/@me')['id']
    ov = [o for o in (ref or {}).get('permission_overwrites', [])]
    ov.append({'id': eu, 'type': 1, 'allow': str(sum(1 << b for b in (6, 10, 11, 13, 14, 15, 16))), 'deny': '0'})
    c = dc._req('POST', f'/guilds/{dc.GUILD}/channels', {
        'name': CANAL, 'type': 0, 'parent_id': (ref or {}).get('parent_id'), 'permission_overwrites': ov,
        'topic': 'Desafio SUBIU ou CAIU: vote com 🟢 ou 🔴 em cada manchete. Resposta às 21h40, ranking toda sexta. Educacional.'})
    dc._canais = None
    return c['id']


def postar(arq):
    from reel_quiz import Quiz
    m = json.load(open(arq, encoding='utf-8'))
    if not (m.get('ibov') or m.get('dolar')):
        return note('notice', 'Desafio Discord: sem série do dia.')
    q = Quiz(m)
    if len(q.mks) < 2:
        return note('notice', 'Desafio Discord: menos de 2 manchetes.')
    est, sha = gh_ler(ESTADO)
    est = est or {}
    if (est.get('hoje') or {}).get('data') == q.dia.isoformat():
        return note('notice', 'Desafio Discord: o de hoje já foi postado.')
    cid = canal_desafio()
    ativo = 'Ibovespa' if q.k == 'ibov' else 'dólar'
    dc._req('POST', f'/channels/{cid}/messages', {'content': (
        f'🎯 **Desafio do dia · {q.dia:%d/%m}**\n{len(q.mks)} manchetes reais de hoje. O **{ativo}** subiu ou caiu nos 30 minutos seguintes?\n'
        f'Vote em cada uma: {SOBE} subiu · {CAI} caiu. **Resposta às 21h40**, ranking da semana na sexta.'), 'flags': 4})
    rodadas = []
    for i, mk in enumerate(q.mks, 1):
        msg = dc._req('POST', f'/channels/{cid}/messages', {'content': f'**Rodada {i}** · {mk["hora"]} · {mk.get("fonte", "")}\n> {mk["titulo"]}', 'flags': 4,
                                                            'allowed_mentions': {'parse': []}})
        for e in (SOBE, CAI):
            dc._req('PUT', f'/channels/{cid}/messages/{msg["id"]}/reactions/{urllib.parse.quote(e)}/@me')
        rodadas.append({'msg': msg['id'], 'certo': SOBE if mk[q.campo] > 0 else CAI, 'var': mk[q.campo], 'hora': mk['hora']})
    est['hoje'] = {'data': q.dia.isoformat(), 'canal': cid, 'ativo': ativo, 'rodadas': rodadas, 'revelado': False}
    gh_gravar(ESTADO, json.dumps(est, ensure_ascii=False, indent=1).encode(), sha, msg='discord: desafio')
    note('notice', f'Desafio Discord postado: {len(rodadas)} rodadas.')


def votos(cid, mid, emoji):
    us = dc._req('GET', f'/channels/{cid}/messages/{mid}/reactions/{urllib.parse.quote(emoji)}?limit=100') or []
    return {u['id']: (u.get('global_name') or u.get('username')) for u in us if not u.get('bot')}


def pct(v):
    return ('+' if v > 0 else '−') + f'{abs(v):.2f}%'.replace('.', ',')


def ultimo_pregao_semana(hoje):
    try:
        cal = json.load(open(os.path.join(os.path.dirname(__file__), '..', 'data', 'calendario.json'), encoding='utf-8'))
        feriados = {e['data'] for e in cal.get('eventos', []) if e.get('tipo') == 'feriado'}
    except Exception:
        feriados = set()
    d = hoje + dt.timedelta(days=1)
    while d.weekday() < 5:
        if d.isoformat() not in feriados:
            return False
        d += dt.timedelta(days=1)
    return True


def revelar():
    est, sha = gh_ler(ESTADO)
    h = (est or {}).get('hoje')
    if not h or h.get('revelado'):
        return note('notice', 'Desafio Discord: nada para revelar.')
    cid, hoje = h['canal'], dt.date.fromisoformat(h['data'])
    semana = f'{hoje.isocalendar()[0]}-W{hoje.isocalendar()[1]:02d}'
    if est.get('semana') != semana:
        est['semana'], est['pontos'] = semana, {}
    acertos, nomes, linhas = {}, {}, []
    for i, r in enumerate(h['rodadas'], 1):
        s, c = votos(cid, r['msg'], SOBE), votos(cid, r['msg'], CAI)
        nomes.update(s); nomes.update(c)
        certos = (s if r['certo'] == SOBE else c).keys() - (c if r['certo'] == SOBE else s).keys()
        for u in certos:
            acertos[u] = acertos.get(u, 0) + 1
        tot = len(s.keys() | c.keys())
        linhas.append(f'**Rodada {i}** ({r["hora"]}): {r["certo"]} {"SUBIU" if r["certo"] == SOBE else "CAIU"} · {pct(r["var"])} em 30 min'
                      + (f' · {len(certos)} de {tot} acertaram' if tot else ''))
    for u in nomes:
        p = est['pontos'].setdefault(u, {'nome': nomes[u], 'pts': 0, 'dias': 0})
        p['nome'], p['pts'], p['dias'] = nomes[u], p['pts'] + acertos.get(u, 0), p['dias'] + 1
    n = len(h['rodadas'])
    gabarito = [nomes[u] for u, k in sorted(acertos.items(), key=lambda x: -x[1]) if k == n]
    txt = [f'✅ **Respostas do desafio de {hoje:%d/%m}** ({h["ativo"]})', *linhas, '']
    if nomes:
        txt.append(('🏆 Gabaritaram: ' + ', '.join(gabarito[:15])) if gabarito else 'Ninguém gabaritou hoje. Amanhã tem mais!')
    else:
        txt.append('Ninguém votou hoje. Amanhã às 19h15 tem desafio novo: vote com 🟢 ou 🔴.')
    txt.append(f'Gráfico com as manchetes no horário: <{SITE}>\n*A variação depois da manchete não prova que ela foi a causa. Educacional.*')
    dc._req('POST', f'/channels/{cid}/messages', {'content': '\n'.join(txt)[:1990], 'flags': 4, 'allowed_mentions': {'parse': []}})
    if ultimo_pregao_semana(hoje) and est['pontos']:
        top = sorted(est['pontos'].values(), key=lambda p: (-p['pts'], -p['dias']))[:10]
        med = ['🥇', '🥈', '🥉'] + ['▫️'] * 7
        rk = [f'{med[i]} **{p["nome"]}**: {p["pts"]} ponto(s) em {p["dias"]} dia(s)' for i, p in enumerate(top)]
        dc._req('POST', f'/channels/{cid}/messages', {'content': '\n'.join([f'📊 **Ranking da semana** ({semana[-3:]})', *rk, '',
                                                                              'Segunda começa do zero. Chame quem opera com você!']), 'flags': 4,
                                                       'allowed_mentions': {'parse': []}})
        est['ranking_anterior'] = top
    h['revelado'] = True
    gh_gravar(ESTADO, json.dumps(est, ensure_ascii=False, indent=1).encode(), sha, msg='discord: respostas')
    note('notice', f'Desafio Discord revelado: {len(nomes)} participante(s).')


if __name__ == '__main__':
    if not dc.TOKEN:
        print('::notice::Sem DISCORD_BOT_TOKEN.'); sys.exit(0)
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'revelar'
    try:
        postar(sys.argv[2]) if cmd == 'postar' else revelar()
    except Exception as e:
        print(f'::warning::Desafio Discord: {e.__class__.__name__}: {str(e)[:200]}')
