"""Reação histórica dos dados econômicos → data/reacoes.json.

Para cada evento do calendário com horário e resultado já divulgado, mede a variação do Ibovespa à vista (proxy do WIN)
e do dólar à vista (proxy do WDO) entre o último preço antes da divulgação e 30 minutos depois (ou a abertura seguinte,
quando o dado sai com o mercado fechado). Cotações de 5 min do Yahoo Finance (não oficiais). Só guardamos a variação
calculada, não as cotações.
"""
import datetime as dt, json, os, re, unicodedata, urllib.request

BRT = dt.timezone(dt.timedelta(hours=-3))
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36', 'Accept': 'application/json,*/*'}
ATIVOS = {'win': '%5EBVSP', 'wdo': 'BRL%3DX'}
SAIDA = 'data/reacoes.json'


def note(k, m):
    print(f'::{k}::{m}')


def tipo(ev):
    if ev.get('tipo'):
        return ev['tipo']
    n = re.sub(r'\(.*?\)', '', ev.get('evento', ''))
    n = unicodedata.normalize('NFD', n.lower()).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', n).strip('-')[:40]


def barras(sym):
    erro = None
    for host in ('query2', 'query1'):
        try:
            url = f'https://{host}.finance.yahoo.com/v8/finance/chart/{sym}?interval=5m&range=60d'
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                j = json.load(r)['chart']['result'][0]
            break
        except Exception as e:
            erro = e
    else:
        raise erro
    ts, cl = j['timestamp'], j['indicators']['quote'][0]['close']
    return [(t, c) for t, c in zip(ts, cl) if c is not None]


def var(bs, t0, minutos=30):
    antes = [(t, c) for t, c in bs if t <= t0]
    depois = [(t, c) for t, c in bs if t >= t0 + minutos * 60]
    if not antes or not depois:
        return None, None
    ta, ca = antes[-1]
    t1, c1 = depois[0]
    # mercado fechado na hora do dado (último preço muito antes, ou primeiro preço depois muito tarde) = medido na abertura
    fechado = (t0 - ta) > 15 * 60 or (t1 - t0) > 45 * 60
    return round((c1 / ca - 1) * 100, 3), fechado


def hora_ev(ev):
    m = re.match(r'^(\d{1,2})h(\d{2})?$', str(ev.get('hora') or '').strip())
    if not m:
        return None
    d = dt.date.fromisoformat(ev['data'])
    return int(dt.datetime(d.year, d.month, d.day, int(m.group(1)), int(m.group(2) or 0), tzinfo=BRT).timestamp())


def main():
    try:
        base = json.load(open(SAIDA, encoding='utf-8'))
    except Exception:
        base = {'metodo': 'Variação do último preço antes da divulgação até 30 min depois (ou a abertura seguinte). WIN pelo Ibovespa à vista, WDO pelo dólar à vista (BRL=X). Cotações de 5 min do Yahoo Finance.', 'registros': []}
    feitos = {r['id'] for r in base['registros']}
    evs = []
    for f in ['data/calendario.json', 'data/reacoes-historico.json'] + sorted(__import__('glob').glob('data/semana/*.json'))[-2:]:
        try:
            evs += json.load(open(f, encoding='utf-8')).get('eventos', [])
        except Exception:
            pass
    agora = dt.datetime.now(BRT).timestamp()
    pend = []
    for ev in evs:
        t0 = hora_ev(ev) if ev.get('data') else None
        if not t0 or (ev.get('importancia') or 1) < 2 or ev.get('resultado') in (None, ''):
            continue
        rid = f"{ev['data']}|{ev.get('hora')}|{tipo(ev)}"
        if rid in feitos or t0 > agora - 40 * 60 or t0 < agora - 58 * 86400:
            continue
        feitos.add(rid); pend.append((rid, t0, ev))
    if not pend:
        note('notice', 'Reação: nenhum evento novo para medir.'); return
    try:
        bs = {k: barras(s) for k, s in ATIVOS.items()}
    except Exception as e:
        note('warning', f'Cotações intradiárias indisponíveis: {type(e).__name__}'); return
    novos = 0
    for rid, t0, ev in pend:
        r = {'id': rid, 'data': ev['data'], 'hora': ev.get('hora'), 'tipo': tipo(ev), 'evento': ev['evento'], 'pais': ev.get('pais'),
             'resultado': ev.get('resultado'), 'consenso': ev.get('consenso'),
             'surpresa': (ev.get('surpresa') or {}).get('direcao') if ev.get('surpresa') else ('em linha' if ev.get('consenso') and str(ev.get('consenso')) == str(ev.get('resultado')) else None)}
        for k in ATIVOS:
            v, fechado = var(bs[k], t0)
            r[k] = v
            if v is not None and fechado:
                r[k + '_abertura'] = True  # mercado fechado na hora: inclui o gap da abertura
        if r['win'] is None and r['wdo'] is None:
            continue
        base['registros'].append(r); novos += 1
    base['registros'] = sorted(base['registros'], key=lambda r: r['id'])[-2000:]
    base['atualizado_em'] = dt.datetime.now(BRT).isoformat(timespec='seconds')
    json.dump(base, open(SAIDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    note('notice', f'Reação: {novos} evento(s) medidos; total {len(base["registros"])}')


if __name__ == '__main__':
    if os.environ.get('TESTE'):
        for k, s in ATIVOS.items():
            try:
                b = barras(s); note('notice', f'{k}: {len(b)} barras, última {dt.datetime.fromtimestamp(b[-1][0], BRT):%d/%m %H:%M}')
            except Exception as e:
                note('warning', f'{k}: {type(e).__name__} {str(e)[:80]}')
    else:
        main()
