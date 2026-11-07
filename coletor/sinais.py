"""Sinais da manhã (7h25 de Brasília, dias úteis): o que o mundo fez antes da abertura, medido, para apoiar o termômetro.

Mede contra o fechamento anterior: S&P 500 futuro (ES=F), Nasdaq futuro (NQ=F), EWZ (ETF do Brasil em Nova York, com o
pré-mercado quando houver), DXY (DX-Y.NYB), petróleo Brent (BZ=F), VIX e o dólar no exterior (BRL=X). Fonte: Yahoo Finance.

Regra do sinal quantitativo (experimental, transparente, sem ajuste fino):
  WIN  = 0,5·S&P fut + 0,3·EWZ − 0,4·DXY + 0,1·Brent        → alta se ≥ +0,15; baixa se ≤ −0,15; senão neutro
  WDO  = 0,6·DXY − 0,3·S&P fut − 0,3·EWZ + 0,2·VIX/10      → alta se ≥ +0,12; baixa se ≤ −0,12; senão neutro
Os pesos refletem a relação usual (bolsa brasileira acompanha o apetite global por risco; dólar forte lá fora pesa no real).
O fechamento confere este sinal à parte do termômetro, para mostrar com o tempo se ele ajuda.
Grava data/sinais.json. Sem dados suficientes, grava o que tiver e o sinal fica 'sem dados'.
"""
import datetime as dt
import json
import urllib.request
from zoneinfo import ZoneInfo

BRT = dt.timezone(dt.timedelta(hours=-3))
NY = ZoneInfo('America/New_York')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36'}
ATIVOS = [('sp', 'S&P 500 fut.', 'ES%3DF'), ('nq', 'Nasdaq fut.', 'NQ%3DF'), ('ewz', 'EWZ (Brasil em NY)', 'EWZ'),
          ('dxy', 'DXY', 'DX-Y.NYB'), ('brent', 'Brent', 'BZ%3DF'), ('vix', 'VIX', '%5EVIX'), ('brl', 'Dólar no exterior', 'BRL%3DX')]


def _chart(sym, intervalo, periodo, pre=False):
    for host in ('query2', 'query1'):
        try:
            url = f'https://{host}.finance.yahoo.com/v8/finance/chart/{sym}?interval={intervalo}&range={periodo}' + ('&includePrePost=true' if pre else '')
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
                return json.load(r)['chart']['result'][0]
        except Exception:
            continue
    return None


def variacao(sym):
    """Último preço (inclui pré-mercado) contra o fechamento do último pregão anterior a hoje (data de Nova York)."""
    dia, intra = _chart(sym, '1d', '10d'), _chart(sym, '5m', '1d', pre=True)
    if not dia or not intra:
        return None
    hoje = dt.datetime.now(NY).date()
    fech = [(dt.datetime.fromtimestamp(t, NY).date(), c) for t, c in zip(dia['timestamp'], dia['indicators']['quote'][0]['close']) if c is not None]
    ant = [c for d, c in fech if d < hoje]
    ult = [c for c in intra['indicators']['quote'][0]['close'] if c is not None]
    if not ant or not ult:
        return None
    return round((ult[-1] / ant[-1] - 1) * 100, 2)


def sinal(score, lim):
    if score is None:
        return 'sem dados'
    return 'bullish' if score >= lim else 'bearish' if score <= -lim else 'neutro'


def pct(v):
    return ('+' if v > 0 else '−' if v < 0 else '') + f'{abs(v):.2f}%'.replace('.', ',')


def main():
    agora = dt.datetime.now(BRT)
    v = {k: variacao(sym) for k, _, sym in ATIVOS}
    g = lambda k: v.get(k) or 0.0
    tem_win = v.get('sp') is not None and v.get('dxy') is not None
    tem_wdo = v.get('dxy') is not None and (v.get('sp') is not None or v.get('ewz') is not None)
    s_win = round(0.5 * g('sp') + 0.3 * g('ewz') - 0.4 * g('dxy') + 0.1 * g('brent'), 3) if tem_win else None
    s_wdo = round(0.6 * g('dxy') - 0.3 * g('sp') - 0.3 * g('ewz') + 0.2 * g('vix') / 10, 3) if tem_wdo else None
    nome = {k: n for k, n, _ in ATIVOS}

    def motivos(pesos):
        cont = sorted(((k, w * g(k)) for k, w in pesos if v.get(k) is not None), key=lambda x: -abs(x[1]))
        return [f'{nome[k]} {pct(v[k])}' for k, c in cont[:3] if abs(c) >= 0.02]
    out = {'data': agora.date().isoformat(), 'hora': agora.strftime('%H:%M'),
           'ativos': [{'id': k, 'nome': n, 'var': v[k]} for k, n, _ in ATIVOS if v[k] is not None],
           'win': {'leitura': sinal(s_win, 0.15), 'score': s_win, 'motivos': motivos([('sp', 0.5), ('ewz', 0.3), ('dxy', -0.4), ('brent', 0.1)])},
           'wdo': {'leitura': sinal(s_wdo, 0.12), 'score': s_wdo, 'motivos': motivos([('dxy', 0.6), ('sp', -0.3), ('ewz', -0.3), ('vix', 0.02)])},
           'regra': 'WIN = 0,5·S&P fut + 0,3·EWZ − 0,4·DXY + 0,1·Brent (alta ≥ +0,15; baixa ≤ −0,15). '
                    'WDO = 0,6·DXY − 0,3·S&P fut − 0,3·EWZ + 0,02·VIX (alta ≥ +0,12; baixa ≤ −0,12). Variações contra o fechamento anterior, Yahoo Finance.',
           'experimental': True}
    json.dump(out, open('data/sinais.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'::notice::Sinais {out["hora"]}: WIN {out["win"]["leitura"]} ({s_win}) · WDO {out["wdo"]["leitura"]} ({s_wdo}) · '
          + ', '.join(f'{a["nome"]} {pct(a["var"])}' for a in out['ativos']))


if __name__ == '__main__':
    main()
