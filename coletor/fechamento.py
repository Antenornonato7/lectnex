"""Fechamento do pregão no Telegram (dias úteis, ~19h de Brasília).

Usa dados que o site já tem: data/cotacoes.json (Ibovespa e ações, brapi), dólar à vista (AwesomeAPI),
data/leitura.json (termômetro da manhã) e data/calendario.json (agenda do próximo pregão).
Também registra o acerto do termômetro em data/placar-termometro.json.

Critério do placar (aproximação educacional): WIN medido pelo Ibovespa à vista e WDO pelo dólar à vista.
alta → acerta se subiu; baixa → acerta se caiu; neutro → acerta se a variação ficou entre −0,5% e +0,5%.
"""
import datetime as dt, json, os, sys, urllib.request

sys.path.insert(0, os.path.dirname(__file__))
import telegram as tg  # reaproveita token, canal, envio e escape

BRT = dt.timezone(dt.timedelta(hours=-3))
hoje = dt.datetime.now(BRT).date()
FORCAR = bool(os.environ.get('FORCAR'))
SETA = {'bullish': '▲ alta', 'bearish': '▼ baixa', 'neutro': '● neutro'}


def ler(p):
    try:
        return json.load(open(p, encoding='utf-8'))
    except Exception:
        return None


def pct(v):
    return ('+' if v > 0 else '−' if v < 0 else '') + f'{abs(v):.2f}%'.replace('.', ',')


def acertou(leitura, var):
    if var is None or leitura not in SETA:
        return None
    return var > 0 if leitura == 'bullish' else var < 0 if leitura == 'bearish' else abs(var) <= 0.5


def dolar():
    erros = []
    try:
        with urllib.request.urlopen(urllib.request.Request('https://economia.awesomeapi.com.br/json/last/USD-BRL', headers={'User-Agent': 'lectnex-bot'}), timeout=15) as r:
            d = json.load(r)['USDBRL']
        return float(d['bid']), float(d['pctChange'])
    except Exception as e:
        erros.append(f'AwesomeAPI: {e}')
    try:  # reserva: brapi (mesmo token público usado no site)
        with urllib.request.urlopen('https://brapi.dev/api/v2/currency?currency=USD-BRL&token=uRJnTfjL6jypdHfJ8b5LJd', timeout=15) as r:
            d = json.load(r)['currency'][0]
        return float(d['bidPrice']), float(d['percentageChange'])
    except Exception as e:
        erros.append(f'brapi: {e}')
    tg.note('warning', 'Dólar indisponível: ' + ' | '.join(erros))
    return None, None


def main():
    cot = ler('data/cotacoes.json') or {}
    ibov = next((x for x in cot.get('itens', []) if x.get('ticker') == 'IBOV'), None)
    dia_ibov = None
    if ibov and ibov.get('hora'):
        dia_ibov = dt.datetime.fromisoformat(ibov['hora'].replace('Z', '+00:00')).astimezone(BRT).date()
    cal0 = ler('data/calendario.json') or {}
    feriado = any(e.get('data') == hoje.isoformat() and 'B3 fechada' in (e.get('evento') or '') for e in cal0.get('eventos', []))
    if (hoje.weekday() >= 5 or feriado) and not FORCAR:
        tg.note('notice', 'Hoje não tem pregão na B3; fechamento não enviado.')
        return
    if dia_ibov != hoje and not FORCAR:
        tg.note('notice', f'Sem pregão hoje ou cotação não atualizada (Ibovespa de {dia_ibov}); fechamento não enviado.')
        return
    iv = ibov.get('var_pct') if ibov else None
    usd, uv = dolar()

    linhas = [f'🔔 <b>Fechamento · {hoje:%d/%m}</b>']
    linhas.append(' · '.join(filter(None, [
        'IBOV <b>' + f'{ibov["preco"]:,.0f}'.replace(',', '.') + f'</b> ({pct(iv)})' if ibov and iv is not None else '',
        'Dólar <b>R$ ' + f'{usd:.3f}'.replace('.', ',') + f'</b> ({pct(uv)})' if usd else ''])))
    m = sorted([x for x in cot.get('mapa', []) if isinstance(x.get('var_pct'), (int, float))], key=lambda x: x['var_pct'])
    if len(m) >= 6:
        linhas += ['', '📈 ' + ' · '.join(f'{tg.e(x["ticker"])} {pct(x["var_pct"])}' for x in m[::-1][:3]),
                   '📉 ' + ' · '.join(f'{tg.e(x["ticker"])} {pct(x["var_pct"])}' for x in m[:3])]

    # termômetro da manhã × fechamento
    lt = ler('data/leitura.json') or {}
    term = lt.get('termometro') if lt.get('data') == hoje.isoformat() else None
    placar = ler('data/placar-termometro.json') or {'criterio': 'WIN pelo Ibovespa à vista, WDO pelo dólar à vista; neutro = variação entre −0,5% e +0,5%', 'dias': []}
    if term:
        reg = {'data': hoje.isoformat()}
        partes = []
        for k, var in (('win', iv), ('wdo', uv)):
            t = (term.get(k) or {}).get('leitura')
            a = acertou(t, var)
            if a is None:
                continue
            reg[k] = {'leitura': t, 'var_pct': round(var, 2), 'acerto': a}
            partes.append(f'{k.upper()} {SETA[t]} → {"✅ acertou" if a else "❌ errou"} ({"IBOV" if k == "win" else "dólar"} {pct(var)})')
        if partes:
            placar['dias'] = [d for d in placar['dias'] if d['data'] != reg['data']] + [reg]
            placar['dias'] = sorted(placar['dias'], key=lambda d: d['data'])[-250:]
            ult = placar['dias'][-20:]
            tot = sum(1 for d in ult for k in ('win', 'wdo') if k in d)
            ok = sum(1 for d in ult for k in ('win', 'wdo') if d.get(k, {}).get('acerto'))
            placar['atualizado_em'] = dt.datetime.now(BRT).isoformat(timespec='seconds')
            json.dump(placar, open('data/placar-termometro.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            linhas += ['', '🎯 <b>Termômetro da manhã</b>'] + partes + [(f'Placar dos últimos {len(ult)} pregões:' if len(ult) > 1 else 'Placar (1º pregão):') + f' <b>{ok}/{tot}</b> ({ok / tot * 100:.0f}%)' if tot else '']

    # agenda do próximo dia com eventos
    cal = ler('data/calendario.json') or {}
    futuros = sorted({e['data'] for e in cal.get('eventos', []) if e.get('data', '') > hoje.isoformat()})
    if futuros:
        prox = futuros[0]
        evs = [e for e in cal['eventos'] if e['data'] == prox and (e.get('importancia') or 1) >= 2]
        evs.sort(key=lambda e: e.get('hora') or '')
        if evs:
            d = dt.date.fromisoformat(prox)
            nome = 'Amanhã' if d == hoje + dt.timedelta(days=1) else ['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom'][d.weekday()] + f' {d:%d/%m}'
            linhas += ['', f'📅 <b>{nome}</b>'] + [f'{e.get("hora") or "dia"} {tg.FLAG.get(e.get("pais"), "")} {tg.e(e["evento"])}{" ⚠️" if (e.get("importancia") or 1) >= 3 else ""}' for e in evs[:5]]

    linhas += ['', f'<a href="{tg.SITE}">Mercado Hoje →</a>', '<i>Educacional. Não é recomendação. Cotações com atraso de ~30 min.</i>']
    texto = '\n'.join(l for l in linhas if l is not None)
    if not tg.TOKEN:
        print(texto)
        tg.note('notice', 'Telegram não configurado; fechamento só impresso.')
        return
    ok = tg.enviar(texto)
    tg.note('notice' if ok else 'warning', 'Fechamento enviado ao Telegram' if ok else 'Fechamento não enviado')


if __name__ == '__main__':
    main()
