"""Relógio do Lectnex: o único agendador do site.

Roda a cada ~10-30 min (agendamento do próprio GitHub e/ou um "pinger" externo que dispara este workflow)
e decide, pelo horário de Brasília, quais tarefas estão devidas. Dispara cada uma por workflow_dispatch.
É idempotente: se a tarefa já rodou no horário (ou está na fila), não dispara de novo — então pode ser
chamado várias vezes sem duplicar Telegram, fechamento etc.

Precisa de GITHUB_TOKEN com actions:write (o próprio do workflow). DRY=1 só mostra o que faria.
"""
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request

BRT = dt.timezone(dt.timedelta(hours=-3))
AGORA = dt.datetime.now(BRT)
REPO = os.environ.get('GITHUB_REPOSITORY', 'Antenornonato7/lectnex')
TOKEN = os.environ.get('GITHUB_TOKEN', '')
DRY = os.environ.get('DRY') == '1'
API = f'https://api.github.com/repos/{REPO}/actions/workflows'


def api(url, dados=None):
    req = urllib.request.Request(url, data=json.dumps(dados).encode() if dados is not None else None,
                                 headers={'Authorization': f'Bearer {TOKEN}', 'Accept': 'application/vnd.github+json',
                                          'X-GitHub-Api-Version': '2022-11-28'}, method='POST' if dados is not None else 'GET')
    with urllib.request.urlopen(req, timeout=20) as r:
        corpo = r.read()
        return json.loads(corpo) if corpo else {}


def pregao_hoje():
    if AGORA.weekday() >= 5:
        return False
    try:
        cal = json.load(open('data/calendario.json', encoding='utf-8'))
        return not any(e.get('data') == AGORA.date().isoformat() and 'B3 fechada' in (e.get('evento') or '') for e in cal.get('eventos', []))
    except Exception:
        return True


def hm(s):
    h, m = map(int, s.split(':'))
    return AGORA.replace(hour=h, minute=m, second=0, microsecond=0)


# (arquivo, título da execução que conta como "já rodou", inputs, regra)
# regra: ('intervalo', minutos, janela) | ('horarios', [hh:mm...], janela_min) ; janela = função -> bool
PREGAO = pregao_hoje()
UTIL = AGORA.weekday() < 5
TAREFAS = [
    ('cotacoes.yml', None, {'forcar_mapa': 'false'}, ('intervalo', 25), lambda: PREGAO and hm('10:05') <= AGORA <= hm('18:50')),
    ('monitor.yml', 'Monitor do site', {'teste': 'false'}, ('intervalo', 55), lambda: True),
    ('noticias.yml', None, {}, ('intervalo', 9), lambda: 6 <= AGORA.hour <= 23),
    ('curva.yml', None, {}, ('horarios', ['10:23', '13:23', '16:23', '18:23'], 120), lambda: UTIL),
    ('reacao.yml', None, {'teste': 'false'}, ('horarios', ['12:41', '19:41'], 150), lambda: UTIL),
    ('fechamento.yml', None, {'forcar': 'false'}, ('horarios', ['19:05'], 180), lambda: PREGAO),
    ('resumo-dono.yml', 'Resumo do dia', {'teste': 'false'}, ('horarios', ['19:25'], 240), lambda: True),
    ('telegram.yml', 'Telegram contar', {'acao': 'contar'}, ('horarios', ['08:17'], 240), lambda: True),
    ('termo.yml', None, {}, ('horarios', ['08:05'], 240), lambda: True),
    ('antes.yml', 'Antes do dado', {'enviar': 'true'}, ('horarios', ['07:20'], 180), lambda: UTIL),
    ('coletor-cvm.yml', None, {}, ('horarios', ['07:17'], 360), lambda: AGORA.weekday() in (1, 2, 3, 4, 5)),
    ('semanal.yml', 'Resumo semanal enviar', {'enviar': 'true'}, ('horarios', ['10:17'], 360), lambda: AGORA.weekday() == 6),
    ('carrossel.yml', 'Carrossel da semana', {'previa': 'false'}, ('horarios', ['09:47'], 360), lambda: AGORA.weekday() == 5),
]


def ultimas(arq, titulo):
    runs = api(f'{API}/{arq}/runs?per_page=15').get('workflow_runs', [])
    out = []
    for r in runs:
        if r.get('event') not in ('schedule', 'workflow_dispatch'):
            continue
        if titulo and not (r.get('display_title') or '').startswith(titulo):
            continue
        out.append(dt.datetime.fromisoformat(r['created_at'].replace('Z', '+00:00')).astimezone(BRT))
    return out


def devida(regra, runs):
    if regra[0] == 'intervalo':
        return not runs or (AGORA - max(runs)).total_seconds() / 60 >= regra[1], f'a cada {regra[1]} min'
    horarios, janela = regra[1], regra[2]
    passados = [hm(h) for h in horarios if hm(h) <= AGORA <= hm(h) + dt.timedelta(minutes=janela)]
    if not passados:
        return False, 'fora do horário'
    slot = max(passados)
    return not any(t >= slot - dt.timedelta(minutes=3) for t in runs), f'horário {slot:%H:%M}'


def main():
    print(f'Relógio {AGORA:%a %d/%m %H:%M} (Brasília) · pregão hoje: {"sim" if PREGAO else "não"}')
    disparadas = []
    for arq, titulo, inputs, regra, janela in TAREFAS:
        if not janela():
            continue
        try:
            runs = ultimas(arq, titulo)
            ok, motivo = devida(regra, runs)
        except urllib.error.HTTPError as ex:
            print(f'::warning::{arq}: não consegui ler as execuções (HTTP {ex.code})')
            continue
        if not ok:
            print(f'  · {arq}: em dia ({motivo})')
            continue
        print(f'  → {arq}: disparando ({motivo})')
        if not DRY:
            try:
                api(f'{API}/{arq}/dispatches', {'ref': 'main', 'inputs': inputs})
                disparadas.append(arq)
            except urllib.error.HTTPError as ex:
                print(f'::error::{arq}: falhou ao disparar (HTTP {ex.code}: {ex.read().decode()[:160]})')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as f:
            f.write(f"### Relógio {AGORA:%d/%m %H:%M}\n\n" + ('Disparadas: ' + ', '.join(disparadas) if disparadas else 'Nada devido agora.') + '\n')


if __name__ == '__main__':
    main()
