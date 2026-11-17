"""Servidor Discord da Lectnex. Nunca apaga nada.

Modos: ler (estado atual) · simular (mostra o que montar faria, sem mudar nada) · montar (cria o que falta, renomeia, ajusta).
Uso: DISCORD_BOT_TOKEN=... python3 scripts/discord_servidor.py ler|simular|montar
O log do GitHub Actions deste repositório é público: aqui só saem nomes de canais e cargos e contagens,
nunca nomes de membros nem conteúdo de mensagens.
"""
import json
import os
import time
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
        if e.code == 429:  # limite de ritmo do Discord: espera e tenta de novo
            time.sleep(float(json.loads(e.read() or b'{}').get('retry_after', 2)) + 0.5)
            return api(metodo, caminho, corpo)
        raise SystemExit(f'::error::Discord {metodo} {caminho}: HTTP {e.code} {e.read()[:300].decode(errors="replace")}')


def perms_txt(v):
    v = int(v)
    return ', '.join(n for b, n in PERMS.items() if v >> b & 1) or '—'


def ler():
    eu = api('GET', '/users/@me')
    servidores = api('GET', '/users/@me/guilds')
    print(f'Bot {eu["username"]} está em {len(servidores)} servidor(es): ' + ', '.join(f'{x["name"]} ({x["id"]})' for x in servidores))
    if GUILD not in [x['id'] for x in servidores]:
        sys.exit(f'::error::O bot não está no servidor {GUILD}. Abra o link de convite e autorize no servidor Lectnex.')
    g = api('GET', f'/guilds/{GUILD}?with_counts=true')
    canais = api('GET', f'/guilds/{GUILD}/channels')
    cargos = sorted(api('GET', f'/guilds/{GUILD}/roles'), key=lambda r: -r['position'])
    print(f'Bot: {eu["username"]} · Servidor: {g["name"]} · ~{g.get("approximate_member_count")} membros '
          f'({g.get("approximate_presence_count")} online)')
    print(f'Impulsos: {g.get("premium_subscription_count", 0)} (nível {g.get("premium_tier", 0)}) · tag do servidor precisa de 3')
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


# ---------------------------------------------------------------- montagem (plano do documento "Servidor Discord Lectnex: organização")
B = lambda *bits: str(sum(1 << b for b in bits))
VER, ENVIAR, GER_MSG, LINKS, ARQ, HIST, REAGIR = 10, 11, 13, 14, 15, 16, 6
TOPICO, MSG_TOPICO, GER_TOPICOS = 35, 38, 34
EQUIPE = 'equipe'  # só equipe e robô escrevem
CATEGORIAS = [
    ('COMECE AQUI', [('boas-vindas', 0, EQUIPE, 'O que é a Lectnex e por onde começar'),
                     ('regras', 0, EQUIPE, 'Regras e aviso legal'),
                     ('avisos', 5, EQUIPE, 'Novidades do site e da comunidade'),
                     ('apresente-se', 0, None, 'Conte o que você opera e há quanto tempo')]),
    ('MERCADO', [('leitura-do-dia', 0, EQUIPE, 'Leitura do Dia às 7h40 (automático)'),
                 ('agenda-e-alertas', 0, EQUIPE, 'Agenda do dia e dados acima ou abaixo do esperado (automático)'),
                 ('fechamento', 0, EQUIPE, 'Fechamento e gráfico do dia (automático)'),
                 ('juros-e-dolar', 0, EQUIPE, 'Dias que mexeram nos juros e saltos fortes (automático)'),
                 ('desafio-diario', 0, EQUIPE, 'Desafio SUBIU ou CAIU: vote com reações, resposta às 21h40, ranking na sexta')]),
    ('PREGÃO', [('win-mini-indice', 0, 10, 'Mini índice durante o pregão. Conteúdo educacional, sem recomendação.'),
                ('wdo-mini-dolar', 0, 10, 'Mini dólar durante o pregão. Conteúdo educacional, sem recomendação.')]),
    ('INVESTIMENTOS', [('acoes-e-dividendos', 0, None, 'Ações para o longo prazo: resultados, dividendos e JCP. Educacional, sem recomendação.'),
                       ('fundos-imobiliarios', 0, None, 'FIIs: rendimentos, vacância, tijolo × papel. Educacional, sem recomendação.'),
                       ('renda-fixa', 0, None, 'CDB, LCI/LCA, Tesouro Direto, debêntures: taxas, prazos e IR. Educacional, sem recomendação.'),
                       ('carteiras', 15, None, 'Cada membro mostra como monta a própria carteira e por quê. Ninguém recomenda ativo para ninguém.')]),
    ('ESTUDO', [('duvidas', 15, None, 'Cada dúvida vira um tópico. Use as etiquetas.'),
                ('diario-de-trades', 15, None, 'Um tópico por membro para registrar o próprio dia'),
                ('material', 0, EQUIPE, 'Lições da Academia, calculadoras e guias do site')]),
    ('COMUNIDADE', [('off-topic', 0, None, 'Conversa livre'),
                    ('sugestoes-pro-site', 0, None, 'Ideias e erros encontrados no site')]),
    ('AO VIVO', [('Sala do pregão', 2, None, None), ('Sala de investimentos', 2, None, None)]),
]
ETIQUETAS = {'duvidas': ['Iniciante', 'Risco', 'IR', 'Plataforma', 'WIN', 'WDO', 'Investimentos'], 'diario-de-trades': ['WIN', 'WDO', 'Ações'],
             'carteiras': ['Dividendos', 'FIIs', 'Renda fixa', 'Longo prazo', 'Aposentadoria']}
RENOMEAR = {'rules': ('regras', 'COMECE AQUI'), 'general': ('off-topic', 'COMUNIDADE'), 'acoes-b3': ('acoes-e-dividendos', 'INVESTIMENTOS')}   # canais que já existem
RENOMEAR_VOZ = {'general': ('Sala do pregão', 'AO VIVO')}
RENOMEAR_CAT = {'text channels': 'COMUNIDADE', 'voice channels': 'AO VIVO'}
CARGOS = [('Moderador', 0x00B4A2, True, B(VER, ENVIAR, GER_MSG, HIST, LINKS, ARQ, REAGIR, GER_TOPICOS, TOPICO, MSG_TOPICO)),
          ('Trader WIN', 0xF39200, False, '0'), ('Trader WDO', 0x3B82F6, False, '0'), ('Investidor', 0x8B5CF6, False, '0'), ('Fundador', 0x009988, True, '0')]
RENOMEAR_CARGO = {'Ações': 'Investidor'}
GOLPE = ['sinal vip', 'sala de sinais', 'sala vip', 'lucro garantido', 'renda extra', 'chama no privado', 'chama no pv', 'me chama no pv',
         'me chama no whats', 'mentoria paga', 'robô que ganha', 'robo que ganha', 'dobra a banca', 'dobrar a banca', 'ganhe r$', 'investimento garantido']
LINKS_BLOQ = ['*http*', '*discord.gg/*', '*t.me/*', '*wa.me/*', '*bit.ly/*']
LINKS_OK = ['*lectnex.com.br*', '*b3.com.br*', '*bcb.gov.br*', '*ibge.gov.br*', '*gov.br*', '*tradingview.com*']
REGRAS = """**Regras do servidor Lectnex**

1. **Aqui é estudo, não é recomendação.** Nada neste servidor é indicação de compra ou venda. Cada um decide e responde pelas próprias operações.
2. **Proibido vender sinal, curso, mentoria ou robô.** Também não vale "me chama no privado" para isso.
3. **Nada de prometer ganho.** Print de lucro sem contexto, "ganhe R$ 500 por dia" e parecidos são apagados.
4. **Respeito acima de tudo.** Sem ataques pessoais, preconceito ou provocação com quem perdeu dinheiro.
5. **Cada assunto no seu canal.** WIN em #win-mini-indice, dólar em #wdo-mini-dolar, dúvida em #duvidas.
6. **Sem spam e sem divulgação.** Links de outros grupos, servidores e redes sociais só com autorização da equipe.
7. **Dados de terceiros são de terceiros.** Não publique conteúdo pago de outras casas (relatórios, cotações licenciadas).
8. **Ninguém da equipe pede senha, token ou acesso à corretora.** Se alguém pedir, é golpe: denuncie.

Quem descumprir: aviso, depois silêncio de 24 horas, depois banimento. Golpe e venda de sinal levam banimento direto.

*Conteúdo educacional. Nada aqui é recomendação de investimento (CVM Res. 20).*"""
BOAS_VINDAS = """**Bem-vindo à Lectnex** 👋
Aqui a gente estuda o mercado brasileiro com dados públicos: mini índice, mini dólar, juros e ações.

**Comece por aqui**
1. Leia {regras} (2 minutos).
2. Conte em {apresente} o que você opera.
3. Toda manhã às 7h40 a Leitura do Dia chega em {leitura}.

Dúvida de iniciante é bem-vinda em {duvidas}. No site <https://lectnex.com.br> você encontra a calculadora de risco, o Diário de Trades e a Academia, de graça.

⚠️ **Ninguém da Lectnex manda mensagem no privado oferecendo sinal ou pedindo dados.** Se receber, é golpe. Dica: desative mensagens diretas deste servidor nas suas configurações de privacidade.

*Conteúdo educacional. Nada aqui é recomendação de investimento.*"""


def montar(simular):
    feito = []

    def faz(desc, metodo, caminho, corpo=None, falso=None):
        feito.append(desc)
        print(('[simulação] ' if simular else '') + desc)
        return falso if simular else api(metodo, caminho, corpo)

    eu = api('GET', '/users/@me')
    g = api('GET', f'/guilds/{GUILD}')
    canais = api('GET', f'/guilds/{GUILD}/channels')
    cargos = api('GET', f'/guilds/{GUILD}/roles')
    todos = next(r for r in cargos if r['id'] == GUILD)
    bot_role = next((r for r in cargos if r.get('managed') and r.get('tags', {}).get('bot_id') == eu['id']), None)
    por_nome = lambda nome, tipo=None: next((c for c in canais if c['name'].lower() == nome.lower() and (tipo is None or c['type'] in tipo)), None)

    # 1. cargos (criados abaixo do cargo do robô; "Fundador" você arrasta para o topo depois)
    for r0 in cargos:
        if r0['name'] in RENOMEAR_CARGO and RENOMEAR_CARGO[r0['name']] not in [x['name'] for x in cargos]:
            faz(f'Renomear cargo {r0["name"]} → {RENOMEAR_CARGO[r0["name"]]}', 'PATCH', f'/guilds/{GUILD}/roles/{r0["id"]}', {'name': RENOMEAR_CARGO[r0['name']]})
            r0['name'] = RENOMEAR_CARGO[r0['name']]
    ids_cargo = {r['name']: r['id'] for r in cargos}
    for nome, cor, separado, perms in CARGOS:
        if nome not in ids_cargo:
            r = faz(f'Criar cargo {nome}', 'POST', f'/guilds/{GUILD}/roles', {'name': nome, 'color': cor, 'hoist': separado, 'mentionable': False, 'permissions': perms}, {'id': f'novo-{nome}'})
            ids_cargo[nome] = r['id']
    # @everyone: sem criar convite e sem mencionar @everyone
    novo = int(todos['permissions']) & ~(1 << 0) & ~(1 << 17)
    if novo != int(todos['permissions']):
        faz('Tirar de @everyone: criar convite e mencionar @everyone', 'PATCH', f'/guilds/{GUILD}/roles/{GUILD}', {'permissions': str(novo)})

    def sobreposicoes(modo, privado=False):
        ov = []
        if privado:
            ov.append({'id': GUILD, 'type': 0, 'allow': '0', 'deny': B(VER)})
            ov.append({'id': ids_cargo['Moderador'], 'type': 0, 'allow': B(VER, ENVIAR, HIST), 'deny': '0'})
        elif modo == EQUIPE:
            ov.append({'id': GUILD, 'type': 0, 'allow': '0', 'deny': B(ENVIAR, TOPICO, MSG_TOPICO)})
        if bot_role and (modo == EQUIPE or privado):
            ov.append({'id': bot_role['id'], 'type': 0, 'allow': B(VER, ENVIAR, GER_MSG, LINKS, ARQ, HIST), 'deny': '0'})
        return ov

    # 2. categorias existentes renomeadas; novas criadas
    for c in [c for c in canais if c['type'] == 4]:
        alvo = RENOMEAR_CAT.get(c['name'].lower())
        if alvo and not por_nome(alvo, [4]):
            faz(f'Renomear categoria "{c["name"]}" → {alvo}', 'PATCH', f'/channels/{c["id"]}', {'name': alvo})
            c['name'] = alvo
    ids_cat = {}
    for pos, (cat, _) in enumerate(CATEGORIAS):
        c = por_nome(cat, [4])
        if not c:
            c = faz(f'Criar categoria {cat}', 'POST', f'/guilds/{GUILD}/channels', {'name': cat, 'type': 4, 'position': pos}, {'id': f'nova-{cat}', 'name': cat, 'type': 4})
            canais.append(c)
        ids_cat[cat] = c['id']

    # 3. canais que já existem: renomear e mover
    for c in list(canais):
        mapa = RENOMEAR_VOZ if c['type'] == 2 else RENOMEAR if c['type'] == 0 else {}
        alvo = mapa.get(c['name'].lower())
        if alvo and not por_nome(alvo[0], [c['type']]):
            corpo = {'name': alvo[0], 'parent_id': ids_cat[alvo[1]]}
            if alvo[0] == 'regras':
                corpo['permission_overwrites'] = c.get('permission_overwrites', []) + [o for o in sobreposicoes(EQUIPE) if o['id'] not in [x['id'] for x in c.get('permission_overwrites', [])]]
                corpo['topic'] = 'Regras e aviso legal'
            faz(f'Renomear #{c["name"]} → {alvo[0]} e mover para {alvo[1]}', 'PATCH', f'/channels/{c["id"]}', corpo)
            c['name'], c['parent_id'] = alvo[0], ids_cat[alvo[1]]

    # 4. canais novos
    for cat, lista in CATEGORIAS:
        for pos, (nome, tipo, modo, topico) in enumerate(lista):
            if por_nome(nome, [tipo]):
                continue
            corpo = {'name': nome, 'type': tipo, 'parent_id': ids_cat[cat], 'position': pos, 'permission_overwrites': sobreposicoes(modo)}
            if topico:
                corpo['topic'] = topico
            if isinstance(modo, int):
                corpo['rate_limit_per_user'] = modo
            if tipo == 15:
                corpo['available_tags'] = [{'name': t} for t in ETIQUETAS.get(nome, [])]
            c = faz(f'Criar #{nome} em {cat}' + (f' (modo lento {modo}s)' if isinstance(modo, int) else ' (só equipe e robô escrevem)' if modo == EQUIPE else ''),
                    'POST', f'/guilds/{GUILD}/channels', corpo, {'id': f'novo-{nome}', 'name': nome, 'type': tipo})
            canais.append(c)
    if not por_nome('log-moderacao', [0]):
        c = faz('Criar #log-moderacao (privado: só equipe e robô)', 'POST', f'/guilds/{GUILD}/channels',
                {'name': 'log-moderacao', 'type': 0, 'permission_overwrites': sobreposicoes(None, privado=True), 'topic': 'Alertas do AutoMod'}, {'id': 'novo-log', 'name': 'log-moderacao', 'type': 0})
        canais.append(c)
    log = por_nome('log-moderacao', [0])

    # 5. ordem das categorias
    ordem = [{'id': ids_cat[cat], 'position': i} for i, (cat, _) in enumerate(CATEGORIAS)]
    for cat, lista in CATEGORIAS:
        for i, (nome, tipo, _, _) in enumerate(lista):
            c = por_nome(nome, [tipo])
            if c and not str(c['id']).startswith('nov'):
                ordem.append({'id': c['id'], 'position': i})
    ordem = [o for o in ordem if not str(o['id']).startswith('nov')]
    try:
        faz('Ordenar categorias e canais', 'PATCH', f'/guilds/{GUILD}/channels', ordem)
    except SystemExit as e:  # ordem é cosmética: não para a montagem
        print(f'::warning::Ordem dos canais: {e}')

    # 6. segurança do servidor
    if g.get('verification_level', 0) < 2:
        faz('Nível de verificação: Médio (conta com mais de 5 minutos no Discord)', 'PATCH', f'/guilds/{GUILD}', {'verification_level': 2})

    # 7. AutoMod (só cria o que não existe com o mesmo nome)
    try:
        regras = {r['name'] for r in api('GET', f'/guilds/{GUILD}/auto-moderation/rules')}
    except SystemExit:
        regras = set()
    isentos = [ids_cargo['Moderador']] if not str(ids_cargo['Moderador']).startswith('novo') else []
    alerta = [{'type': 2, 'metadata': {'channel_id': log['id']}}] if not str(log['id']).startswith('novo') else []
    automod = [
        ('Lectnex: golpes e sinais', {'event_type': 1, 'trigger_type': 1, 'trigger_metadata': {'keyword_filter': [f'*{k}*' for k in GOLPE]},
                                      'actions': [{'type': 1, 'metadata': {'custom_message': 'Mensagem bloqueada: venda de sinal ou promessa de ganho não é permitida aqui (regra 2 e 3).'}}]}),
        ('Lectnex: links de fora', {'event_type': 1, 'trigger_type': 1, 'trigger_metadata': {'keyword_filter': LINKS_BLOQ, 'allow_list': LINKS_OK},
                                    'actions': [{'type': 1, 'metadata': {'custom_message': 'Links de fora só com autorização da equipe (regra 6). Sites oficiais e o lectnex.com.br são liberados.'}}]}),
        ('Lectnex: suspeita de spam', {'event_type': 1, 'trigger_type': 3, 'actions': [{'type': 1}]}),
        ('Lectnex: palavras ofensivas', {'event_type': 1, 'trigger_type': 4, 'trigger_metadata': {'presets': [1, 2, 3]}, 'actions': [{'type': 1}]}),
    ]
    for nome, corpo in automod:
        if nome not in regras:
            corpo = {**corpo, 'name': nome, 'enabled': True, 'exempt_roles': isentos, 'actions': corpo['actions'] + alerta}
            try:
                faz(f'AutoMod: {nome}', 'POST', f'/guilds/{GUILD}/auto-moderation/rules', corpo)
            except SystemExit as e:  # ex.: o servidor já tem uma regra de spam com outro nome
                print(f'::warning::{nome}: {e}')

    # 8. regras e boas-vindas: posta e fixa (ou atualiza a mensagem do robô já fixada)
    def mencao(n):
        c = por_nome(n)
        return f'<#{c["id"]}>' if c and not str(c['id']).startswith('nov') else f'#{n}'
    textos = {'regras': REGRAS, 'boas-vindas': BOAS_VINDAS.format(regras=mencao('regras'), apresente=mencao('apresente-se'), leitura=mencao('leitura-do-dia'), duvidas=mencao('duvidas'))}
    for canal, texto in textos.items():
        c = por_nome(canal, [0])
        if not c:
            continue
        recentes = [] if str(c['id']).startswith('nov') else api('GET', f'/channels/{c["id"]}/messages?limit=50')
        primeira = texto.split('\n', 1)[0]
        minha = next((m for m in recentes if m['author']['id'] == eu['id'] and m['content'].split('\n', 1)[0] == primeira), None)
        if minha:
            if minha['content'] != texto:
                faz(f'Atualizar a mensagem do robô em #{canal}', 'PATCH', f'/channels/{c["id"]}/messages/{minha["id"]}', {'content': texto})
        else:
            minha = faz(f'Postar a mensagem em #{canal}', 'POST', f'/channels/{c["id"]}/messages', {'content': texto, 'flags': 4}, {'id': 'nova-msg', 'pinned': False})
        if not minha.get('pinned'):
            try:
                faz(f'Fixar a mensagem em #{canal}', 'PUT', f'/channels/{c["id"]}/messages/pins/{minha["id"]}')
            except SystemExit:
                try:
                    faz(f'Fixar a mensagem em #{canal} (rota antiga)', 'PUT', f'/channels/{c["id"]}/pins/{minha["id"]}')
                except SystemExit as e:  # desde 2026 fixar exige a permissão própria "Fixar mensagens"
                    print(f'::warning::Não consegui fixar em #{canal}: falta a permissão "Fixar mensagens" para o robô ({e})')
    if g.get('rules_channel_id') and por_nome('regras') and g['rules_channel_id'] != por_nome('regras')['id']:
        faz('Definir #regras como canal de regras da Comunidade', 'PATCH', f'/guilds/{GUILD}', {'rules_channel_id': por_nome('regras')['id']})

    # 9. logo no servidor e no bot
    import base64
    logo = 'data:image/png;base64,' + base64.b64encode(open('assets/brand/logo-transparente.png', 'rb').read()).decode()
    if not g.get('icon') or os.environ.get('TROCAR_LOGO'):
        faz('Colocar a logo da Lectnex como foto do servidor', 'PATCH', f'/guilds/{GUILD}', {'icon': logo})
    if not eu.get('avatar') or os.environ.get('TROCAR_LOGO'):
        try:
            faz('Colocar a logo da Lectnex como foto do bot', 'PATCH', '/users/@me', {'avatar': logo})
        except SystemExit as e:
            print(f'::warning::Foto do bot: {e}')

    # 10. ajustes do servidor: descrição, notificações só com menção, mensagens de entrada, alertas de segurança
    cid = lambda n: (por_nome(n) or {}).get('id')
    ajustes = {}
    desc = 'Comunidade de estudo do mercado brasileiro: mini índice, mini dólar, juros, ações e investimentos. Educacional, sem recomendação.'
    if g.get('description') != desc:
        ajustes['description'] = desc
    if g.get('default_message_notifications') != 1:
        ajustes['default_message_notifications'] = 1
    if cid('apresente-se') and g.get('system_channel_id') != cid('apresente-se'):
        ajustes['system_channel_id'] = cid('apresente-se')
        ajustes['system_channel_flags'] = (1 << 1) | (1 << 2) | (1 << 3)  # sem avisos de impulso, dicas e figurinhas de resposta
    if cid('log-moderacao'):
        if g.get('safety_alerts_channel_id') != cid('log-moderacao'):
            ajustes['safety_alerts_channel_id'] = cid('log-moderacao')
        if g.get('public_updates_channel_id') != cid('log-moderacao'):
            ajustes['public_updates_channel_id'] = cid('log-moderacao')
    NOMES = {'description': 'descrição', 'default_message_notifications': 'notificar só menções', 'system_channel_id': 'entradas em #apresente-se',
             'system_channel_flags': 'sem avisos automáticos', 'safety_alerts_channel_id': 'alertas de segurança no log', 'public_updates_channel_id': 'avisos do Discord no log'}
    for k, v in ajustes.items():  # um por vez: o que o Discord recusar não trava o resto
        try:
            faz(f'Ajuste do servidor: {NOMES[k]}', 'PATCH', f'/guilds/{GUILD}', {k: v})
        except SystemExit as e:
            print(f'::warning::Ajuste "{NOMES[k]}" recusado: {e}')

    # 11. tela de boas-vindas (aparece para quem entra)
    tela = [('boas-vindas', 'Comece por aqui', '👋'), ('leitura-do-dia', 'Leitura do Dia às 7h40', '📊'), ('duvidas', 'Pergunte sem medo', '❓'),
            ('win-mini-indice', 'Mini índice no pregão', '📈'), ('renda-fixa', 'Investimentos: renda fixa, FIIs e ações', '💰')]
    canais_tela = [{'channel_id': cid(n), 'description': d, 'emoji_name': em} for n, d, em in tela if cid(n) and not str(cid(n)).startswith('nov')]
    try:
        faz('Tela de boas-vindas do servidor', 'PATCH', f'/guilds/{GUILD}/welcome-screen',
            {'enabled': True, 'description': 'Estudo do mercado brasileiro com dados públicos. Educacional, sem recomendação.', 'welcome_channels': canais_tela})
    except SystemExit as e:
        print(f'::warning::Tela de boas-vindas: {e}')

    # 12. perguntas da entrada (Onboarding): escolhe o que acompanha → cargo e canais
    r_ = lambda n: ids_cargo.get(n)
    if not any(str(v).startswith('novo') for v in ids_cargo.values()):
        prompts = [{'id': '0', 'type': 0, 'title': 'O que você acompanha?', 'single_select': False, 'required': False, 'in_onboarding': True,
                    'options': [{'id': '0', 'title': 'Mini índice (WIN)', 'emoji': {'name': '📈'}, 'role_ids': [r_('Trader WIN')], 'channel_ids': [cid('win-mini-indice')]},
                                {'id': '1', 'title': 'Mini dólar (WDO)', 'emoji': {'name': '💵'}, 'role_ids': [r_('Trader WDO')], 'channel_ids': [cid('wdo-mini-dolar')]},
                                {'id': '2', 'title': 'Investimentos (ações, FIIs, renda fixa)', 'emoji': {'name': '💰'}, 'role_ids': [r_('Investidor')],
                                 'channel_ids': [c for c in (cid('acoes-e-dividendos'), cid('fundos-imobiliarios'), cid('renda-fixa'), cid('carteiras')) if c]}]},
                   {'id': '1', 'type': 0, 'title': 'Há quanto tempo você opera ou investe?', 'single_select': True, 'required': False, 'in_onboarding': True,
                    'options': [{'id': '3', 'title': 'Estou começando', 'emoji': {'name': '🌱'}, 'role_ids': [], 'channel_ids': [c for c in (cid('duvidas'), cid('material')) if c]},
                                {'id': '4', 'title': 'Menos de 1 ano', 'emoji': {'name': '📚'}, 'role_ids': [], 'channel_ids': [c for c in (cid('duvidas'),) if c]},
                                {'id': '5', 'title': 'Mais de 1 ano', 'emoji': {'name': '🎯'}, 'role_ids': [], 'channel_ids': [c for c in (cid('diario-de-trades'),) if c]}]}]
        padrao = [c for c in map(cid, ['boas-vindas', 'regras', 'avisos', 'apresente-se', 'leitura-do-dia', 'agenda-e-alertas', 'fechamento',
                                       'juros-e-dolar', 'duvidas', 'material', 'off-topic', 'sugestoes-pro-site', 'Sala do pregão']) if c]
        try:
            faz('Perguntas da entrada (Onboarding)', 'PUT', f'/guilds/{GUILD}/onboarding', {'prompts': prompts, 'default_channel_ids': padrao, 'enabled': True, 'mode': 0})
        except SystemExit as e:
            print(f'::warning::Onboarding (configure pelo painel se falhar): {e}')

    # 13. apresentação em cada canal automático (uma vez só): testa o envio e explica o que chega ali
    intro = {'leitura-do-dia': '📊 **Aqui chega a Leitura do Dia**, todo dia de pregão às 7h40: resumo do que mexe com o mercado, viés e o que observar.',
             'agenda-e-alertas': '📅 **Aqui chegam a agenda do dia** (às 7h40) **e os alertas** quando um dado sai acima ou abaixo do esperado.',
             'fechamento': '🔔 **Aqui chega o fechamento** de cada pregão, com o gráfico do dia: o que as notícias fizeram com o preço.',
             'juros-e-dolar': '⚡ **Aqui chegam os saltos fortes dos juros**: cada dia em que a curva andou 0,75 ponto ou mais, com o motivo. Histórico em <https://lectnex.com.br/juros/>'}
    for canal, texto in intro.items():
        c = por_nome(canal, [0])
        if not c or str(c['id']).startswith('nov'):
            continue
        recentes = api('GET', f'/channels/{c["id"]}/messages?limit=20')
        if not any(m['author']['id'] == eu['id'] and m['content'].startswith(texto[:20]) for m in recentes):
            faz(f'Apresentação em #{canal}', 'POST', f'/channels/{c["id"]}/messages', {'content': texto + '\n*Conteúdo educacional. Não é recomendação de investimento.*', 'flags': 4})

    print(f'\n{len(feito)} ação(ões){" (nada foi alterado: simulação)" if simular else ""}. Nada foi apagado.')


def visual():
    """Pacote do nível 3: banner animado, fundo do convite, ícones e degradê nos cargos, áudio máximo e emojis (assets/discord/)."""
    import base64
    D = 'assets/discord/'
    uri = lambda f, t: f'data:{t};base64,' + base64.b64encode(open(D + f, 'rb').read()).decode()

    def tenta(desc, metodo, caminho, corpo):
        try:
            api(metodo, caminho, corpo)
            print(desc)
            return True
        except SystemExit as e:
            print(f'::warning::{desc}: {e}')
            return False
    tenta('Banner animado do servidor', 'PATCH', f'/guilds/{GUILD}', {'banner': uri('banner.gif', 'image/gif')})
    tenta('Fundo da tela de convite', 'PATCH', f'/guilds/{GUILD}', {'splash': uri('convite-fundo.jpg', 'image/jpeg')})
    cargos = {r['name']: r for r in api('GET', f'/guilds/{GUILD}/roles')}
    for nome, arq in [('Fundador', 'cargo-fundador.png'), ('Moderador', 'cargo-moderador.png'), ('Trader WIN', 'cargo-win.png'),
                      ('Trader WDO', 'cargo-wdo.png'), ('Investidor', 'cargo-investidor.png')]:
        if nome in cargos:
            tenta(f'Ícone do cargo {nome}', 'PATCH', f'/guilds/{GUILD}/roles/{cargos[nome]["id"]}', {'icon': uri(arq, 'image/png')})
    for nome, (a, b) in {'Fundador': (0x009988, 0xF39200), 'Moderador': (0x00B4A2, 0x3B82F6)}.items():
        if nome in cargos:
            tenta(f'Degradê no cargo {nome}', 'PATCH', f'/guilds/{GUILD}/roles/{cargos[nome]["id"]}',
                  {'colors': {'primary_color': a, 'secondary_color': b, 'tertiary_color': None}})
    for c in api('GET', f'/guilds/{GUILD}/channels'):
        if c['type'] == 2 and c.get('bitrate') != 384000:
            tenta(f'Áudio máximo (384 kbps) em {c["name"]}', 'PATCH', f'/channels/{c["id"]}', {'bitrate': 384000})
    ja = {e['name'] for e in api('GET', f'/guilds/{GUILD}/emojis')}
    import glob
    for f in sorted(glob.glob(D + 'emoji-*.png')):
        nome = 'lx_' + os.path.basename(f)[6:-4]
        if nome not in ja and not tenta(f'Emoji :{nome}:', 'POST', f'/guilds/{GUILD}/emojis', {'name': nome, 'image': uri(os.path.basename(f), 'image/png')}):
            print('::warning::Sem permissão para emojis: ligue "Gerenciar expressões" (ou "Criar expressões") no cargo do bot.')
            break


def convite():
    """Convite permanente para #boas-vindas (reaproveita um do robô se já existir). O código é público: vai no site."""
    canais = api('GET', f'/guilds/{GUILD}/channels')
    bv = next(c for c in canais if c['name'] == 'boas-vindas')
    eu = api('GET', '/users/@me')
    for i in api('GET', f'/channels/{bv["id"]}/invites'):
        if (i.get('inviter') or {}).get('id') == eu['id'] and i.get('max_age') == 0 and i.get('max_uses') == 0:
            print(f'CONVITE=https://discord.gg/{i["code"]}'); return
    i = api('POST', f'/channels/{bv["id"]}/invites', {'max_age': 0, 'max_uses': 0, 'unique': False})
    print(f'CONVITE=https://discord.gg/{i["code"]}')


if __name__ == '__main__':
    if not TOKEN:
        sys.exit('::error::Falta o segredo DISCORD_BOT_TOKEN.')
    modo = sys.argv[1] if len(sys.argv) > 1 else 'ler'
    if modo == 'ler':
        ler()
    elif modo == 'visual':
        visual()
    elif modo == 'convite':
        convite()
    elif modo in ('simular', 'montar'):
        montar(modo == 'simular')
    else:
        sys.exit(f'Modo desconhecido: {modo}')
