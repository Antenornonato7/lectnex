"""Resumo semanal do site (domingo) no chat PRIVADO do Telegram.

Junta numa mensagem só:
- Google Analytics (mesma conta de serviço do Search Console, segredo GSC_SERVICE_ACCOUNT): visitantes, visitas,
  páginas vistas e páginas mais vistas nos últimos 7 dias, comparados com os 7 anteriores; cliques nos atalhos
  da página inicial (atalho_plano, atalho_diario, atalho_estudo), inscrições na newsletter (sign_up), ferramentas
  usadas, quem viu o fechamento do dia e alertas ativados.
- Inscritos na newsletter e no canal do Telegram (data/newsletter.json, data/telegram.json).
- Automações do GitHub que falharam na semana (API do Actions, com o GITHUB_TOKEN do próprio workflow).
Nada é gravado no repositório. SO_LOG=1 só mostra no log, sem enviar.
"""
import datetime as dt
import html
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from search_console import ler_chave, enviar  # noqa: E402

BRT = dt.timezone(dt.timedelta(hours=-3))
HOJE = dt.datetime.now(BRT).date()
FIM = HOJE - dt.timedelta(days=1)
INI = FIM - dt.timedelta(days=6)
INI_ANT, FIM_ANT = INI - dt.timedelta(days=7), INI - dt.timedelta(days=1)
PROP = os.environ.get('GA_PROPERTY_ID', '').strip() or '561843941'
REPO = os.environ.get('GITHUB_REPOSITORY', 'Antenornonato7/lectnex')
e = lambda s: html.escape(str(s), quote=False)
ATALHOS = [('atalho_plano', 'Preparar meu dia'), ('atalho_diario', 'Registrar operação'), ('atalho_estudo', 'Continuar estudando')]
OUTROS = [('sign_up', 'Inscrições na newsletter (formulário)'), ('ferramenta_usada', 'Ferramentas usadas'), ('fechamento_visto', 'Viram o fechamento do dia'),
          ('push_ativado', 'Ativaram alertas no celular'), ('menu_clique', 'Cliques no menu')]


def n(v):
    return f'{int(round(v)):,}'.replace(',', '.')


def var(a, b):
    if not b:
        return ''
    p = (a / b - 1) * 100
    return f' ({"+" if p >= 0 else "−"}{abs(p):.0f}%)'.replace('.', ',')


def sessao():
    bruto = os.environ.get('GSC_SERVICE_ACCOUNT', '').strip()
    if not bruto:
        return None
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
    cred = service_account.Credentials.from_service_account_info(ler_chave(bruto), scopes=['https://www.googleapis.com/auth/analytics.readonly'])
    return AuthorizedSession(cred)


def ga(s, corpo):
    r = s.post(f'https://analyticsdata.googleapis.com/v1beta/properties/{PROP}:runReport', json=corpo, timeout=60)
    if r.status_code >= 400:
        raise RuntimeError(f'HTTP {r.status_code}: {r.text[:300]}')
    return [([d['value'] for d in x.get('dimensionValues', [])], [float(m['value']) for m in x.get('metricValues', [])]) for x in r.json().get('rows', [])]


def periodos():
    return [{'startDate': INI.isoformat(), 'endDate': FIM.isoformat(), 'name': 'atual'},
            {'startDate': INI_ANT.isoformat(), 'endDate': FIM_ANT.isoformat(), 'name': 'anterior'}]


def bloco_analytics(s):
    L = []
    tot = ga(s, {'dateRanges': periodos(), 'metrics': [{'name': 'activeUsers'}, {'name': 'sessions'}, {'name': 'screenPageViews'}]})
    por = {d[-1] if d else 'atual': m for d, m in tot}
    a, b = por.get('atual', [0, 0, 0]), por.get('anterior', [0, 0, 0])
    L += ['<b>Visitas</b>',
          f'Visitantes: <b>{n(a[0])}</b>{var(a[0], b[0])}',
          f'Visitas: {n(a[1])}{var(a[1], b[1])} · páginas vistas: {n(a[2])}{var(a[2], b[2])}', '']
    pags = ga(s, {'dateRanges': periodos()[:1], 'dimensions': [{'name': 'pagePath'}], 'metrics': [{'name': 'screenPageViews'}],
                  'orderBys': [{'metric': {'metricName': 'screenPageViews'}, 'desc': True}], 'limit': 25})
    soma = {}
    for d, m in pags:  # "/" e "/index.html" são a mesma página (Mercado Hoje)
        k = 'Mercado Hoje' if d[0] in ('/', '/index.html') else d[0].lstrip('/').removesuffix('.html') or d[0]
        soma[k] = soma.get(k, 0) + m[0]
    top = sorted(soma.items(), key=lambda x: -x[1])[:7]
    if top:
        L += ['<b>Páginas mais vistas</b>'] + [f'{i}. {e(k)} · {n(v)}' for i, (k, v) in enumerate(top, 1)] + ['']
    nomes = [x for x, _ in ATALHOS + OUTROS]
    ev = ga(s, {'dateRanges': periodos()[:1], 'dimensions': [{'name': 'eventName'}], 'metrics': [{'name': 'eventCount'}, {'name': 'totalUsers'}],
                'dimensionFilter': {'filter': {'fieldName': 'eventName', 'inListFilter': {'values': nomes}}}})
    cont = {d[0]: m for d, m in ev}
    L += ['<b>Atalhos da página inicial</b>'] + [f'{rot}: {n(cont.get(k, [0, 0])[0])} cliques · {n(cont.get(k, [0, 0])[1])} pessoas' for k, rot in ATALHOS]
    extra = [f'{rot}: {n(cont.get(k, [0])[0])}' for k, rot in OUTROS if cont.get(k)]
    L += ([''] + extra if extra else []) + ['']
    return L


def bloco_inscritos():
    L = []
    for arq, chave, rot in (('data/newsletter.json', 'inscritos', 'Newsletter'), ('data/telegram.json', 'seguidores', 'Canal do Telegram')):
        try:
            v = json.load(open(arq, encoding='utf-8')).get(chave)
            if v is not None:
                L.append(f'{rot}: <b>{n(v)}</b>')
        except Exception:
            pass
    return (['<b>Inscritos</b>'] + L + ['']) if L else []


def bloco_falhas():
    token = os.environ.get('GITHUB_TOKEN', '')
    if not token:
        return []
    desde = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%SZ')
    url = f'https://api.github.com/repos/{REPO}/actions/runs?per_page=100&created=%3E{desde}'
    falhas, pagina = {}, 1
    while pagina <= 10:
        req = urllib.request.Request(url + f'&page={pagina}', headers={'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json'})
        runs = json.load(urllib.request.urlopen(req, timeout=30)).get('workflow_runs', [])
        for r in runs:
            if r.get('conclusion') in ('failure', 'timed_out', 'startup_failure'):
                falhas[r['name']] = falhas.get(r['name'], 0) + 1
        if len(runs) < 100:
            break
        pagina += 1
    if not falhas:
        return ['<b>Automações</b>', 'Nenhuma falha na semana. ✅', '']
    return ['<b>Automações que falharam</b>'] + [f'{e(k)}: {v}×' for k, v in sorted(falhas.items(), key=lambda x: -x[1])] + \
           ['(o Relógio tenta de novo sozinho; falha repetida já gera alerta)', '']


def main():
    L = [f'📊 <b>Resumo semanal do site</b>', f'{INI.strftime("%d/%m")} a {FIM.strftime("%d/%m")} (comparado com a semana anterior)', '']
    try:
        s = sessao()
        L += bloco_analytics(s) if s else ['Analytics: falta o segredo GSC_SERVICE_ACCOUNT.', '']
    except Exception as ex:
        print(f'::warning::Analytics: {ex}')
        L += [f'Analytics: não consegui ler ({e(str(ex)[:200])}).', '']
    L += bloco_inscritos()
    try:
        L += bloco_falhas()
    except Exception as ex:
        print(f'::warning::Actions: {ex}')
    L.append('<a href="https://analytics.google.com/">Abrir o Analytics</a>')
    texto = '\n'.join(L)
    print(texto)
    if os.environ.get('SO_LOG') == '1':
        print('SO_LOG=1: não enviado.')
        return
    enviar(texto)


if __name__ == '__main__':
    main()
