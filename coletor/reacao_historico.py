"""Histórico longo de reação (roda uma vez, sob demanda): mede WIN/WDO nas divulgações de ~2 anos atrás → data/reacoes.json.

O Yahoo Finance só entrega barras de 5 min dos últimos 60 dias, mas guarda barras de 1 hora de ~730 dias. Para as
divulgações mais antigas que o histórico de 30 min, medimos do último preço antes da divulgação até o primeiro preço
1 hora depois (ou a abertura seguinte, se o mercado estava fechado). Esses registros levam "janela": "1h".
Nunca substitui um registro já medido em 30 min (mesmo dia e mesmo tipo).

Datas (todas conferidas na fonte oficial em 04/11/2026):
  - Payroll e CPI: calendários do BLS (bls.gov/schedule/2025, /2026 e bls.gov/bls/2025-lapse-revised-release-dates.htm),
    8h30 de Nova York. Out/2025 cancelados pela paralisação do governo.
  - FOMC: calendário do Federal Reserve, 14h de Nova York.  - Copom: calendário do BCB, comunicado às 18h30 de Brasília.
  - IPCA e IPCA-15: API de calendário do IBGE (servicodados.ibge.gov.br/api/v3/calendario), 9h de Brasília.
"""
import datetime as dt
import json
import os
import urllib.request
from zoneinfo import ZoneInfo

BRT = dt.timezone(dt.timedelta(hours=-3))
NY = ZoneInfo('America/New_York')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36', 'Accept': 'application/json,*/*'}
SAIDA = 'data/reacoes.json'

PAYROLL = ['2024-11-01', '2024-12-06', '2025-01-10', '2025-02-07', '2025-03-07', '2025-04-04', '2025-05-02', '2025-06-06', '2025-07-03',
           '2025-08-01', '2025-09-05', '2025-11-20', '2025-12-16', '2026-01-09', '2026-02-11', '2026-03-06', '2026-04-03', '2026-05-08',
           '2026-06-05', '2026-07-02', '2026-08-07']
CPI = ['2024-11-13', '2024-12-11', '2025-01-15', '2025-02-12', '2025-03-12', '2025-04-10', '2025-05-13', '2025-06-11', '2025-07-15',
       '2025-08-12', '2025-09-11', '2025-10-24', '2025-12-18', '2026-01-13', '2026-02-13', '2026-03-11', '2026-04-10', '2026-05-12',
       '2026-06-10', '2026-07-14', '2026-08-12']
FOMC = [('2024-11-07', 'corte para 4,50%–4,75%'), ('2024-12-18', 'corte para 4,25%–4,50%'), ('2025-01-29', 'manutenção em 4,25%–4,50%'),
        ('2025-03-19', 'manutenção em 4,25%–4,50%'), ('2025-05-07', 'manutenção em 4,25%–4,50%'), ('2025-06-18', 'manutenção em 4,25%–4,50%'),
        ('2025-07-30', 'manutenção em 4,25%–4,50%'), ('2025-09-17', 'corte para 4,00%–4,25%'), ('2025-10-29', 'corte para 3,75%–4,00%'),
        ('2025-12-10', 'corte para 3,50%–3,75%'), ('2026-01-28', None), ('2026-03-18', None), ('2026-04-29', None), ('2026-06-17', None),
        ('2026-07-29', None)]
COPOM = [('2024-11-06', '11,25% (+0,50)'), ('2024-12-11', '12,25% (+1,00)'), ('2025-01-29', '13,25% (+1,00)'), ('2025-03-19', '14,25% (+1,00)'),
         ('2025-05-07', '14,75% (+0,50)'), ('2025-06-18', '15,00% (+0,25)'), ('2025-07-30', '15,00% (manutenção)'),
         ('2025-09-17', '15,00% (manutenção)'), ('2025-11-05', '15,00% (manutenção)'), ('2025-12-10', '15,00% (manutenção)'),
         ('2026-01-28', '15,00% (manutenção)'), ('2026-03-18', '14,75% (−0,25)'), ('2026-04-29', '14,50% (−0,25)'),
         ('2026-06-17', '14,25% (−0,25)'), ('2026-08-05', '14,00% (−0,25)')]
# Reserva quando a API do IBGE não responde (ela costuma recusar conexões de fora do Brasil). 2026: calendário oficial
# do IBGE para 2026; 2025: 12/03 e 11/04 conferidos nos releases do IBGE, demais no calendário anual de divulgação.
IPCA = ['2024-11-08', '2024-12-10', '2025-01-10', '2025-02-11', '2025-03-12', '2025-04-11', '2025-05-09', '2025-06-10', '2025-07-10',
        '2025-08-12', '2025-09-10', '2025-10-09', '2025-11-11', '2025-12-10', '2026-01-09', '2026-02-10', '2026-03-12', '2026-04-10',
        '2026-05-12', '2026-06-12', '2026-07-10', '2026-08-11']
MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']


def note(k, m):
    print(f'::{k}::{m}')


def ny(d, h, m):
    y, mo, da = map(int, d.split('-'))
    return dt.datetime(y, mo, da, h, m, tzinfo=NY).astimezone(BRT)


def brt(d, h, m):
    y, mo, da = map(int, d.split('-'))
    return dt.datetime(y, mo, da, h, m, tzinfo=BRT)


def ref(d, atraso=1):
    """Mês de referência aproximado (mês anterior à divulgação)."""
    y, m = int(d[:4]), int(d[5:7]) - atraso
    return MESES[(m - 1) % 12]


def ibge(produto, nome, tipo):
    """Datas de divulgação pela API de calendário do IBGE."""
    out = []
    for pag in range(1, 6):
        url = f'https://servicodados.ibge.gov.br/api/v3/calendario/{produto}?de=10-01-2024&ate=08-31-2026&qtd=50&page={pag}'
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=12) as r:
                j = json.load(r)
        except Exception as e:
            note('warning', f'IBGE {nome}: {type(e).__name__} {str(e)[:80]}')
            break
        itens = j.get('items', []) if isinstance(j, dict) else j
        for it in itens:
            s = it.get('data_divulgacao') or ''
            try:
                quando = dt.datetime.strptime(s[:16], '%d/%m/%Y %H:%M').replace(tzinfo=BRT)
            except ValueError:
                continue
            if quando.hour == 0:
                quando = quando.replace(hour=9)
            tit = (it.get('titulo') or '').lower()
            if 'ipca-e' in tit or 'inpc' in tit and 'ipca' not in tit:
                continue
            out.append((tipo, f'{nome} ({MESES[(quando.month - 2) % 12] if tipo == "ipca" else MESES[(quando.month - 1) % 12]})', quando, None))
        if not isinstance(j, dict) or pag >= (j.get('totalPages') or 1):
            break
    vistos, unicos = set(), []
    for x in sorted(out, key=lambda x: x[2]):
        if x[2].date() not in vistos:
            vistos.add(x[2].date()); unicos.append(x)
    note('notice', f'IBGE {nome}: {len(unicos)} divulgação(ões)')
    return unicos


def barras(sym):
    erro = None
    for host in ('query2', 'query1'):
        try:
            url = f'https://{host}.finance.yahoo.com/v8/finance/chart/{sym}?interval=60m&range=730d'
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                j = json.load(r)['chart']['result'][0]
            break
        except Exception as e:
            erro = e
    else:
        raise erro
    q = j['indicators']['quote'][0]
    pts = []
    for t, o, c in zip(j['timestamp'], q['open'], q['close']):
        if o is not None:
            pts.append((t, o, True))       # abertura da barra
        if c is not None:
            pts.append((t + 3600, c, False))  # fechamento da barra (1 h depois)
    pts.sort()
    return pts


def var(pts, t0):
    antes = [p for p in pts if p[0] <= t0]
    depois = [p for p in pts if p[0] >= t0 + 3600]
    if not antes or not depois:
        return None, None
    ta, ca, _ = antes[-1]
    t1, c1, _ = depois[0]
    if t1 - t0 > 4 * 86400 or t0 - ta > 4 * 86400:
        return None, None
    fechado = (t0 - ta) > 75 * 60 or (t1 - t0) > 135 * 60
    return round((c1 / ca - 1) * 100, 3), fechado


def main():
    base = json.load(open(SAIDA, encoding='utf-8'))
    tem = {(r['data'], r['tipo']) for r in base['registros']}
    evs = [('payroll', f'Payroll — criação de vagas ({ref(d)})', ny(d, 8, 30), None) for d in PAYROLL]
    evs += [('cpi-eua', f'CPI — inflação ao consumidor ({ref(d)})', ny(d, 8, 30), None) for d in CPI]
    evs += [('fomc', 'Decisão do FOMC (Fed)', ny(d, 14, 0), r) for d, r in FOMC]
    evs += [('copom', 'Decisão do Copom', brt(d, 18, 30), r) for d, r in COPOM]
    ipca = ibge(9256, 'IPCA', 'ipca')
    evs += ipca or [('ipca', f'IPCA ({ref(d)})', brt(d, 9, 0), None) for d in IPCA]
    evs += ibge(9260, 'IPCA-15', 'ipca-15')
    try:
        bs = {'win': barras('%5EBVSP'), 'wdo': barras('BRL%3DX')}
    except Exception as e:
        note('error', f'Cotações de 1 hora indisponíveis: {type(e).__name__}'); raise SystemExit(1)
    for k, p in bs.items():
        note('notice', f'{k}: barras de 1 h desde {dt.datetime.fromtimestamp(p[0][0], BRT):%d/%m/%Y}')
    novos, pulados = 0, 0
    for tp, nome, quando, resultado in evs:
        d = quando.date().isoformat()
        if (d, tp) in tem or quando >= dt.datetime(2026, 9, 1, tzinfo=BRT):
            pulados += 1
            continue
        hora = f'{quando:%H}h{quando:%M}'.replace('h00', 'h')
        r = {'id': f'{d}|{hora}|{tp}', 'data': d, 'hora': hora, 'tipo': tp, 'evento': nome, 'pais': 'BR' if tp in ('copom', 'ipca', 'ipca-15') else 'US',
             'resultado': resultado, 'consenso': None, 'surpresa': None, 'janela': '1h'}
        t0 = int(quando.timestamp())
        for k in bs:
            v, fechado = var(bs[k], t0)
            r[k] = v
            if v is not None and fechado:
                r[k + '_abertura'] = True
        if r['win'] is None and r['wdo'] is None:
            continue
        base['registros'].append(r); tem.add((d, tp)); novos += 1
    base['registros'] = sorted(base['registros'], key=lambda r: r['id'])
    base['metodo'] = ('Variação do último preço antes da divulgação até 30 min depois (ou a abertura seguinte). WIN pelo Ibovespa à vista, '
                      'WDO pelo dólar à vista (BRL=X). Cotações de 5 min do Yahoo Finance. Registros com "janela": "1h" (antes de set/2026) '
                      'usam barras de 1 hora: do último preço antes até 1 hora depois.')
    base['atualizado_em'] = dt.datetime.now(BRT).isoformat(timespec='seconds')
    json.dump(base, open(SAIDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    por = {}
    for r in base['registros']:
        por[r['tipo']] = por.get(r['tipo'], 0) + 1
    note('notice', f'Histórico: {novos} divulgação(ões) novas, {pulados} já existiam. Total por tipo: {por}')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8').write(f'### Histórico de reação\n\n{novos} novas. Por tipo: {por}\n')


if __name__ == '__main__':
    main()
