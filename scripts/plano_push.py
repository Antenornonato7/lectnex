"""Lembrete do Plano do Dia no celular (OneSignal), às 8h45 de Brasília nos dias de pregão (horário no Relógio).

Mostra o contrato vigente de WIN e WDO (com aviso de rolagem), os dados fortes do dia ainda por sair e abre
direto no Plano do Dia (futuros.html#plano).

Quem recebe: assinantes que marcaram "Plano do Dia às 8h45" no painel de alertas. Para não criar mais uma tag
no OneSignal (o plano grátis limita etiquetas por pessoa), a escolha vai na tag "leitura":
  0 = nenhum · 1 = só Leitura do Dia · 2 = Leitura + Plano · 3 = só Plano.
Idempotente por dia. TESTE=1 manda para todos os assinantes do Plano com o título marcado como teste.
"""
import datetime as dt, json, os, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'scripts'))
sys.path.insert(0, os.path.join(RAIZ, 'coletor'))
from ultimo_pregao import feriados, pregao

BRT = dt.timezone(dt.timedelta(hours=-3))
LETRA = 'FGHJKMNQUVXZ'
DIAS = ['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom']
FILTRO = [{'field': 'tag', 'key': 'leitura', 'relation': '=', 'value': '2'}, {'operator': 'OR'},
          {'field': 'tag', 'key': 'leitura', 'relation': '=', 'value': '3'}]


def prox_pregao(d, fer):
    while not pregao(d, fer):
        d += dt.timedelta(days=1)
    return d


def ant_pregao(d, fer):
    d -= dt.timedelta(days=1)
    while not pregao(d, fer):
        d -= dt.timedelta(days=1)
    return d


def vencimento_win(y, m, fer):
    """Quarta-feira mais próxima do dia 15 (mesma regra de LX.winExpiry); sem pregão → dia útil seguinte."""
    d15 = dt.date(y, m, 15)
    diff = (2 - d15.weekday()) % 7
    qua = d15 + dt.timedelta(days=diff if diff <= 3 else diff - 7)
    return prox_pregao(qua, fer)


def contratos(hoje, fer):
    """(código, último pregão) do WIN e do WDO vigentes, como LX.liveContracts (fechamento às 18h25 já tratado: 8h45 é antes)."""
    win = wdo = None
    for i in range(0, 14):
        y, m = hoje.year + (hoje.month - 1 + i) // 12, (hoje.month - 1 + i) % 12 + 1
        cod = f'{LETRA[m - 1]}{str(y)[2:]}'
        if win is None and m % 2 == 0:
            v = vencimento_win(y, m, fer)
            if v >= hoje:
                win = ('WIN' + cod, v)
        if wdo is None:
            ult = ant_pregao(prox_pregao(dt.date(y, m, 1), fer), fer)   # último pregão = dia útil antes do 1º dia útil do mês
            if ult >= hoje:
                wdo = ('WDO' + cod, ult)
        if win and wdo:
            return win, wdo
    return win, wdo


def hora(ev):
    h = str(ev.get('hora') or '')
    if 'h' not in h:
        return None
    hh, mm = (h.split('h') + [''])[:2]
    try:
        return int(hh) * 60 + int(mm or 0)
    except ValueError:
        return None


def montar(agora):
    hoje, fer = agora.date(), feriados()
    (win, win_v), (wdo, wdo_v) = contratos(hoje, fer)
    rola = [f'último pregão do {c} é hoje' for c, v in ((win, win_v), (wdo, wdo_v)) if v == hoje]
    rola += [f'último pregão do {c} é amanhã' for c, v in ((win, win_v), (wdo, wdo_v)) if v == prox_pregao(hoje + dt.timedelta(days=1), fer)]
    try:
        cal = json.load(open(os.path.join(RAIZ, 'data/calendario.json'), encoding='utf-8')).get('eventos', [])
    except Exception:
        cal = []
    ja = agora.hour * 60 + agora.minute
    fortes = sorted([e for e in cal if e.get('data') == hoje.isoformat() and (e.get('importancia') or 0) >= 3 and (hora(e) or 0) >= ja and not e.get('resultado')],
                    key=lambda e: hora(e) or 0)
    partes = [f'{win} · {wdo}' + (f' ({"; ".join(rola)})' if rola else '')]
    if fortes:
        lista = ', '.join(f'{e["hora"]} {e["evento"].split(" — ")[0].split(" (")[0]}' for e in fortes[:3])
        partes.append(('Hoje: ' + lista + (f' e mais {len(fortes) - 3}' if len(fortes) > 3 else ''))[:150])
    else:
        partes.append('Sem dado forte agendado para hoje.')
    partes.append('Defina seu limite de perda antes da abertura.')
    return f'📋 Plano do Dia · {DIAS[hoje.weekday()]} {hoje:%d/%m}', ' '.join(p if p.endswith('.') else p + '.' for p in partes)


def main():
    agora = dt.datetime.now(BRT)
    teste = os.environ.get('TESTE') == '1'
    if not teste and not pregao(agora.date()):
        print('Sem pregão hoje: lembrete não enviado.')
        return
    titulo, texto = montar(agora)
    if teste:
        titulo = '✅ Teste · ' + titulo
    print(titulo); print(texto)
    import push
    if not push.APP or not push.KEY:
        print('::notice::OneSignal não configurado: nada enviado.')
        return
    chave = f'plano-{agora.date().isoformat()}' + (f'-teste-{agora:%H%M%S}' if teste else '')
    push.enviar('plano', titulo, texto, push.tg.SITE + 'futuros.html#plano', chave, filtros=FILTRO)


if __name__ == '__main__':
    main()
