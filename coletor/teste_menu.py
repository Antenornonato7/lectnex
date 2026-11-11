"""Resultado do teste A/B do menu de estudo ("Laboratório" × "Aprender") no chat PRIVADO do Telegram.

O site sorteia cada visitante (assets/lectnex-core.js, LX.abMenu) e manda ao Google Analytics:
- propriedade de usuário  teste_menu = A (Laboratório) ou B (Aprender);
- evento menu_clique com os parâmetros destino (lab, futuros…) e teste_menu.

Este script lê o Google Analytics (Data API) com a MESMA conta de serviço do relatório do Search Console
(segredo GSC_SERVICE_ACCOUNT) e responde: em cada variante, que parte dos visitantes clicou no menu de estudo?
Diz se a diferença já é confiável (teste de duas proporções, 95%) ou se ainda é cedo.

Precisa (uma vez só):
1. No Google Analytics: Admin → Acesso à propriedade → adicionar relatorio-gsc@lectnex.iam.gserviceaccount.com como Leitor.
2. No Google Cloud (projeto lectnex): ativar a "Google Analytics Data API".
3. No Analytics: Admin → Definições personalizadas → criar teste_menu (escopo usuário) e destino (escopo evento).
4. No GitHub: segredo GA_PROPERTY_ID com o número da propriedade (Admin → Detalhes da propriedade).
Nunca grava nada no repositório: o resultado vai só para o Telegram privado.
TESTE=1 envia mesmo fora do horário (para conferir a configuração).
"""
import datetime as dt
import html
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from search_console import ler_chave, enviar  # noqa: E402  (mesma chave e mesmo envio do relatório do Google)

BRT = dt.timezone(dt.timedelta(hours=-3))
INICIO = dt.date(2026, 11, 11)       # dia em que o teste entrou no ar
FIM_PREVISTO = dt.date(2026, 11, 25)  # ~2 semanas
API = 'https://analyticsdata.googleapis.com/v1beta/properties/{}:runReport'
NOME = {'A': 'Laboratório', 'B': 'Aprender'}
e = lambda s: html.escape(str(s), quote=False)


def sessao():
    bruto = os.environ.get('GSC_SERVICE_ACCOUNT', '').strip()
    if not bruto:
        return None
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
    info = ler_chave(bruto)
    cred = service_account.Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/analytics.readonly'])
    s = AuthorizedSession(cred)
    s.email = info.get('client_email', '')
    return s


def relatorio(s, prop, corpo):
    r = s.post(API.format(prop), json=corpo, timeout=60)
    if r.status_code >= 400:
        raise RuntimeError(f'HTTP {r.status_code}: {r.text[:400]}')
    linhas = r.json().get('rows', [])
    return [([d['value'] for d in x.get('dimensionValues', [])], [float(m['value']) for m in x.get('metricValues', [])]) for x in linhas]


def z_duas_proporcoes(x1, n1, x2, n2):
    if not (n1 and n2):
        return None
    p = (x1 + x2) / (n1 + n2)
    ep = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    return None if ep == 0 else (x2 / n2 - x1 / n1) / ep


def main():
    prop = os.environ.get('GA_PROPERTY_ID', '').strip()
    try:
        s = sessao()
    except Exception as ex:
        enviar(f'🧪 Teste do menu: a chave do Google não funcionou.\n{e(str(ex)[:300])}'); sys.exit(1)
    if s is None or not prop.isdigit():
        falta = 'o segredo GSC_SERVICE_ACCOUNT' if s is None else 'o segredo GA_PROPERTY_ID (número da propriedade do Analytics)'
        msg = f'🧪 Teste do menu ainda não configurado: falta {falta} no GitHub. Passo a passo no topo de coletor/teste_menu.py.'
        print('::warning::' + msg); enviar(msg); return

    ontem = dt.datetime.now(BRT).date() - dt.timedelta(days=1)
    periodo = [{'startDate': INICIO.isoformat(), 'endDate': max(ontem, INICIO).isoformat()}]
    try:
        vistos = relatorio(s, prop, {'dateRanges': periodo, 'dimensions': [{'name': 'customUser:teste_menu'}], 'metrics': [{'name': 'totalUsers'}]})
        cliques = relatorio(s, prop, {'dateRanges': periodo, 'dimensions': [{'name': 'customUser:teste_menu'}, {'name': 'customEvent:destino'}],
                                      'metrics': [{'name': 'totalUsers'}, {'name': 'eventCount'}],
                                      'dimensionFilter': {'filter': {'fieldName': 'eventName', 'stringFilter': {'value': 'menu_clique'}}}})
    except Exception as ex:
        msg = (f'🧪 <b>Teste do menu</b>: não consegui ler o Analytics.\n{e(str(ex)[:400])}\n\n'
               f'Confira se {e(s.email)} é Leitor da propriedade, se a "Google Analytics Data API" está ativa no Google Cloud '
               'e se as definições personalizadas teste_menu e destino existem.')
        print('::error::' + str(ex)[:400]); enviar(msg); sys.exit(1)

    n = {v: 0 for v in 'AB'}
    for dims, mets in vistos:
        if dims[0] in n:
            n[dims[0]] += int(mets[0])
    x, cl = {v: 0 for v in 'AB'}, {v: 0 for v in 'AB'}
    for dims, mets in cliques:
        if dims[0] in x and dims[1] == 'lab':
            x[dims[0]] += int(mets[0]); cl[dims[0]] += int(mets[1])
    taxa = {v: (x[v] / n[v] * 100 if n[v] else None) for v in 'AB'}
    dias = (ontem - INICIO).days + 1

    L = [f'🧪 <b>Teste do menu: "Laboratório" × "Aprender"</b>', f'{INICIO.strftime("%d/%m")} a {ontem.strftime("%d/%m")} · {dias} dia(s)', '']
    for v in 'AB':
        t = '—' if taxa[v] is None else f'{taxa[v]:.1f}%'.replace('.', ',')
        L.append(f'<b>{NOME[v]}</b>: {n[v]} visitantes · {x[v]} clicaram no menu de estudo ({cl[v]} cliques) · <b>{t}</b>')
    L.append('')
    z = z_duas_proporcoes(x['A'], n['A'], x['B'], n['B'])
    if min(n.values()) < 200 or min(x.values()) < 10:
        L.append('⏳ Ainda é cedo: precisa de pelo menos ~200 visitantes e 10 cliques em cada nome para comparar.')
    elif z is None or abs(z) < 1.96:
        L.append('🤝 Empate técnico até aqui: a diferença ainda pode ser acaso. Se continuar assim no fim, tanto faz o nome.')
    else:
        g = 'B' if z > 0 else 'A'
        L.append(f'🏆 <b>"{NOME[g]}"</b> leva mais gente para a área de estudo, com diferença acima do acaso (95% de confiança).')
    if ontem >= FIM_PREVISTO:
        L.append('\nO teste já completou as 2 semanas previstas. Me diga se quer fixar o nome vencedor no site.')
    texto = '\n'.join(L)
    print(texto)
    enviar(texto)


if __name__ == '__main__':
    main()
