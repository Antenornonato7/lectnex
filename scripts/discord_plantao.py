"""Plantão do Discord da Lectnex (roda algumas vezes por dia pelo GitHub Actions).

1. Responde as dúvidas novas do fórum #duvidas que ainda ninguém respondeu, com o Claude (precisa do segredo
   ANTHROPIC_API_KEY; sem ele, só lista as dúvidas pendentes). Sempre educacional, nunca recomenda compra ou venda.
2. Posta no canal privado #log-moderacao um resumo do período: mensagens por canal, tópicos novos, o que foi
   respondido e o que precisa de gente.
Para ler o texto das mensagens, o bot precisa da opção "Message Content Intent" ligada no portal do Discord.
Nada vai para o log público do GitHub além de contagens.
"""
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'coletor'))
import discord_post as dc  # noqa: E402

GUILD = dc.GUILD
CHAVE = os.environ.get('ANTHROPIC_API_KEY', '').strip()
MODELO = os.environ.get('PLANTAO_MODELO', 'claude-sonnet-5-5')
HORAS = float(os.environ.get('PLANTAO_HORAS', '6'))  # janela do resumo
EPOCA = 1420070400000
SITE = 'https://lectnex.com.br/'
SISTEMA = f"""Você é o assistente do plantão da comunidade Lectnex no Discord, um projeto educacional sobre o mercado brasileiro
(mini índice WIN, mini dólar WDO, juros, ações, FIIs e renda fixa). Responda em português do Brasil, em tom de professor paciente,
em no máximo 180 palavras, com markdown simples do Discord.

Regras que você nunca quebra:
- Nada de recomendação de compra, venda ou manutenção de ativo, preço-alvo, "entra aqui" ou "vale a pena comprar X". Se pedirem,
  diga com gentileza que a comunidade é educacional e explique COMO a pessoa pode analisar sozinha.
- Não prometa ganho nem diga o que o mercado vai fazer.
- Imposto e questões legais: explique a regra geral e indique conferir com um contador ou a Receita.
- Se não souber ou a pergunta depender de dado de hoje, diga isso e indique onde olhar.
- Quando ajudar, indique uma página do site: calculadora de risco e posição {SITE}futuros.html#risco ·
  Diário de Trades {SITE}futuros.html#diario · IR day trade {SITE}calculadora-ir-day-trade.html · glossário {SITE}glossario.html ·
  Academia {SITE}laboratorio.html?tab=academia · juros {SITE}macro.html · dias que mexeram nos juros {SITE}juros/ ·
  renda fixa e simuladores {SITE}laboratorio.html?tab=rf.
Termine sempre com a linha: *Conteúdo educacional, não é recomendação de investimento.*"""


def ts(snowflake):
    return dt.datetime.fromtimestamp(((int(snowflake) >> 22) + EPOCA) / 1000, dt.timezone.utc)


def claude(pergunta):
    corpo = {'model': MODELO, 'max_tokens': 700, 'system': SISTEMA, 'messages': [{'role': 'user', 'content': pergunta[:4000]}]}
    req = urllib.request.Request('https://api.anthropic.com/v1/messages', data=json.dumps(corpo).encode(), method='POST',
                                 headers={'x-api-key': CHAVE, 'anthropic-version': '2023-06-01', 'content-type': 'application/json'})
    with urllib.request.urlopen(req, timeout=90) as r:
        j = json.load(r)
    return ''.join(b.get('text', '') for b in j.get('content', []) if b.get('type') == 'text').strip()


def main():
    if not dc.TOKEN:
        sys.exit('::error::Falta DISCORD_BOT_TOKEN.')
    eu = dc._req('GET', '/users/@me')
    canais = dc._req('GET', f'/guilds/{GUILD}/channels')
    nome = {c['id']: c['name'] for c in canais}
    desde = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=HORAS)
    sem_texto = False

    # 1. dúvidas do fórum
    duvidas = next((c for c in canais if c['name'] == 'duvidas'), None)
    ativos = dc._req('GET', f'/guilds/{GUILD}/threads/active').get('threads', [])
    topicos_novos = [t for t in ativos if ts(t['id']) >= desde]
    respondidas, pendentes = [], []
    for t in [t for t in ativos if duvidas and t.get('parent_id') == duvidas['id']]:
        if ts(t['id']) < dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=48):
            continue
        msgs = dc._req('GET', f'/channels/{t["id"]}/messages?limit=20')
        if any(m['author']['id'] == eu['id'] for m in msgs):
            continue
        autor = next((m['author']['id'] for m in msgs if m['id'] == t['id']), None)
        if any(m['author']['id'] != autor and not m['author'].get('bot') for m in msgs):
            continue  # alguém da comunidade já respondeu
        texto = '\n'.join(m.get('content', '') for m in sorted(msgs, key=lambda m: int(m['id'])) if m['author']['id'] == autor).strip()
        if not texto:
            sem_texto = True
        if not CHAVE or not texto:
            pendentes.append(t)
            continue
        try:
            resp = claude(f'Título do tópico: {t["name"]}\n\nPergunta:\n{texto}')
            dc._req('POST', f'/channels/{t["id"]}/messages', {'content': ('🤖 **Plantão Lectnex**\n' + resp)[:1990], 'allowed_mentions': {'parse': []},
                                                               'message_reference': {'message_id': t['id'], 'fail_if_not_exists': False}, 'flags': 4})
            respondidas.append(t)
        except Exception as e:
            print(f'::warning::Não respondi um tópico: {e}')
            pendentes.append(t)

    # 2. movimento por canal (só contagem)
    mov = {}
    for c in canais:
        if c['type'] not in (0, 5) or c['name'] in ('log-moderacao',):
            continue
        try:
            msgs = dc._req('GET', f'/channels/{c["id"]}/messages?limit=100')
        except Exception:
            continue
        n = sum(1 for m in msgs if ts(m['id']) >= desde and not m['author'].get('bot'))
        if n:
            mov[c['name']] = n
    g = dc._req('GET', f'/guilds/{GUILD}?with_counts=true')

    # 3. resumo no canal privado da equipe
    hora = dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).strftime('%d/%m %Hh%M')
    L = [f'🛡️ **Plantão · {hora}** (últimas {HORAS:g} h) · {g.get("approximate_member_count", "?")} membros']
    L.append('**Mensagens:** ' + (' · '.join(f'#{k} {v}' for k, v in sorted(mov.items(), key=lambda x: -x[1])) or 'nenhuma'))
    if topicos_novos:
        L.append('**Tópicos novos:** ' + ' · '.join(f'<#{t["id"]}> ({nome.get(t.get("parent_id"), "?")})' for t in topicos_novos[:10]))
    if respondidas:
        L.append('**Respondi:** ' + ' · '.join(f'<#{t["id"]}>' for t in respondidas))
    if pendentes:
        motivo = 'falta a chave da API' if not CHAVE else 'sem texto legível' if sem_texto else 'falha ao responder'
        L.append(f'**Precisa de alguém ({motivo}):** ' + ' · '.join(f'<#{t["id"]}>' for t in pendentes))
    if sem_texto:
        L.append('⚠️ Não consigo ler o texto das mensagens: ligue "Message Content Intent" em discord.com/developers → Bot.')
    calmo = not (mov or topicos_novos or respondidas or pendentes)
    if calmo and os.environ.get('SO_SE_HOUVER') == '1':
        print('Período calmo: sem resumo.')
    else:
        dc.postar('log-moderacao', md='\n'.join(L))
    print(f'Mensagens em {len(mov)} canal(is) · {len(topicos_novos)} tópico(s) novo(s) · {len(respondidas)} respondida(s) · {len(pendentes)} pendente(s)')


if __name__ == '__main__':
    main()
