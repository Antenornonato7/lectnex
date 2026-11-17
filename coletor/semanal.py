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


def ao_vivo(caminho):
    try:
        req = urllib.request.Request(f'https://raw.githubusercontent.com/{os.environ.get("GITHUB_REPOSITORY", "Antenornonato7/lectnex")}/ao-vivo/{caminho}', headers=UA)
        return json.load(urllib.request.urlopen(req, timeout=20))
    except Exception:
        return None


def destaques_semana(seg, sex):
    """As 3 manchetes com maior reação em 30 min na semana (data/dias), com o dia para linkar a página do dia."""
    out = []
    for d in (ler('data/dias/indice.json') or {}).get('dias', []):
        if not (seg.isoformat() <= d <= sex.isoformat()):
            continue
        for mk in (ler(f'data/dias/{d}.json') or {}).get('marcadores', []):
            for campo, nome in (('ibov30', 'Ibovespa'), ('dolar30', 'dólar')):
                if mk.get(campo) is not None:
                    out.append((abs(mk[campo]), d, mk, nome, mk[campo]))
    out.sort(key=lambda x: -x[0])
    vistos, top = set(), []
    for _, d, mk, nome, v in out:
        h, m_ = map(int, mk['hora'].split(':'))
        if mk['titulo'][:40] in vistos or any(d == d2 and abs(h * 60 + m_ - int(mk2['hora'][:2]) * 60 - int(mk2['hora'][3:5])) < 30 for d2, mk2, _, _ in top):
            continue  # a mesma reação aparece em várias manchetes do mesmo momento: fica a primeira
        vistos.add(mk['titulo'][:40]); top.append((d, mk, nome, v))
        if len(top) == 3:
            break
    return top


def rankings():
    """Pódio do simulador (sexta) e do desafio SUBIU ou CAIU (último pregão da semana), gravados pelo robô do Discord."""
    sim, des = ao_vivo('discord/simulador.json') or {}, ao_vivo('discord/desafio.json') or {}
    hs = (sim.get('historico') or [{}])[-1] if sim.get('publicado') else {}
    return [x for x in hs.get('top', [])][:3], (des.get('ranking_anterior') or [])[:3]


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
    top3 = destaques_semana(seg, sex)
    pod_sim, pod_des = rankings()
    med = ['🥇', '🥈', '🥉']
    brl = lambda v: ('+' if v > 0 else '−' if v < 0 else '') + 'R$ ' + f'{abs(v):,}'.replace(',', '.')

    # Telegram (HTML)
    e = tg.e
    t = [f'🗓 <b>{titulo}</b>', '']
    if ib: t.append(f'Ibovespa <b>{br(ib, 0)}</b> ({pct(ibv)} na semana)')
    if us: t.append(f'Dólar <b>R$ {br(us, 3)}</b> ({pct(usv)} na semana)')
    if juros: t.append(f'Juro prefixado {juros[0]}: <b>{br(juros[1])}%</b> ({"+" if juros[2] >= 0 else "−"}{abs(round(juros[2]))} bps)')
    if tot: t += ['', f'🎯 Viés do modelo: <b>{ok}/{tot}</b> acertos na semana']
    if top3: t += ['', '📰 <b>As notícias que mais mexeram</b>'] + [f'{dt.date.fromisoformat(d):%d/%m} {mk["hora"]} · {e(mk["titulo"][:90])} → {nome} {pct(v)} em 30 min' for d, mk, nome, v in top3]
    if surp: t += ['', '⚡ <b>Surpresas</b>'] + [f'{FLAG.get(x.get("pais"), "")} {e(x["evento"])}: {e(x["resultado"])} (cons. {e(x.get("consenso") or "—")})' for x in surp[:5]]
    if altos: t += ['', '📅 <b>Próxima semana</b>'] + [f'{DIAS[dt.date.fromisoformat(x["data"]).weekday()]} {e(x.get("hora") or "")} {FLAG.get(x.get("pais"), "")} {e(x["evento"])}' for x in altos]
    if pod_sim: t += ['', '🎮 <b>Ranking do simulador</b>'] + [f'{med[i]} {e(x["nome"])}: {brl(x["r"])}' for i, x in enumerate(pod_sim)]
    t += ['', f'🎮 Segunda sai o novo pregão da semana: <a href="{SITE}simulador.html">jogue grátis</a> · ranking no <a href="https://discord.gg/kM6YcQA82P">Discord</a>']
    t += ['', f'<a href="{SITE}semana/{prox.isoformat()}.html">Agenda completa da semana →</a>', '<i>Educacional. Não é recomendação.</i>']
    texto_tg = '\n'.join(t)

    # Newsletter (markdown)
    m = [f'Os números da semana de **{seg:%d/%m} a {sex:%d/%m}** e o que vem pela frente.', '', '## Como fechou']
    if ib: m.append(f'- **Ibovespa:** {br(ib, 0)} pontos ({pct(ibv)} na semana)')
    if us: m.append(f'- **Dólar à vista:** R$ {br(us, 3)} ({pct(usv)} na semana)')
    if juros: m.append(f'- **Juro prefixado {juros[0]} (Tesouro):** {br(juros[1])}% ao ano ({"+" if juros[2] >= 0 else "−"}{abs(round(juros[2]))} bps)')
    if tot: m += ['', f'**Placar do viés do modelo (experimental):** {ok} de {tot} acertos na semana. [Ver o histórico]({SITE}#placar-term)']
    if top3: m += ['', '## As notícias que mais mexeram'] + [f'- **{dt.date.fromisoformat(d):%d/%m} {mk["hora"]}** · {mk["titulo"]} → {nome} **{pct(v)}** em 30 min ([o dia completo]({SITE}manchetes/{d}.html))' for d, mk, nome, v in top3]
    if surp: m += ['', '## Surpresas da semana'] + [f'- {x["evento"]}: **{x["resultado"]}** (consenso {x.get("consenso") or "—"}){" — " + x["surpresa"]["reacao"] if x["surpresa"].get("reacao") else ""}' for x in surp[:6]]
    if altos: m += ['', '## O que move WIN, WDO e DI na próxima semana'] + [f'- **{DIAS[dt.date.fromisoformat(x["data"]).weekday()]} {x.get("hora") or ""}** · {x["evento"]}' for x in altos]
    m += ['', '## Treine no simulador']
    if pod_sim: m += ['Pódio do pregão da semana:'] + [f'{med[i]} **{x["nome"]}**: {brl(x["r"])} em {x["ops"]} operação(ões)' for i, x in enumerate(pod_sim)] + ['']
    if pod_des: m += ['Desafio SUBIU ou CAIU no Discord:'] + [f'{med[i]} **{x["nome"]}**: {x["pts"]} ponto(s)' for i, x in enumerate(pod_des)] + ['']
    m += [f'Segunda sai o novo **pregão da semana**: opere um dia real de WIN ou WDO com as manchetes no horário, dinheiro fictício. [Jogar grátis]({SITE}simulador.html?utm_source=newsletter&utm_medium=email) · [Ranking no Discord](https://discord.gg/kM6YcQA82P)',
          '', f'👑 A Lectnex Pro está em construção. [Entre na lista de fundadores (grátis)]({SITE}pro.html?utm_source=newsletter&utm_medium=email) e vote no que vem primeiro.']
    m += ['', f'[Agenda completa da semana]({SITE}semana/{prox.isoformat()}.html) · [Mercado Hoje]({SITE})', '', '_Conteúdo educacional. Não é recomendação de investimento._']
    texto_md = '\n'.join(m)
    try:  # versão HTML com o modelo da marca (o markdown acima fica como reserva)
        import email_html as H
        cards = []
        if ib: v, c = H.var(ibv); cards.append(('IBOVESPA', br(ib, 0), v + ' na semana', c))
        if us: v, c = H.var(usv); cards.append(('DÓLAR', 'R$ ' + br(us, 3), v + ' na semana', c))
        if juros: cards.append((f'PRÉ {juros[0]}', br(juros[1]) + '%', f'{"+" if juros[2] >= 0 else "−"}{abs(round(juros[2]))} bps', H.VERM if juros[2] > 0 else H.VERDE))
        bl = [H.paragrafo(f'Os números da semana de <strong>{seg:%d/%m} a {sex:%d/%m}</strong> e o que vem pela frente.')]
        if cards: bl.append(H.secao('Como fechou', H.numeros(cards)))
        if tot: bl.append(H.paragrafo(f'🎯 <strong>Viés do modelo (experimental):</strong> {ok} de {tot} acertos na semana.', 14))
        if top3: bl.append(H.secao('As notícias que mais mexeram', H.lista([f'<strong>{dt.date.fromisoformat(d):%d/%m} {H.e(mk["hora"])}</strong> · {H.e(mk["titulo"])} → {nome} <strong style="color:{H.var(v)[1]}">{H.var(v)[0]}</strong> em 30 min · <a href="{SITE}manchetes/{d}.html" style="color:{H.TEAL_D}">o dia completo</a>' for d, mk, nome, v in top3])))
        if surp: bl.append(H.secao('Surpresas da semana', H.lista([f'<strong>{H.e(x["evento"])}:</strong> {H.e(x["resultado"])} (consenso {H.e(x.get("consenso") or "—")})' + (f'<br><span style="color:{H.CINZA};font-size:14px">{H.e(x["surpresa"]["reacao"])}</span>' if x["surpresa"].get("reacao") else '') for x in surp[:6]]), H.ORANGE))
        if altos: bl.append(H.secao('O que move WIN, WDO e DI na próxima semana', H.lista([f'<strong>{DIAS[dt.date.fromisoformat(x["data"]).weekday()]} {H.e(x.get("hora") or "")}</strong> · {H.e(x["evento"])}' for x in altos])))
        bl.append(H.botao('AGENDA COMPLETA DA SEMANA →', f'{SITE}semana/{prox.isoformat()}.html?utm_source=newsletter&utm_medium=email'))
        pod = ''
        if pod_sim: pod += '<div style="font-size:14px;margin-top:8px">' + '<br>'.join(f'{med[i]} <strong>{H.e(x["nome"])}</strong>: {brl(x["r"])}' for i, x in enumerate(pod_sim)) + '</div>'
        bl.append(H.destaque(f'<div style="{H.MONO}font-size:11px;letter-spacing:1.5px;color:#00B4A2;font-weight:700">SIMULADOR · PREGÃO DA SEMANA</div>'
                             '<div style="font-size:17px;font-weight:800;margin:6px 0">Segunda sai um novo pregão para treinar</div>' + pod +
                             H.botao('JOGAR GRÁTIS', SITE + 'simulador.html?utm_source=newsletter&utm_medium=email', H.TEAL, '#FFFFFF')))
        bl.append(H.paragrafo(f'👑 A Lectnex Pro está em construção. <a href="{SITE}pro.html?utm_source=newsletter&amp;utm_medium=email" style="color:{H.TEAL_D};font-weight:700">Entre na lista de fundadores (grátis)</a>.', 14))
        texto_md = H.documento(titulo, f'Ibovespa {pct(ibv)} e dólar {pct(usv)} na semana' if ib and us else titulo, bl)
    except Exception as err:
        tg.note('warning', f'Resumo semanal: HTML falhou, vai em texto ({err.__class__.__name__}: {err})')

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
