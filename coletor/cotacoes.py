"""Coleta cotações (atraso ~30 min, plano gratuito da brapi) do Ibovespa e das ações de maior peso.

Grava data/cotacoes.json, lido pela faixa "B3" no topo do Mercado Hoje.
Roda no GitHub Actions a cada 30 minutos durante o pregão (workflow "Cotações B3").
Uso local: BRAPI_TOKEN=... python3 coletor/cotacoes.py
Só biblioteca padrão do Python.
"""
import json, os, sys, time, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

TOKEN = os.environ.get('BRAPI_TOKEN', '')
# Ibovespa + 10 ações de maior peso no índice (ordem de exibição)
ATIVOS = [('^BVSP', 'Ibovespa'), ('PETR4', 'Petrobras'), ('VALE3', 'Vale'), ('ITUB4', 'Itaú'), ('BBDC4', 'Bradesco'),
          ('BBAS3', 'Banco do Brasil'), ('B3SA3', 'B3'), ('ELET3', 'Eletrobras'), ('WEGE3', 'WEG'), ('ABEV3', 'Ambev'), ('PRIO3', 'PRIO')]
BRT = timezone(timedelta(hours=-3))
SAIDA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'cotacoes.json')


def cotar(ticker):
    q = f'?token={urllib.parse.quote(TOKEN)}' if TOKEN else ''
    url = f'https://brapi.dev/api/quote/{urllib.parse.quote(ticker)}{q}'
    req = urllib.request.Request(url, headers={'User-Agent': 'lectnex-coletor/1.0'})
    with urllib.request.urlopen(req, timeout=20) as r:
        j = json.load(r)
    x = (j.get('results') or [{}])[0]
    preco, pct = x.get('regularMarketPrice'), x.get('regularMarketChangePercent')
    if preco is None:
        raise ValueError('sem preço')
    t = x.get('regularMarketTime')
    return {'preco': round(float(preco), 2), 'var_pct': None if pct is None else round(float(pct), 2), 'hora': t}


def main():
    antigo = {}
    try:
        antigo = {i['ticker']: i for i in json.load(open(SAIDA, encoding='utf-8')).get('itens', [])}
    except Exception:
        pass
    itens, falhas = [], []
    for tk, nome in ATIVOS:
        try:
            d = cotar(tk)
            itens.append({'ticker': 'IBOV' if tk == '^BVSP' else tk, 'nome': nome, **d})
        except Exception as e:
            falhas.append(f'{tk}: {e}')
            if ('IBOV' if tk == '^BVSP' else tk) in antigo:  # mantém o último valor bom
                itens.append(antigo['IBOV' if tk == '^BVSP' else tk])
        time.sleep(0.4)
    for f in falhas:
        print(f'::warning title=Cotação falhou::{f}')
    if not itens:
        print('::error::nenhuma cotação obtida'); sys.exit(1)
    out = {'atualizado_em': datetime.now(BRT).isoformat(timespec='minutes'), 'fonte': 'brapi.dev (atraso de ~30 min)', 'itens': itens}
    json.dump(out, open(SAIDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(itens)} cotações gravadas, {len(falhas)} falhas')


if __name__ == '__main__':
    main()
