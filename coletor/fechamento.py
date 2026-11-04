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
SO_STORY = bool(os.environ.get('SO_STORY'))  # prévia: só monta o resumo do story; não posta no canal nem grava placar
FORCAR = bool(os.environ.get('FORCAR')) or SO_STORY
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
    ua = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36', 'Accept': 'application/json,*/*'}
    for host in ('query2', 'query1'):  # reserva 2: Yahoo Finance (BRL=X), a mesma fonte da "reação aos dados"
        try:
            req = urllib.request.Request(f'https://{host}.finance.yahoo.com/v8/finance/chart/BRL=X?interval=5m&range=1d', headers=ua)
            with urllib.request.urlopen(req, timeout=15) as r:
                meta = json.load(r)['chart']['result'][0]['meta']
            preco, ant = float(meta['regularMarketPrice']), float(meta.get('chartPreviousClose') or meta.get('previousClose'))
            tg.note('notice', f'Dólar pela reserva Yahoo ({host}) após falha de: ' + ' | '.join(erros))
            return preco, (preco / ant - 1) * 100
        except Exception as e:
            erros.append(f'Yahoo {host}: {e}')
    tg.note('warning', 'Dólar indisponível: ' + ' | '.join(erros))
    return None, None


def arquivar_dia(m):
    """Guarda o gráfico do dia com as manchetes em data/dias/AAAA-MM-DD.json (página "O que mexeu hoje")."""
    if SO_STORY or m.get('data') != hoje.isoformat() or not (m.get('ibov') or m.get('dolar')):
        return
    os.makedirs('data/dias', exist_ok=True)
    json.dump(m, open(f'data/dias/{hoje.isoformat()}.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    try:
        ind = json.load(open('data/dias/indice.json', encoding='utf-8'))
    except Exception:
        ind = {'dias': []}
    ind['dias'] = sorted(set(ind['dias']) | {hoje.isoformat()})[-120:]
    json.dump(ind, open('data/dias/indice.json', 'w', encoding='utf-8'), ensure_ascii=False)


def manchetes_que_mexeram():
    """As 3 manchetes do dia seguidas dos maiores movimentos em 30 min (Ibovespa para WIN, dólar para WDO).
    Manchetes: branch ao-vivo (noticias-agora.json → 'hoje'). Preços: Yahoo Finance, barras de 5 min."""
    tok, repo = os.environ.get('GITHUB_TOKEN'), os.environ.get('GITHUB_REPOSITORY')
    if not tok or not repo:
        return []
    try:
        req = urllib.request.Request(f'https://api.github.com/repos/{repo}/contents/noticias-agora.json?ref=ao-vivo',
                                     headers={'Authorization': f'Bearer {tok}', 'Accept': 'application/vnd.github.raw', 'User-Agent': 'lectnex-bot'})
        with urllib.request.urlopen(req, timeout=20) as r:
            aovivo = json.loads(r.read())
        hoje_n = aovivo.get('hoje', [])
        arquivar_dia(aovivo.get('mercado') or {})
        if os.environ.get('MERCADO_JSON') and (aovivo.get('mercado') or {}).get('data') == hoje.isoformat():  # para o post do gráfico do dia
            json.dump(aovivo['mercado'], open(os.environ['MERCADO_JSON'], 'w', encoding='utf-8'), ensure_ascii=False)
    except Exception as e:
        tg.note('warning', f'Manchetes do dia indisponíveis: {e.__class__.__name__}')
        return []
    ua = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36'}
    series = {}
    for nome, sym in (('WIN', '%5EBVSP'), ('WDO', 'BRL%3DX')):
        try:
            with urllib.request.urlopen(urllib.request.Request(f'https://query2.finance.yahoo.com/v8/finance/chart/{sym}?interval=5m&range=1d', headers=ua), timeout=20) as r:
                res = json.load(r)['chart']['result'][0]
            series[nome] = [(dt.datetime.fromtimestamp(t, BRT), c) for t, c in zip(res['timestamp'], res['indicators']['quote'][0]['close']) if c]
        except Exception as e:
            tg.note('warning', f'Série de 5 min ({nome}) indisponível: {e.__class__.__name__}')

    def reacao(serie, t0):
        antes = [c for t, c in serie if t <= t0]
        depois = [c for t, c in serie if t0 + dt.timedelta(minutes=25) <= t <= t0 + dt.timedelta(minutes=35)]
        if not antes or not depois:
            return None
        return (depois[0] / antes[-1] - 1) * 100

    cands = []
    for h in hoje_n:
        t0 = dt.datetime.fromisoformat(h['publicado'])
        if t0.date() != hoje or not (10 <= t0.hour < 17 or (t0.hour == 17 and t0.minute <= 20)):
            continue
        for ativo in [a for a in ('WIN', 'WDO') if a in h.get('ativos', [])] or ['WIN']:
            v = reacao(series.get(ativo, []), t0)
            if v is not None:
                cands.append((abs(v) + (0.05 if h.get('impacto') == 'alto' else 0), v, ativo, h, t0))
    cands.sort(key=lambda c: -c[0])
    linhas, usados = [], set()
    for _, v, ativo, h, t0 in cands:
        if h['url'] in usados:
            continue
        usados.add(h['url'])
        nome = 'Ibovespa' if ativo == 'WIN' else 'dólar'
        linhas.append(f'{t0:%Hh%M} · {tg.e(h["titulo"][:110])} ({tg.e(h["fonte"])})\n   → {nome} {pct(v)} em 30 min')
        if len(linhas) == 3:
            break
    return linhas


def antes_depois():
    """No dia de evento forte: o que o histórico da manhã (data/antes.json) indicava × o que aconteceu hoje."""
    a = ler('data/antes.json') or {}
    if a.get('data') != hoje.isoformat() or a.get('vazio'):
        return None
    ev = next((e for e in (ler('data/calendario.json') or {}).get('eventos', []) if e.get('data') == hoje.isoformat() and e.get('tipo') == a.get('tipo')), {})
    sp = (ev.get('surpresa') or {}).get('direcao') if isinstance(ev.get('surpresa'), dict) else None
    if not sp and ev.get('resultado') not in (None, '') and ev.get('consenso') and str(ev['resultado']) == str(ev['consenso']):
        sp = 'em linha'
    hist = (a.get('por_surpresa') or {}).get(sp) if sp in ('acima', 'abaixo') else None
    base = 'surpresa' if hist else 'geral'
    hist = hist or a.get('divulgacoes') or {}
    out = {'tipo': a.get('tipo'), 'evento': a.get('curto') or a.get('evento'), 'hora': a.get('hora'), 'resultado': ev.get('resultado'), 'consenso': ev.get('consenso'),
           'surpresa': sp, 'base': base, 'hist': {k: hist.get(k) for k in ('win', 'wdo')}, 'hoje': None}
    try:
        import reacao  # mesma medida do histórico: último preço antes até 30 min depois (barras de 5 min)
        t0 = reacao.hora_ev({'data': hoje.isoformat(), 'hora': a.get('hora')})
        if t0:
            bs = {k: reacao.barras(sym) for k, sym in reacao.ATIVOS.items()}
            v = {k: reacao.var(bs[k], t0)[0] for k in bs}
            if v['win'] is not None or v['wdo'] is not None:
                abertura = reacao.var(bs['win'], t0)[1]
                out['hoje'] = {'win': None if abertura else v['win'], 'wdo': v['wdo']}
    except Exception as e:
        tg.note('warning', f'Antes × depois: reação de hoje indisponível ({e.__class__.__name__})')
    return out


PLACAR_HIST = 'data/placar-historico.json'


def acerto(sobe, v):
    """O histórico 'indica' uma direção quando subiu em ≥60% ou ≤40% das vezes; senão está dividido (não conta)."""
    if sobe is None or v is None or 40 < sobe < 60:
        return None
    return (v > 0) == (sobe >= 60) if v != 0 else False


def registrar_placar_historico(ad):
    """Guarda o Antes × Depois do dia e completa reações pendentes (ex.: WIN do Copom, medido na abertura seguinte)."""
    pl = ler(PLACAR_HIST) or {'criterio': 'O histórico indica uma direção quando o ativo subiu em 60% ou mais (alta) ou em 40% ou menos (queda) '
                                          'das divulgações anteriores com a mesma surpresa (ou de todas, sem surpresa definida). Acerta quando a reação '
                                          'de 30 min (ou da abertura seguinte) vai para esse lado. Entre 40% e 60%: dividido, não conta.', 'eventos': []}
    evs = {e['data'] + '|' + e['tipo']: e for e in pl['eventos']}
    if ad:
        k = hoje.isoformat() + '|' + ad['tipo']
        velho = evs.get(k, {})
        evs[k] = {'data': hoje.isoformat(), 'tipo': ad['tipo'], 'evento': ad['evento'], 'hora': ad.get('hora'), 'surpresa': ad.get('surpresa'),
                  'base': ad['base'], 'sobe': {x: (ad['hist'].get(x) or {}).get('sobe') for x in ('win', 'wdo')},
                  'n': {x: (ad['hist'].get(x) or {}).get('n') for x in ('win', 'wdo')},
                  'reacao': {x: ((ad.get('hoje') or {}).get(x) if (ad.get('hoje') or {}).get(x) is not None else (velho.get('reacao') or {}).get(x)) for x in ('win', 'wdo')}}
    pend = [e for e in evs.values() if None in e['reacao'].values() and (hoje - dt.date.fromisoformat(e['data'])).days <= 50]
    if pend:
        try:
            import reacao
            bs = {x: reacao.barras(sym) for x, sym in reacao.ATIVOS.items()}
            for e in pend:
                t0 = reacao.hora_ev({'data': e['data'], 'hora': e.get('hora')})
                for x in ('win', 'wdo'):
                    if t0 and e['reacao'][x] is None:
                        e['reacao'][x] = reacao.var(bs[x], t0)[0]
        except Exception as ex:
            tg.note('warning', f'Placar do histórico: reação pendente não medida ({ex.__class__.__name__})')
    for e in evs.values():
        e['acerto'] = {x: acerto(e['sobe'].get(x), e['reacao'].get(x)) for x in ('win', 'wdo')}
    pl['eventos'] = sorted(evs.values(), key=lambda e: e['data'])[-300:]
    pl['atualizado_em'] = dt.datetime.now(BRT).isoformat(timespec='seconds')
    if not SO_STORY:
        json.dump(pl, open(PLACAR_HIST, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def semana_em_eventos():
    """Sexta: os eventos fortes da semana (Antes × Depois) e o placar acumulado, para o canal."""
    if hoje.weekday() != 4:
        return []
    pl = (ler(PLACAR_HIST) or {}).get('eventos', [])
    ini = (hoje - dt.timedelta(days=4)).isoformat()
    evs = [e for e in pl if ini <= e['data'] <= hoje.isoformat()]
    if not evs:
        return []
    nomes = {'win': 'WIN', 'wdo': 'WDO'}
    l = ['📊 <b>A semana em eventos: o histórico acertou?</b>']
    for e in evs:
        d = dt.date.fromisoformat(e['data'])
        partes = []
        for k in ('win', 'wdo'):
            sb, v, a = e['sobe'].get(k), e['reacao'].get(k), e['acerto'].get(k)
            ind = '—' if sb is None else f'▲{sb}%' if sb >= 60 else f'▼{100 - sb}%' if sb <= 40 else 'dividido'
            res = 'pendente' if v is None else (f'{"+" if v > 0 else ""}{v:.2f}%'.replace('.', ',') + ('' if a is None else ' ✅' if a else ' ❌'))
            partes.append(f'{nomes[k]} {ind} → {res}')
        l.append(f'{["seg", "ter", "qua", "qui", "sex"][d.weekday()]} {d:%d/%m} <b>{tg.e(e["evento"])}</b>: ' + ' · '.join(partes))
    cont = lambda lst: (sum(1 for e in lst for k in ('win', 'wdo') if e['acerto'].get(k) is not None), sum(1 for e in lst for k in ('win', 'wdo') if e['acerto'].get(k)))
    n, ok = cont(evs)
    nt, okt = cont(pl)
    if n:
        l.append(f'Na semana: <b>{ok}/{n}</b>' + (f' · desde o início: <b>{okt}/{nt}</b> ({okt / nt * 100:.0f}%)' if nt > n else ''))
    l.append('<i>▲/▼ = lado para onde o ativo foi na maioria das vezes anteriores (60% ou mais). Dividido não conta.</i>')
    l.append('Placar completo, com todos os erros: lectnex.com.br/placar')
    return l


def texto_antes_depois(ad):
    """Linhas do Telegram (HTML)."""
    sp = {'acima': 'acima do consenso', 'abaixo': 'abaixo do consenso', 'em linha': 'em linha com o consenso'}.get(ad['surpresa'])
    l = [f'🧭 <b>Antes × depois · {tg.e(ad["evento"])}</b>']
    if sp:
        l.append(f'Veio {sp}' + (f' ({tg.e(str(ad["resultado"]))} × {tg.e(str(ad["consenso"]))})' if ad.get('resultado') and ad.get('consenso') else '') + '.')
    nomes = {'win': 'Ibovespa', 'wdo': 'dólar'}
    hs = [f'{nomes[k]} subiu em {h["sobe"]}% das {h["n"]} vezes' for k, h in ad['hist'].items() if h]
    if hs:
        l.append(('Quando veio assim antes: ' if ad['base'] == 'surpresa' else 'No histórico: ') + ' · '.join(hs) + '.')
    if ad.get('hoje'):
        hj = [f'{nomes[k]} {"+" if v > 0 else ""}{v:.2f}%'.replace('.', ',') for k, v in ad['hoje'].items() if v is not None]
        if hj:
            l.append('Hoje, 30 min depois: ' + ' · '.join(hj) + '.')
    else:
        l.append('Hoje: a reação sai com a bolsa fechada e é medida na abertura do próximo pregão.')
    return l


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

    resumo = {'data': hoje.isoformat(), 'ibov': {'preco': ibov['preco'], 'var': iv} if ibov and iv is not None else None,
              'dolar': {'preco': usd, 'var': uv} if usd else None, 'altas': [], 'baixas': [], 'termometro': {}, 'placar': None, 'agenda': None}
    linhas = [f'🔔 <b>Fechamento · {hoje:%d/%m}</b>']
    linhas.append(' · '.join(filter(None, [
        'IBOV <b>' + f'{ibov["preco"]:,.0f}'.replace(',', '.') + f'</b> ({pct(iv)})' if ibov and iv is not None else '',
        'Dólar <b>R$ ' + f'{usd:.3f}'.replace('.', ',') + f'</b> ({pct(uv)})' if usd else ''])))
    m = sorted([x for x in cot.get('mapa', []) if isinstance(x.get('var_pct'), (int, float))], key=lambda x: x['var_pct'])
    if len(m) >= 6:
        resumo['altas'] = [[x['ticker'], x['var_pct']] for x in m[::-1][:3]]; resumo['baixas'] = [[x['ticker'], x['var_pct']] for x in m[:3]]
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
            resumo['termometro'][k] = reg[k]
            partes.append(f'{k.upper()} {SETA[t]} → {"✅ acertou" if a else "❌ errou"} ({"IBOV" if k == "win" else "dólar"} {pct(var)})')
        if partes:
            placar['dias'] = [d for d in placar['dias'] if d['data'] != reg['data']] + [reg]
            placar['dias'] = sorted(placar['dias'], key=lambda d: d['data'])[-250:]
            ult = placar['dias'][-20:]
            tot = sum(1 for d in ult for k in ('win', 'wdo') if k in d)
            ok = sum(1 for d in ult for k in ('win', 'wdo') if d.get(k, {}).get('acerto'))
            placar['atualizado_em'] = dt.datetime.now(BRT).isoformat(timespec='seconds')
            if not SO_STORY:
                json.dump(placar, open('data/placar-termometro.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            if tot: resumo['placar'] = {'ok': ok, 'tot': tot, 'n': len(ult)}
            linhas += ['', '🎯 <b>Termômetro da manhã</b>'] + partes + [(f'Placar dos últimos {len(ult)} pregões:' if len(ult) > 1 else 'Placar (1º pregão):') + f' <b>{ok}/{tot}</b> ({ok / tot * 100:.0f}%)' if tot else '']

    try:
        ad = antes_depois()
    except Exception as e:
        ad = None
        tg.note('warning', f'Antes × depois indisponível: {e.__class__.__name__}')
    if ad:
        resumo['antes_depois'] = ad
        linhas += [''] + texto_antes_depois(ad)
    try:
        registrar_placar_historico(ad)
    except Exception as e:
        tg.note('warning', f'Placar do histórico não atualizado: {e.__class__.__name__}')
    try:
        sem = semana_em_eventos()
        if sem:
            linhas += [''] + sem
    except Exception as e:
        tg.note('warning', f'Semana em eventos indisponível: {e.__class__.__name__}')

    mex = manchetes_que_mexeram()
    if mex:
        resumo['manchetes'] = mex
        linhas += ['', '📰 <b>Manchetes do dia e o que veio depois</b>'] + mex + ['<i>O movimento seguinte não prova que a notícia foi a causa.</i>']

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
            top = sorted(evs, key=lambda e: -(e.get('importancia') or 1))[:3]
            top.sort(key=lambda e: (e.get('hora') is None, e.get('hora') or ''))
            resumo['agenda'] = {'nome': nome, 'eventos': [[e.get('hora') or 'dia', e['evento'], (e.get('importancia') or 1) >= 3] for e in top]}
            linhas += ['', f'📅 <b>{nome}</b>'] + [f'{e.get("hora") or "dia"} {tg.FLAG.get(e.get("pais"), "")} {tg.e(e["evento"])}{" ⚠️" if (e.get("importancia") or 1) >= 3 else ""}' for e in evs[:5]]

    linhas += ['', f'<a href="{tg.SITE}">Mercado Hoje →</a>', '<i>Educacional. Não é recomendação. Cotações com atraso de ~30 min.</i>']
    texto = '\n'.join(l for l in linhas if l is not None)
    if os.environ.get('FECH_JSON'):  # usado pelo story do fechamento
        json.dump(resumo, open(os.environ['FECH_JSON'], 'w', encoding='utf-8'), ensure_ascii=False)
    if SO_STORY:
        tg.note('notice', 'Prévia do story: resumo montado, nada postado no canal.')
        return
    if not tg.TOKEN:
        print(texto)
        tg.note('notice', 'Telegram não configurado; fechamento só impresso.')
        return
    ok = tg.enviar(texto)
    tg.note('notice' if ok else 'warning', 'Fechamento enviado ao Telegram' if ok else 'Fechamento não enviado')


if __name__ == '__main__':
    main()
