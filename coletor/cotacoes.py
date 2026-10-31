"""Coleta cotações (atraso ~30 min, plano gratuito da brapi) do Ibovespa e das ações de maior peso.

Grava data/cotacoes.json, lido pela faixa "B3" e pelo mapa de calor do Mercado Hoje.
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
# Mapa de calor: ações líquidas do Ibovespa agrupadas por setor (o tamanho vem do valor de mercado informado pela brapi).
# Coletado de hora em hora (rodadas com minuto < 30); as 10 da faixa acima são reaproveitadas.
SETORES = {
    'Petróleo e gás': ['PETR4', 'PRIO3', 'VBBR3', 'UGPA3', 'CSAN3'],
    'Mineração e siderurgia': ['VALE3', 'GGBR4', 'CMIN3'],
    'Bancos e financeiro': ['ITUB4', 'BBDC4', 'BBAS3', 'ITSA4', 'BPAC11', 'B3SA3', 'BBSE3', 'CXSE3'],
    'Energia e saneamento': ['ELET3', 'SBSP3', 'EQTL3', 'CMIG4', 'ENEV3'],
    'Consumo e varejo': ['ABEV3', 'LREN3', 'MGLU3', 'ASAI3', 'RADL3'],
    'Indústria e serviços': ['WEGE3', 'RENT3', 'TOTS3'],
    'Saúde': ['RDOR3', 'HAPV3'],
    'Papel e celulose': ['SUZB3', 'KLBN11'],
    'Telecom': ['VIVT3', 'TIMS3'],
}
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
    mc = x.get('marketCap')
    return {'preco': round(float(preco), 2), 'var_pct': None if pct is None else round(float(pct), 2), 'hora': t,
            'mcap': None if mc in (None, 0) else float(mc), 'nome_longo': x.get('shortName') or x.get('longName')}


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
    # Mapa de calor (de hora em hora, ou se ainda não existe / for disparo manual)
    antigo_full = {}
    try:
        antigo_full = json.load(open(SAIDA, encoding='utf-8'))
    except Exception:
        pass
    mapa = antigo_full.get('mapa') or []
    mapa_em = antigo_full.get('mapa_em')
    if datetime.now(timezone.utc).minute < 30 or not mapa or os.environ.get('FORCAR_MAPA'):
        ja = {i['ticker']: i for i in itens}
        velho = {m['ticker']: m for m in mapa}
        novo = []
        for setor, tks in SETORES.items():
            for tk in tks:
                try:
                    d = ja.get(tk) if ja.get(tk, {}).get('mcap') else None
                    d = d or cotar(tk)
                    if tk not in ja:
                        time.sleep(0.4)
                    novo.append({'ticker': tk, 'setor': setor, 'preco': d['preco'], 'var_pct': d['var_pct'], 'mcap': d.get('mcap')})
                except Exception as e:
                    print(f'::warning title=Mapa: cotação falhou::{tk}: {e}')
                    if tk in velho:
                        novo.append(velho[tk])
        if novo:
            mapa, mapa_em = novo, datetime.now(BRT).isoformat(timespec='minutes')
    out = {'atualizado_em': datetime.now(BRT).isoformat(timespec='minutes'), 'fonte': 'brapi.dev (atraso de ~30 min)', 'itens': [{k: v for k, v in i.items() if k not in ('nome_longo',)} for i in itens],
           'mapa_em': mapa_em, 'mapa': mapa}
    json.dump(out, open(SAIDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(itens)} cotações gravadas, {len(falhas)} falhas')


if __name__ == '__main__':
    main()
