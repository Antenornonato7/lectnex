"""Pregões extras para o Simulador de pregão: baixa do Yahoo Finance as barras de 5 min dos últimos 60 dias do Ibovespa (^BVSP) e
do dólar (BRL=X) e grava data/sim/AAAA-MM-DD.json (mesmo formato de data/dias, sem manchetes) + data/sim/indice.json.
Dias que já estão em data/dias (com manchetes) não são duplicados. Uso: python3 scripts/simulador_historico.py
"""
import datetime as dt
import json
import os
import urllib.request

BRT = dt.timezone(dt.timedelta(hours=-3))
RAIZ = os.path.join(os.path.dirname(__file__), '..')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36'}


def baixar(sym):
    for host in ('query2', 'query1'):
        try:
            req = urllib.request.Request(f'https://{host}.finance.yahoo.com/v8/finance/chart/{sym}?interval=5m&range=60d', headers=UA)
            res = json.load(urllib.request.urlopen(req, timeout=40))['chart']['result'][0]
            por_dia = {}
            for t, c in zip(res['timestamp'], res['indicators']['quote'][0]['close']):
                if c is None:
                    continue
                h = dt.datetime.fromtimestamp(t, BRT)
                por_dia.setdefault(h.date().isoformat(), []).append([h.strftime('%H:%M'), round(c, 2 if sym.startswith('%5E') else 4)])
            return por_dia
        except Exception as e:
            print(f'::warning::{sym} via {host}: {e}')
    return {}


def main():
    ib, dl = baixar('%5EBVSP'), baixar('BRL%3DX')
    pasta = os.path.join(RAIZ, 'data', 'sim')
    os.makedirs(pasta, exist_ok=True)
    com_manchetes = set(json.load(open(os.path.join(RAIZ, 'data', 'dias', 'indice.json'), encoding='utf-8')).get('dias', []))
    dias_ib = sorted(ib)
    hoje = dt.datetime.now(BRT).date().isoformat()
    feitos = []
    for n, d in enumerate(dias_ib):
        if d >= hoje or dt.date.fromisoformat(d).weekday() > 4:
            continue
        pi = [p for p in ib[d] if '10:00' <= p[0] <= '17:00']
        pd = [p for p in dl.get(d, []) if '09:00' <= p[0] <= '18:25']
        if len(pi) < 60 or len(pd) < 60 or n == 0:
            continue
        ant_i = ib[dias_ib[n - 1]][-1][1]
        dl_ant = [x for x in sorted(dl) if x < d]
        ant_d = dl[dl_ant[-1]][-1][1] if dl_ant else pd[0][1]
        feitos.append(d)
        if d in com_manchetes:
            continue
        json.dump({'data': d, 'historico': True, 'ibov': {'anterior': ant_i, 'pontos': pi}, 'dolar': {'anterior': ant_d, 'pontos': pd}, 'marcadores': []},
                  open(os.path.join(pasta, f'{d}.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    existentes = sorted(f[:-5] for f in os.listdir(pasta) if f[:4].isdigit() and f.endswith('.json'))
    json.dump({'dias': existentes}, open(os.path.join(pasta, 'indice.json'), 'w', encoding='utf-8'))
    print(f'::notice::Simulador: {len(existentes)} pregões extras em data/sim (de {len(feitos)} completos nos últimos 60 dias).')


if __name__ == '__main__':
    main()
