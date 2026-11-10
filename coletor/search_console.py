"""Relatório semanal do Google Search Console no chat PRIVADO do Telegram (TELEGRAM_ADMIN_CHAT_ID).

Toda segunda-feira (horário em coletor/relogio.py). Mostra:
  - cliques, impressões, CTR e posição média da semana, comparados com a semana anterior
  - desempenho por grupo de páginas (ações, glossário, respostas rápidas, leitura…)
  - páginas e buscas que mais trouxeram cliques
  - oportunidades: buscas com muitas impressões em posição 5–20 (perto da primeira página)
  - amostra de indexação das páginas novas (URL Inspection API)

O Search Console tem atraso de 2 a 3 dias, então a "semana" termina 3 dias antes de hoje.
Nenhum dado vai para o repositório (que é público): só para o Telegram privado.

Segredos:
  GSC_SERVICE_ACCOUNT  JSON da chave da conta de serviço do Google Cloud (com acesso à propriedade no Search Console)
  GSC_SITE             opcional: 'sc-domain:lectnex.com.br' ou 'https://lectnex.com.br/'. Sem ele, usa a propriedade
                       que a conta de serviço enxergar com lectnex.com.br no nome.
  TELEGRAM_BOT_TOKEN, TELEGRAM_ADMIN_CHAT_ID  como no Resumo do dono.
TESTE=1 só imprime (e envia marcado como teste se houver Telegram).
"""
import datetime as dt
import glob
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

BRT = dt.timezone(dt.timedelta(hours=-3))
HOJE = dt.datetime.now(BRT).date()
FIM = HOJE - dt.timedelta(days=3)           # último dia com dado quase completo
INI = FIM - dt.timedelta(days=6)            # 7 dias
INI_ANT, FIM_ANT = INI - dt.timedelta(days=7), INI - dt.timedelta(days=1)
BASE = 'https://lectnex.com.br/'
API = 'https://searchconsole.googleapis.com'
TESTE = os.environ.get('TESTE') == '1'
AMOSTRA_INDEX = 30                          # URLs inspecionadas por semana (cota da API: 2.000/dia)
e = lambda s: html.escape(str(s if s is not None else ''), quote=False)

GRUPOS = [  # (rótulo, regra sobre o caminho da URL)
    ('Páginas por ação', lambda p: p.startswith('acoes/') and p != 'acoes/'),
    ('Glossário (termos)', lambda p: p.startswith('glossario/')),
    ('Respostas rápidas', lambda p: p in ('vencimento-mini-indice-mini-dolar.html', 'calculadora-ir-day-trade.html', 'valor-do-ponto-mini-indice-mini-dolar.html')),
    ('Leitura do Dia', lambda p: p.startswith('leitura/')),
    ('Agenda da semana', lambda p: p.startswith('semana/')),
    ('Manchetes', lambda p: p.startswith('manchetes')),
    ('Páginas principais', lambda p: True),
]


# ----------------------------------------------------------------------------- acesso ao Google
def sessao():
    bruto = os.environ.get('GSC_SERVICE_ACCOUNT', '').strip()
    if not bruto:
        return None
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
    info = json.loads(bruto)
    cred = service_account.Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/webmasters.readonly'])
    s = AuthorizedSession(cred)
    s.email = info.get('client_email', '')
    return s


def chamar(s, metodo, caminho, corpo=None):
    r = s.request(metodo, API + caminho, json=corpo, timeout=60)
    if r.status_code >= 400:
        raise RuntimeError(f'HTTP {r.status_code} em {caminho.split("?")[0]}: {r.text[:300]}')
    return r.json() if r.content else {}


def propriedade(s):
    if os.environ.get('GSC_SITE', '').strip():
        return os.environ['GSC_SITE'].strip()
    sites = [x['siteUrl'] for x in chamar(s, 'GET', '/webmasters/v3/sites').get('siteEntry', []) if x.get('permissionLevel') != 'siteUnverifiedUser']
    nossos = [x for x in sites if 'lectnex.com.br' in x]
    if not nossos:
        raise RuntimeError('a conta de serviço não tem acesso a nenhuma propriedade do lectnex.com.br no Search Console '
                           f'(propriedades visíveis: {sites or "nenhuma"}). Adicione o e-mail dela como usuário da propriedade.')
    return sorted(nossos, key=lambda x: not x.startswith('sc-domain:'))[0]   # prefere a propriedade de domínio


def consulta(s, site, ini, fim, dimensoes, limite=1000):
    corpo = {'startDate': ini.isoformat(), 'endDate': fim.isoformat(), 'dimensions': dimensoes, 'rowLimit': limite, 'dataState': 'all'}
    return chamar(s, 'POST', f'/webmasters/v3/sites/{urllib.parse.quote(site, safe="")}/searchAnalytics/query', corpo).get('rows', [])


def inspecionar(s, site, url):
    r = chamar(s, 'POST', '/v1/urlInspection/index:inspect', {'inspectionUrl': url, 'siteUrl': site, 'languageCode': 'pt-BR'})
    st = (r.get('inspectionResult') or {}).get('indexStatusResult') or {}
    return st.get('verdict'), st.get('coverageState') or ''


# ----------------------------------------------------------------------------- contas
def caminho(url):
    p = re.sub(r'^https?://(www\.)?lectnex\.com\.br/?', '', url).split('#')[0].split('?')[0]
    return p or 'index.html'


def grupo(p):
    return next(nome for nome, regra in GRUPOS if regra(p))


def totais(linhas):
    c = sum(x['clicks'] for x in linhas)
    i = sum(x['impressions'] for x in linhas)
    pos = sum(x['position'] * x['impressions'] for x in linhas) / i if i else 0
    return {'cliques': c, 'impressoes': i, 'ctr': c / i * 100 if i else 0, 'posicao': pos}


def var(a, b, pct=True):
    if b in (0, None):
        return ' (novo)' if a else ''
    d = (a / b - 1) * 100 if pct else a - b
    return f' ({"+" if d >= 0 else ""}{d:.0f}%)' if pct else f' ({"+" if d >= 0 else ""}{d:.1f})'.replace('.', ',')


def n(v):
    return f'{v:,.0f}'.replace(',', '.')


def dec(v, casas=1):
    return f'{v:.{casas}f}'.replace('.', ',')


def amostra_urls():
    """Páginas novas para checar indexação: as 3 respostas rápidas + rodízio semanal de ações e glossário."""
    fixas = [BASE + x for x in ('vencimento-mini-indice-mini-dolar.html', 'calculadora-ir-day-trade.html', 'valor-do-ponto-mini-indice-mini-dolar.html', 'acoes/', 'acoes/petr4.html', 'glossario/rolagem.html')]
    resto = sorted(glob.glob('acoes/*.html') + glob.glob('glossario/*.html'))
    resto = [BASE + x for x in resto if BASE + x not in fixas and not x.endswith('index.html')]
    if not resto:
        return fixas
    semana = HOJE.isocalendar()[1]
    k = AMOSTRA_INDEX - len(fixas)
    ini = (semana * k) % len(resto)
    return fixas + (resto[ini:] + resto[:ini])[:k]


# ----------------------------------------------------------------------------- relatório
def montar(s, site):
    pags = consulta(s, site, INI, FIM, ['page'])
    pags_ant = consulta(s, site, INI_ANT, FIM_ANT, ['page'])
    buscas = consulta(s, site, INI, FIM, ['query'])
    t, t0 = totais(pags), totais(pags_ant)
    L = [f'🔎 <b>Google · semana de {INI:%d/%m} a {FIM:%d/%m}</b>{" (TESTE)" if TESTE else ""}',
         f'Cliques: <b>{n(t["cliques"])}</b>{var(t["cliques"], t0["cliques"])}',
         f'Impressões: <b>{n(t["impressoes"])}</b>{var(t["impressoes"], t0["impressoes"])}',
         f'CTR: {dec(t["ctr"])}% · posição média: {dec(t["posicao"])}{var(t["posicao"], t0["posicao"], pct=False) if t0["impressoes"] else ""}']
    if not pags:
        L.append('\nAinda sem impressões nesta semana. Em domínio novo é normal levar algumas semanas.')
    # por grupo
    g, g0 = {}, {}
    for linhas, alvo in ((pags, g), (pags_ant, g0)):
        for x in linhas:
            alvo.setdefault(grupo(caminho(x['keys'][0])), []).append(x)
    if g:
        L.append('\n📂 <b>Por tipo de página</b> (cliques · impressões)')
        for nome, _ in GRUPOS:
            if nome in g or nome in g0:
                a, b = totais(g.get(nome, [])), totais(g0.get(nome, []))
                L.append(f'• {e(nome)}: {n(a["cliques"])} · {n(a["impressoes"])}{var(a["impressoes"], b["impressoes"])} · {len(g.get(nome, []))} pág.')
    # top páginas
    top = sorted(pags, key=lambda x: (-x['clicks'], -x['impressions']))[:8]
    if top:
        L.append('\n🏆 <b>Páginas que mais trouxeram visitas</b>')
        L += [f'• {e(caminho(x["keys"][0]))}: {n(x["clicks"])} cliques · {n(x["impressions"])} impr. · pos. {dec(x["position"])}' for x in top]
    # top buscas
    topb = sorted(buscas, key=lambda x: (-x['clicks'], -x['impressions']))[:8]
    if topb:
        L.append('\n💬 <b>Buscas que trouxeram cliques</b>')
        L += [f'• "{e(x["keys"][0])}": {n(x["clicks"])} cliques · pos. {dec(x["position"])}' for x in topb]
    # oportunidades
    opp = sorted([x for x in buscas if 5 <= x['position'] <= 20 and x['impressions'] >= 20], key=lambda x: -x['impressions'])[:6]
    if opp:
        L.append('\n🎯 <b>Quase na primeira página</b> (posição 5–20, vale melhorar)')
        L += [f'• "{e(x["keys"][0])}": {n(x["impressions"])} impr. · pos. {dec(x["position"])}' for x in opp]
    return L


def indexacao(s, site):
    urls = amostra_urls()
    sim, nao, erros = 0, [], 0
    for u in urls:
        try:
            veredito, estado = inspecionar(s, site, u)
        except Exception as ex:
            erros += 1
            print(f'::warning::inspeção falhou em {u}: {str(ex)[:160]}')
            continue
        if veredito == 'PASS':
            sim += 1
        else:
            nao.append((caminho(u), estado or veredito or '?'))
    L = [f'\n🗂️ <b>Indexação (amostra de {len(urls)} páginas novas)</b>', f'No Google: <b>{sim}</b> · fora: <b>{len(nao)}</b>' + (f' · não verificadas: {erros}' if erros else '')]
    estados = {}
    for _, est in nao:
        estados[est] = estados.get(est, 0) + 1
    L += [f'• {e(est)}: {q}' for est, q in sorted(estados.items(), key=lambda x: -x[1])[:4]]
    return L


def enviar(texto):
    token = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
    chat = os.environ.get('TELEGRAM_ADMIN_CHAT_ID', '').strip()
    if not (token and chat) or chat.startswith('@'):
        print('::warning::Sem TELEGRAM_ADMIN_CHAT_ID (chat privado): relatório não enviado.')
        return
    partes, atual = [], ''
    for linha in texto.split('\n'):   # limite do Telegram: 4.096 caracteres por mensagem
        if len(atual) + len(linha) + 1 > 3900:
            partes.append(atual); atual = ''
        atual += linha + '\n'
    partes.append(atual)
    for p in partes:
        req = urllib.request.Request(f'https://api.telegram.org/bot{token}/sendMessage',
                                     data=json.dumps({'chat_id': chat, 'text': p, 'parse_mode': 'HTML', 'disable_web_page_preview': True}).encode(),
                                     headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=20).read()
    print('Relatório enviado.')


def main():
    s = sessao()
    if s is None:
        msg = ('🔎 Relatório do Google ainda não configurado: falta o segredo GSC_SERVICE_ACCOUNT no GitHub. '
               'O passo a passo está no LEIA-ME, seção "Relatório do Search Console".')
        print('::warning::' + msg)
        if TESTE:
            enviar(msg)
        return
    try:
        site = propriedade(s)
        print(f'Propriedade: {site} · conta: {s.email}')
        L = montar(s, site)
        try:
            L += indexacao(s, site)
        except Exception as ex:
            L.append(f'\n🗂️ Indexação: não consegui verificar ({e(str(ex)[:120])}).')
        L.append(f'\n<a href="https://search.google.com/search-console?resource_id={urllib.parse.quote(site, safe="")}">Abrir o Search Console</a>')
    except Exception as ex:
        L = [f'🔎 <b>Relatório do Google</b>: falhou.', e(str(ex)[:600]), f'\nConta de serviço: {e(s.email)}']
        print(f'::error::{ex}')
    texto = '\n'.join(L)
    print(texto)
    enviar(texto)


if __name__ == '__main__':
    main()
