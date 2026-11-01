"""Curva de juros pública (Tesouro Direto) → data/curva.json.

Fonte 1 (tentativa): taxas do momento no site do Tesouro Direto (o endpoint antigo pode estar desativado).
Fonte 2 (reserva e histórico): arquivo oficial PrecoTaxaTesouroDireto.csv do Tesouro Transparente (fechamento diário).
Guarda até 30 fotos diárias para comparar "hoje × pregão anterior". Não usa dados licenciados da B3.
"""
import csv, datetime as dt, io, json, os, sys, urllib.request

BRT = dt.timezone(dt.timedelta(hours=-3))
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36', 'Accept': '*/*'}
TD_URL = 'https://www.tesourodireto.com.br/json/br/com/b3/tesourodireto/service/api/treasurybondsinfo.json'
CSV_URL = ('https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/'
           '796d2059-14e9-44e3-80c9-2d9e30b405c1/download/PrecoTaxaTesouroDireto.csv')
SAIDA = 'data/curva.json'


def note(k, m):
    print(f'::{k}::{m}')


def get(url, timeout=60):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read()


def tipo(nome):
    n = nome.lower()
    if 'renda+' in n or 'educa+' in n or 'semestrais' in n:
        return None
    if 'prefixado' in n:
        return 'pre'
    if 'ipca' in n:
        return 'ipca'
    return None


def ponto(nome, venc, taxa, base):
    anos = (venc - base).days / 365.25
    if anos <= 0.05 or taxa is None:
        return None
    return {'titulo': nome, 'venc': venc.isoformat(), 'anos': round(anos, 2), 'taxa': round(float(taxa), 2)}


def de_td():
    j = json.loads(get(TD_URL, 30))
    lst = j['response']['TrsrBdTradgList']
    base = dt.datetime.now(BRT).date()
    foto = {'pre': [], 'ipca': []}
    for it in lst:
        b = it['TrsrBd']; t = tipo(b['nm'])
        if not t:
            continue
        taxa = b.get('anulInvstmtRate') or b.get('anulRedRate')
        p = ponto(b['nm'], dt.date.fromisoformat(b['mtrtyDt'][:10]), taxa, base)
        if p:
            foto[t].append(p)
    if not foto['pre']:
        raise ValueError('sem títulos prefixados')
    return base.isoformat(), foto


def de_csv():
    texto = get(CSV_URL, 120).decode('latin-1')
    linhas = list(csv.DictReader(io.StringIO(texto), delimiter=';'))
    datas = {}
    for l in linhas:
        try:
            base = dt.datetime.strptime(l['Data Base'], '%d/%m/%Y').date()
        except (KeyError, ValueError):
            continue
        if base < dt.date.today() - dt.timedelta(days=45):
            continue
        t = tipo(l.get('Tipo Titulo', ''))
        if not t:
            continue
        venc = dt.datetime.strptime(l['Data Vencimento'], '%d/%m/%Y').date()
        try:
            taxa = float(l['Taxa Compra Manha'].replace(',', '.'))
        except (KeyError, ValueError):
            continue
        p = ponto(f"{l['Tipo Titulo']} {venc.year}", venc, taxa, base)
        if p:
            datas.setdefault(base.isoformat(), {'pre': [], 'ipca': []})[t].append(p)
    return datas


def main():
    try:
        atual = json.load(open(SAIDA, encoding='utf-8'))
    except Exception:
        atual = {'historico': {}}
    hist = atual.get('historico', {})
    fontes = []
    try:  # histórico oficial (fechamentos)
        for d, foto in de_csv().items():
            if d not in hist or hist[d].get('fonte') == 'csv':
                hist[d] = {**foto, 'fonte': 'csv'}
        fontes.append('Tesouro Transparente')
    except Exception as e:
        note('warning', f'CSV do Tesouro Transparente indisponível: {type(e).__name__}: {str(e)[:120]}')
    try:  # taxa do momento
        d, foto = de_td()
        hist[d] = {**foto, 'fonte': 'td', 'hora': dt.datetime.now(BRT).strftime('%H:%M')}
        fontes.append('Tesouro Direto')
    except Exception as e:
        note('warning', f'Tesouro Direto indisponível: {type(e).__name__}: {str(e)[:120]}')
    if not hist:
        note('warning', 'Nenhuma fonte respondeu; curva não atualizada.')
        return
    for foto in hist.values():
        for k in ('pre', 'ipca'):
            foto[k] = sorted(foto.get(k, []), key=lambda p: p['anos'])
    hist = dict(sorted(hist.items())[-30:])
    json.dump({'atualizado_em': dt.datetime.now(BRT).isoformat(timespec='seconds'), 'fontes': fontes, 'historico': hist},
              open(SAIDA, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    ult = list(hist)[-2:]
    note('notice', f'Curva: {len(hist)} dias · últimos {ult} · fontes {fontes} · {len(hist[ult[-1]]["pre"])} prefixados')


if __name__ == '__main__':
    main()
