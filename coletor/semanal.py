"""Resumo da semana (domingo): Ibovespa, dólar, juros, placar do termômetro, surpresas e agenda da próxima semana.
Envia para o Telegram e para a newsletter (Buttondown; se o envio for recusado, fica como rascunho).
ENVIAR=1 envia de verdade; sem isso só imprime o texto (teste)."""
import datetime as dt, html, json, os, sys, urllib.error, urllib.request

sys.path.insert(0, os.path.dirname(__file__))
import telegram as tg

BRT = dt.timezone(dt.timedelta(hours=-3))
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36', 'Accept': 'application/json,*/*'}
SITE = tg.SITE
ENVIAR = bool(os.environ.get('ENVIAR'))
BD = os.environ.get('BUTTONDOWN_API_KEY', '').strip()
FLAG = tg.FLAG
DIAS = ['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom']


def ler(p):
    try:
        return json.load(open(p, encoding='utf-8'))
    except Exception:
        return None


def br(v, casas=2):
    return f'{v:,.{casas}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def pct(v):
    return ('+' if v > 0 else '−' if v < 0 else '') + br(abs(v)) + '%'


def diarios(sym):
    for host in ('query2', 'query1'):
        try:
            url = f'https://{host}.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=1mo'
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                j = json.load(r)['chart']['result'][0]
            return [(dt.datetime.fromtimestamp(t, BRT).date(), c) for t, c in zip(j['timestamp'], j['indicators']['quote'][0]['close']) if c]
        except Exception:
            continue
    return []


def semana_var(sym, seg, sex):
    s = diarios(sym)
    fim = [c for d, c in s if d <= sex and d >= seg]
    ini = [c for d, c in s if d < seg]
    if not fim or not ini:
        return None, None
    return fim[-1], (fim[-1] / ini[-1] - 1) * 100


def main():
    hoje = dt.datetime.now(BRT).date()
    seg = hoje - dt.timedelta(days=(hoje.weekday() - 0) % 7 or 7) if hoje.weekday() != 6 else hoje - dt.timedelta(days=6)
    sex, prox = seg + dt.timedelta(days=4), seg + dt.timedelta(days=7)
    ib, ibv = semana_var('%5EBVSP', seg, sex)
    us, usv = semana_var('BRL%3DX', seg, sex)
    # juros: vencimento prefixado mais longo, último dado da semana × último da semana anterior
    juros = None
    cv = ler('data/curva.json') or {}
    h = cv.get('historico', {})
    dfim = max([d for d in h if seg.isoformat() <= d <= sex.isoformat()], default=None)
    dini = max([d for d in h if d < seg.isoformat()], default=None)
    if dfim and dini:
        a = {p['venc']: p for p in h[dini].get('pre', [])}
        comuns = [p for p in h[dfim].get('pre', []) if p['venc'] in a]
        if comuns:
            p = comuns[-1]; juros = (p['venc'][:4], p['taxa'], (p['taxa'] - a[p['venc']]['taxa']) * 100)
    # placar e surpresas
    pl = [d for d in (ler('data/placar-termometro.json') or {}).get('dias', []) if seg.isoformat() <= d['data'] <= sex.isoformat()]
    tot = sum(1 for d in pl for k in ('win', 'wdo') if k in d); ok = sum(1 for d in pl for k in ('win', 'wdo') if d.get(k, {}).get('acerto'))
    sem = (ler(f'data/semana/{seg.isoformat()}.json') or {}).get('eventos', [])
    surp = [e for e in sem if e.get('surpresa') and e['surpresa'].get('direcao') in ('acima', 'abaixo') and e.get('resultado')]
    cal = (ler(f'data/semana/{prox.isoformat()}.json') or {}).get('eventos', []) or [e for e in (ler('data/calendario.json') or {}).get('eventos', []) if prox.isoformat() <= e.get('data', '') <= (prox + dt.timedelta(days=6)).isoformat()]
    altos = sorted([e for e in cal if (e.get('importancia') or 1) >= 3], key=lambda e: (e['data'], e.get('hora') or ''))[:7]
    titulo = f'Resumo da semana · {seg:%d/%m} a {sex:%d/%m}'

    # Telegram (HTML)
    e = tg.e
    t = [f'🗓 <b>{titulo}</b>', '']
    if ib: t.append(f'Ibovespa <b>{br(ib, 0)}</b> ({pct(ibv)} na semana)')
    if us: t.append(f'Dólar <b>R$ {br(us, 3)}</b> ({pct(usv)} na semana)')
    if juros: t.append(f'Juro prefixado {juros[0]}: <b>{br(juros[1])}%</b> ({"+" if juros[2] >= 0 else "−"}{abs(round(juros[2]))} bps)')
    if tot: t += ['', f'🎯 Termômetro: <b>{ok}/{tot}</b> acertos na semana']
    if surp: t += ['', '⚡ <b>Surpresas</b>'] + [f'{FLAG.get(x.get("pais"), "")} {e(x["evento"])}: {e(x["resultado"])} (cons. {e(x.get("consenso") or "—")})' for x in surp[:5]]
    if altos: t += ['', '📅 <b>Próxima semana</b>'] + [f'{DIAS[dt.date.fromisoformat(x["data"]).weekday()]} {e(x.get("hora") or "")} {FLAG.get(x.get("pais"), "")} {e(x["evento"])}' for x in altos]
    t += ['', f'<a href="{SITE}semana/{prox.isoformat()}.html">Agenda completa da semana →</a>', '<i>Educacional. Não é recomendação.</i>']
    texto_tg = '\n'.join(t)

    # Newsletter (markdown)
    m = [f'Os números da semana de **{seg:%d/%m} a {sex:%d/%m}** e o que vem pela frente.', '', '## Como fechou']
    if ib: m.append(f'- **Ibovespa:** {br(ib, 0)} pontos ({pct(ibv)} na semana)')
    if us: m.append(f'- **Dólar à vista:** R$ {br(us, 3)} ({pct(usv)} na semana)')
    if juros: m.append(f'- **Juro prefixado {juros[0]} (Tesouro):** {br(juros[1])}% ao ano ({"+" if juros[2] >= 0 else "−"}{abs(round(juros[2]))} bps)')
    if tot: m += ['', f'**Placar do termômetro:** {ok} de {tot} acertos na semana. [Ver o histórico]({SITE}#placar-term)']
    if surp: m += ['', '## Surpresas da semana'] + [f'- {x["evento"]}: **{x["resultado"]}** (consenso {x.get("consenso") or "—"}){" — " + x["surpresa"]["reacao"] if x["surpresa"].get("reacao") else ""}' for x in surp[:6]]
    if altos: m += ['', '## O que move WIN, WDO e DI na próxima semana'] + [f'- **{DIAS[dt.date.fromisoformat(x["data"]).weekday()]} {x.get("hora") or ""}** · {x["evento"]}' for x in altos]
    m += ['', f'[Agenda completa da semana]({SITE}semana/{prox.isoformat()}.html) · [Mercado Hoje]({SITE})', '', '_Conteúdo educacional. Não é recomendação de investimento._']
    texto_md = '\n'.join(m)

    if not ENVIAR:
        print(texto_tg); print('-----'); print(texto_md)
        tg.note('notice', f'Resumo semanal (teste): IBOV {ibv} · USD {usv} · juros {juros} · placar {ok}/{tot} · {len(surp)} surpresas · {len(altos)} eventos'); return
    if tg.TOKEN:
        tg.note('notice' if tg.enviar(texto_tg) else 'warning', 'Resumo semanal no Telegram')
    if BD:
        def post(status):
            req = urllib.request.Request('https://api.buttondown.com/v1/emails', data=json.dumps({'subject': titulo, 'body': texto_md, 'status': status}).encode(), method='POST',
                                         headers={'Authorization': f'Token {BD}', 'Content-Type': 'application/json', 'X-API-Version': '2026-04-01', 'X-Buttondown-Live-Dangerously': 'true'})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status
        try:
            post('about_to_send'); tg.note('notice', 'Resumo semanal enviado por e-mail')
        except urllib.error.HTTPError as err:
            if err.code == 403:
                try:
                    post('draft'); tg.note('warning', 'Resumo semanal em rascunho no Buttondown (envio pela API não liberado)')
                except urllib.error.HTTPError as e2:
                    tg.note('warning', f'Buttondown recusou o rascunho ({e2.code})')
            else:
                tg.note('warning', f'Buttondown recusou ({err.code})')


if __name__ == '__main__':
    main()
