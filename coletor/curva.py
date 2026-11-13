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


def valida(d, foto):
    """Descarta só dado quebrado (taxa impossível, vencimento repetido, curva incompleta).
    Movimento forte de mercado NÃO é descartado: em 05/10 e 26/10/2026 (1º e 2º turno) a curva andou mais de 1 p.p. num dia, de verdade."""
    limpa = {}
    for k in ('pre', 'ipca'):
        por_venc = {}
        for p in foto.get(k, []):
            if isinstance(p.get('taxa'), (int, float)) and 0 < p['taxa'] < 40 and p.get('anos', 0) > 0:
                por_venc[p['venc']] = p
            else:
                note('warning', f'Curva {d}: ponto descartado {k} {p.get("venc")} taxa={p.get("taxa")}')
        limpa[k] = list(por_venc.values())
    if len(limpa['pre']) < 3:
        note('warning', f'Curva {d}: só {len(limpa["pre"])} prefixados; dia ignorado.')
        return None
    return limpa


# Palavras que ligam uma manchete aos juros (peso) e o rótulo curto que vai no gráfico
CHAVES = [(r'elei|turno|urna|apura', 4, 'Eleição'), (r'copom|selic|banco central|galípolo', 4, 'Copom'),
          (r'\bipca|inflaç', 3, 'IPCA'), (r'fiscal|arcabouço|gastos|dívida|orçament|tesouro', 3, 'Fiscal'),
          (r'juros|\bdi\b|taxas futuras|curva|treasur', 2, None), (r'payroll|fed\b|fomc|powell', 2, 'Exterior'),
          (r'dólar|câmbio', 1, None)]


def explicar_saltos(hist, minimo=0.75):
    """Para cada dia em que a curva prefixada andou >= 0,75 p.p. em média, procura nas manchetes guardadas daquele dia
    (data/dias/AAAA-MM-DD.json, as mesmas do "O que mexeu hoje") a que melhor explica o salto. Sem IA paga: pontua
    palavras ligadas a juros, impacto da manchete e horário (a taxa do Tesouro é a da manhã)."""
    import re
    eventos, ds = [], list(hist)
    for a, b in zip(ds, ds[1:]):
        ant = {p['venc']: p['taxa'] for p in hist[a].get('pre', [])}
        difs = [p['taxa'] - ant[p['venc']] for p in hist[b].get('pre', []) if p['venc'] in ant]
        if not difs or abs(sum(difs) / len(difs)) < minimo:
            continue
        media = sum(difs) / len(difs)
        melhor, nota_melhor = None, 0
        try:
            dia = json.load(open(f'data/dias/{b}.json', encoding='utf-8'))
        except Exception:
            dia = {}
        for m in dia.get('marcadores', []) or []:
            t = (m.get('titulo') or '').lower()
            nota, rot = 0, None
            for rx, peso, r in CHAVES:
                if re.search(rx, t):
                    nota += peso
                    rot = rot or r
            if not nota:
                continue
            nota += {'alto': 3, 'medio': 1}.get(m.get('impacto'), 0) + (2 if 'DI' in (m.get('ativos') or []) else 0)
            nota += 1 if (m.get('hora') or '99') <= '10:30' else 0
            if nota > nota_melhor:
                melhor, nota_melhor = {**m, 'rotulo': rot}, nota
        ev = {'data': b, 'media_pp': round(media, 2), 'tipo': 'auto'}
        if melhor and nota_melhor >= 4:
            ev.update(rotulo=melhor['rotulo'] or 'Juros', motivo=melhor['titulo'], fonte=melhor.get('fonte'), url=melhor.get('url'), hora=melhor.get('hora'))
        else:
            ev.update(rotulo='Salto', motivo=None)
        eventos.append(ev)
        note('notice', f'Curva: salto em {b} ({media:+.2f} p.p.) · motivo: {ev.get("motivo") or "sem manchete forte guardada"}')
    return eventos


def main():
    try:
        atual = json.load(open(SAIDA, encoding='utf-8'))
    except Exception:
        atual = {'historico': {}}
    hist = atual.get('historico', {})
    fontes = []
    try:  # histórico oficial (fechamentos)
        for d, foto in de_csv().items():
            foto = valida(d, foto)
            if foto and (d not in hist or hist[d].get('fonte') == 'csv'):
                hist[d] = {**foto, 'fonte': 'csv'}
        fontes.append('Tesouro Transparente')
    except Exception as e:
        note('warning', f'CSV do Tesouro Transparente indisponível: {type(e).__name__}: {str(e)[:120]}')
    try:  # taxa do momento
        d, foto = de_td()
        foto = valida(d, foto)
        if not foto:
            raise ValueError('curva do momento incompleta')
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
    # movimento forte é mantido; o motivo provável sai das manchetes guardadas do dia
    eventos = explicar_saltos(hist)
    json.dump({'atualizado_em': dt.datetime.now(BRT).isoformat(timespec='seconds'), 'fontes': fontes, 'historico': hist, 'eventos': eventos},
              open(SAIDA, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    ult = list(hist)[-2:]
    note('notice', f'Curva: {len(hist)} dias · últimos {ult} · fontes {fontes} · {len(hist[ult[-1]]["pre"])} prefixados')


if __name__ == '__main__':
    main()
