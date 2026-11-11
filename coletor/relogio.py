"""Relógio do Lectnex: o único agendador do site.

Se uma tarefa falha, tenta de novo uma vez (3 min depois, dentro da janela). Se falhar duas vezes seguidas, avisa no
chat privado do Telegram pelo workflow "Alerta de falha" (um aviso por falha) e não insiste até o próximo horário.

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
    try:  # feriados da B3 pela mesma regra do site (independe de o calendário já trazer o feriado)
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))
        from ultimo_pregao import feriados
        if AGORA.date().isoformat() in feriados():
            return False
    except Exception:
        pass
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
    ('kit.yml', 'Kit do dia', {}, ('horarios', ['19:32'], 150), lambda: UTIL),
    ('plano-push.yml', 'Plano do Dia', {'teste': 'false'}, ('horarios', ['08:45'], 25), lambda: PREGAO),
    ('lembrete.yml', 'Lembrete manha', {'momento': 'manha'}, ('horarios', ['08:30'], 50), lambda: PREGAO),
    ('lembrete.yml', 'Lembrete noite', {'momento': 'noite'}, ('horarios', ['20:00'], 50), lambda: PREGAO),
    ('lembrete.yml', 'Lembrete fds', {'momento': 'fds'}, ('horarios', ['10:05'], 50), lambda: not PREGAO),
    ('lembrete.yml', 'Lembrete domingo', {'momento': 'domingo'}, ('horarios', ['18:00'], 50), lambda: not PREGAO and AGORA.weekday() != 5),
    ('checar-resultados.yml', 'Conferir resultados', {}, ('horarios', ['21:45'], 120), lambda: UTIL),
    ('telegram.yml', 'Telegram contar', {'acao': 'contar'}, ('horarios', ['08:17'], 240), lambda: True),
    ('termo.yml', None, {}, ('horarios', ['08:05'], 240), lambda: True),
    ('sinais.yml', 'Sinais da manhã', {}, ('horarios', ['07:22'], 25), lambda: PREGAO),
    ('instagram.yml', 'Instagram renovar', {'acao': 'renovar'}, ('horarios', ['06:47'], 240), lambda: AGORA.weekday() == 0),
    ('antes.yml', 'Antes do dado', {'enviar': 'true'}, ('horarios', ['07:20'], 180), lambda: UTIL),
    ('coletor-cvm.yml', None, {}, ('horarios', ['07:17'], 360), lambda: AGORA.weekday() in (1, 2, 3, 4, 5)),
    ('semanal.yml', 'Resumo semanal enviar', {'enviar': 'true'}, ('horarios', ['10:17'], 360), lambda: AGORA.weekday() == 6),
    ('search-console.yml', 'Search Console semanal', {'teste': 'false'}, ('horarios', ['09:12'], 360), lambda: AGORA.weekday() == 0),
    ('teste-menu.yml', 'Teste do menu semanal', {'teste': 'false'}, ('horarios', ['09:27'], 360), lambda: AGORA.weekday() == 0 and AGORA.date() <= dt.date(2026, 12, 1)),
    ('carrossel.yml', 'Carrossel da semana', {'previa': 'false'}, ('horarios', ['09:47'], 360), lambda: AGORA.weekday() == 5),
    ('resumo-site.yml', 'Resumo semanal do site', {'enviar': 'true'}, ('horarios', ['11:07'], 360), lambda: AGORA.weekday() == 6),
]


FALHA = ('failure', 'timed_out', 'startup_failure')
ESPERA_RETENTAR = 3   # minutos depois de uma falha antes de tentar de novo


def quando(iso):
    return dt.datetime.fromisoformat(iso.replace('Z', '+00:00')).astimezone(BRT)


def ultimas(arq, titulo):
    """Execuções recentes da tarefa, da mais nova para a mais antiga: {t, fim, estado}.
    estado: 'ok' (sucesso), 'falha', 'andando' (na fila ou rodando). Canceladas são ignoradas: o cancelamento
    acontece quando uma execução mais nova da mesma tarefa toma o lugar dela."""
    runs = api(f'{API}/{arq}/runs?per_page=15').get('workflow_runs', [])
    out = []
    for r in runs:
        if r.get('event') not in ('schedule', 'workflow_dispatch'):
            continue
        if titulo and not (r.get('display_title') or '').startswith(titulo):
            continue
        if r.get('status') != 'completed':
            estado = 'andando'
        elif r.get('conclusion') in FALHA:
            estado = 'falha'
        elif r.get('conclusion') == 'cancelled':
            continue
        else:
            estado = 'ok'
        out.append({'t': quando(r['created_at']), 'fim': quando(r.get('updated_at') or r['created_at']), 'estado': estado, 'url': r.get('html_url', '')})
    return sorted(out, key=lambda x: x['t'], reverse=True)


def devida(regra, runs):
    """(disparar?, motivo, alerta). Depois de UMA falha, tenta de novo (passados ESPERA_RETENTAR min).
    Depois de DUAS falhas seguidas, não insiste e devolve um alerta para o chat privado."""
    recente = lambda x: (AGORA - x['fim']).total_seconds() / 60 >= ESPERA_RETENTAR
    if regra[0] == 'intervalo':
        if not runs:
            return True, f'a cada {regra[1]} min', None
        seq = []
        for x in runs:   # falhas seguidas mais recentes
            if x['estado'] != 'falha':
                break
            seq.append(x)
        if runs[0]['estado'] == 'andando':
            return False, 'rodando agora', None
        if len(seq) >= 2:
            # continua no ritmo normal (fontes de dados voltam sozinhas), mas avisa uma vez por sequência de falhas
            alerta = {'chave': seq[-1]['t'].strftime('%Y-%m-%d %H:%M'), 'falhas': len(seq), 'url': seq[0]['url'], 'segue': True}
            return (AGORA - runs[0]['t']).total_seconds() / 60 >= regra[1], f'{len(seq)} falhas seguidas', alerta
        if len(seq) == 1 and recente(seq[0]):
            return True, 'tentando de novo após falha', None
        return (AGORA - runs[0]['t']).total_seconds() / 60 >= regra[1], f'a cada {regra[1]} min', None
    horarios, janela = regra[1], regra[2]
    passados = [hm(h) for h in horarios if hm(h) <= AGORA <= hm(h) + dt.timedelta(minutes=janela)]
    if not passados:
        return False, 'fora do horário', None
    slot = max(passados)
    deste = [x for x in runs if x['t'] >= slot - dt.timedelta(minutes=3)]
    if not deste:
        return True, f'horário {slot:%H:%M}', None
    if any(x['estado'] in ('ok', 'andando') for x in deste):
        return False, f'horário {slot:%H:%M}', None
    falhas = [x for x in deste if x['estado'] == 'falha']
    if len(falhas) >= 2:
        return False, f'horário {slot:%H:%M}: {len(falhas)} falhas, sem nova tentativa', {'chave': slot.strftime('%Y-%m-%d %H:%M'), 'falhas': len(falhas), 'url': falhas[0]['url']}
    if recente(falhas[0]):
        return True, f'horário {slot:%H:%M}: tentando de novo após falha', None
    return False, f'horário {slot:%H:%M}: falhou, nova tentativa em instantes', None


NOMES = {'cotacoes.yml': 'Cotações das ações', 'monitor.yml': 'Monitor do site', 'noticias.yml': 'Notícias', 'curva.yml': 'Curva de juros',
         'reacao.yml': 'Reação do mercado', 'fechamento.yml': 'Fechamento do dia', 'resumo-dono.yml': 'Resumo do dono', 'kit.yml': 'Kit do dia',
         'lembrete.yml': 'Lembrete', 'checar-resultados.yml': 'Conferir resultados', 'telegram.yml': 'Contagem do Telegram', 'termo.yml': 'Termômetro',
         'sinais.yml': 'Sinais da manhã', 'instagram.yml': 'Instagram', 'antes.yml': 'Antes do dado', 'coletor-cvm.yml': 'Coletor CVM',
         'semanal.yml': 'Resumo semanal', 'carrossel.yml': 'Carrossel da semana', 'search-console.yml': 'Relatório do Google', 'teste-menu.yml': 'Teste do menu', 'resumo-site.yml': 'Resumo semanal do site', 'plano-push.yml': 'Lembrete do Plano do Dia (8h45)'}


def alertar(arq, titulo, al):
    """Dispara o workflow "Alerta de falha" uma única vez por falha (o título da execução é a chave)."""
    chave = f"{arq.replace('.yml', '')}{' · ' + titulo if titulo else ''} · {al['chave']}"
    ja = api(f'{API}/alerta.yml/runs?per_page=30').get('workflow_runs', [])
    if any((r.get('display_title') or '') == f'Alerta {chave}' for r in ja):
        return False
    nome = NOMES.get(arq, arq) + (f' ({titulo})' if titulo and NOMES.get(arq) == 'Lembrete' else '')
    texto = (f"⚠️ Lectnex: {nome} falhou {al['falhas']} vezes seguidas (desde {al['chave'][-5:]}).\n"
             + ('Ela continua rodando no ritmo normal; aviso só uma vez até voltar a funcionar.' if al.get('segue') else 'O Relógio parou de insistir nesta tarefa até o próximo horário.')
             + f" Log da última falha: {al['url']}")
    if not DRY:
        api(f'{API}/alerta.yml/dispatches', {'ref': 'main', 'inputs': {'chave': chave, 'texto': texto}})
    return True


def main():
    print(f'Relógio {AGORA:%a %d/%m %H:%M} (Brasília) · pregão hoje: {"sim" if PREGAO else "não"}')
    disparadas, alertas = [], []
    for arq, titulo, inputs, regra, janela in TAREFAS:
        if not janela():
            continue
        try:
            runs = ultimas(arq, titulo)
            ok, motivo, alerta = devida(regra, runs)
            if alerta and alertar(arq, titulo, alerta):
                print(f'::warning::{arq}: {alerta["falhas"]} falhas seguidas, alerta enviado')
                alertas.append(arq)
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
            f.write(f"### Relógio {AGORA:%d/%m %H:%M}\n\n" + ('Disparadas: ' + ', '.join(disparadas) if disparadas else 'Nada devido agora.') + ('\n\nAlertas de falha: ' + ', '.join(alertas) if alertas else '') + '\n')


if __name__ == '__main__':
    main()
