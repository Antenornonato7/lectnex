"""Notificações no celular (OneSignal), disparadas junto com o workflow do Telegram.

- leitura: Leitura do Dia de um NOVO dia → assinantes com a tag leitura=1
- surpresa: evento que ganhou "surpresa" no calendário → tag surpresa=1
- agenda: dados fortes com horário → agendados para 5 min antes (send_after), com consenso e como WIN/WDO reagiram
  antes quando veio acima/abaixo (data/reacoes.json) → tag agenda=1
- resultado: dado forte saiu em linha com o consenso (os acima/abaixo já vão como "surpresa") → tag surpresa=1
  (chave de idempotência por evento: rodar várias vezes não duplica)

Precisa de ONESIGNAL_APP_ID e ONESIGNAL_API_KEY; sem eles, não faz nada.
"""
import datetime as dt, json, os, sys, urllib.error, urllib.request, uuid

sys.path.insert(0, os.path.dirname(__file__))
import telegram as tg

APP = os.environ.get('ONESIGNAL_APP_ID', '').strip()
KEY = os.environ.get('ONESIGNAL_API_KEY', '').strip()
BRT = dt.timezone(dt.timedelta(hours=-3))
NS = uuid.UUID('6f1c6f0e-3c1a-4c55-9a51-6c6563746e78')  # namespace Lectnex para as chaves


# tag leitura: 1 = Leitura do Dia, 2 = Leitura + Plano do Dia, 3 = só Plano (ver scripts/plano_push.py)
LEITURA = [{'field': 'tag', 'key': 'leitura', 'relation': '=', 'value': '1'}, {'operator': 'OR'},
           {'field': 'tag', 'key': 'leitura', 'relation': '=', 'value': '2'}]


def enviar_filtro(filtros, titulo, texto, url, chave):
    return enviar('acoes', titulo, texto, url, chave, filtros=filtros)


def enviar(tag, titulo, texto, url, chave, quando=None, filtros=None):
    corpo = {'app_id': APP, 'target_channel': 'push',
             'filters': filtros or [{'field': 'tag', 'key': tag, 'relation': '=', 'value': '1'}],
             'headings': {'en': titulo, 'pt': titulo}, 'contents': {'en': texto, 'pt': texto},
             'url': url, 'idempotency_key': str(uuid.uuid5(NS, chave)), 'ttl': 3600}
    if quando:
        corpo['send_after'] = quando.astimezone(dt.timezone.utc).strftime('%Y-%m-%d %H:%M:%S GMT+0000')
    j, erro, corpo_erro = None, None, ''
    for esquema in ('Key', 'Basic'):  # chave nova (Key) ou chave REST antiga (Basic)
        req = urllib.request.Request('https://api.onesignal.com/notifications', data=json.dumps(corpo).encode(),
                                     headers={'Content-Type': 'application/json', 'Authorization': f'{esquema} {KEY}'})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                j = json.load(r)
            break
        except urllib.error.HTTPError as e:
            erro, corpo_erro = e.code, e.read().decode(errors='replace')[:200]
            if e.code != 401:
                break
        except Exception as e:
            erro, corpo_erro = 'rede', type(e).__name__  # nunca imprime a mensagem: pode conter o cabeçalho com a chave
            break
    if j is None:
        tg.note('warning', f'OneSignal recusou [{tag}] ({erro}): {corpo_erro}')
        return False
    destino = 'agendado ' + corpo['send_after'] if quando else 'enviado'
    if j.get('errors'):
        tg.note('warning', f'Push [{tag}] {titulo}: {destino} com aviso {j.get("errors")} (id {j.get("id")})')
    else:
        tg.note('notice', f'Push [{tag}] {titulo}: {destino} (id {j.get("id")})')
    return True


def _pct(v):
    return ('+' if v > 0 else '−' if v < 0 else '') + f'{abs(v):.2f}%'.replace('.', ',')


def historico(tipo, direcao=None):
    """'acima: WIN +0,04% · WDO −0,16% (8×)' a partir das divulgações anteriores do mesmo dado."""
    try:
        rs = [x for x in json.load(open('data/reacoes.json', encoding='utf-8'))['registros'] if x.get('tipo') == tipo]
    except Exception:
        return ''
    partes = []
    for d in ([direcao] if direcao else ['acima', 'abaixo']):
        sel = [x for x in rs if x.get('surpresa') == d]
        med = {k: [x[k] for x in sel if isinstance(x.get(k), (int, float))] for k in ('win', 'wdo')}
        if med['win'] or med['wdo']:
            partes.append(f'{d}: ' + ' · '.join(f'{k.upper()} {_pct(sum(v) / len(v))}' for k, v in med.items() if v) + f' ({len(sel)}×)')
    return ' | '.join(partes)


def forte(ev):
    """Mesmo critério dos eventos ao vivo: importância 3, ou 2 que mexe em WIN/WDO/DI (2+) durante o pregão."""
    imp, ativos = ev.get('importancia') or 1, [k for k in ('win', 'wdo', 'di') if (ev.get('impacto') or {}).get(k)]
    t = hora_evento(ev)
    return imp >= 3 or (imp >= 2 and len(ativos) >= 2 and t is not None and dt.time(9, 0) <= t.time() <= dt.time(18, 30))


def hora_evento(ev):
    h = str(ev.get('hora') or '').strip()
    if 'h' not in h or not ev.get('data'):
        return None
    hh, mm = (h.split('h') + [''])[:2]
    try:
        d = dt.date.fromisoformat(ev['data'])
        return dt.datetime(d.year, d.month, d.day, int(hh), int(mm or 0), tzinfo=BRT)
    except ValueError:
        return None


def main():
    if not APP or not KEY:
        tg.note('notice', 'Alertas no celular não configurados (faltam ONESIGNAL_APP_ID e/ou ONESIGNAL_API_KEY).')
        return
    if not KEY.startswith('os_v2_') or any(c.isspace() for c in KEY):
        tg.note('warning', 'O segredo do OneSignal não parece uma App API Key (deve ser uma linha só começando com os_v2_app_). Nada foi enviado.')
        return
    site = tg.SITE
    if os.environ.get('TESTE'):
        for tag in ('surpresa', 'agenda', 'leitura'):
            enviar(tag, '✅ Alertas do Lectnex ativos', 'Teste: é assim que os alertas vão chegar.', site, f'teste-{tag}-{dt.datetime.now().isoformat()}', filtros=LEITURA if tag == 'leitura' else None)
        return
    l, la = tg.atual('data/leitura.json'), tg.anterior('data/leitura.json')
    if l and l.get('data') and (not la or la.get('data') != l['data']):
        enviar('leitura', '📊 Leitura do Dia', l.get('titulo') or 'A leitura de hoje está no ar', site + '#leitura', 'leitura-' + l['data'], filtros=LEITURA)
    c, ca = tg.atual('data/calendario.json'), tg.anterior('data/calendario.json')
    if not c:
        return
    ja = {tg.chave(ev) for ev in (ca or {}).get('eventos', []) if ev.get('surpresa')}
    ja_res = {tg.chave(ev) for ev in (ca or {}).get('eventos', []) if ev.get('resultado')}
    agora = dt.datetime.now(BRT)
    for ev in c.get('eventos', []):
        s = ev.get('surpresa')
        if s and s.get('direcao') in ('acima', 'abaixo') and ev.get('resultado') and tg.chave(ev) not in ja:
            seta = '▲ acima' if s['direcao'] == 'acima' else '▼ abaixo'
            texto = f'Saiu {ev["resultado"]}' + (f' · consenso {ev["consenso"]}' if ev.get('consenso') else '') + (f'. {s["reacao"]}' if s.get('reacao') else '')
            h = historico(ev.get('tipo'), s['direcao'])
            if h and not s.get('reacao'):
                texto += f'. Antes, quando veio {h}'
            enviar('surpresa', f'⚡ {ev["evento"]}: {seta} do consenso', texto, site + '#pregao', 'surpresa-' + tg.chave(ev))
        elif ev.get('resultado') and forte(ev) and not s and ev.get('consenso') and tg.chave(ev) not in ja_res:
            enviar('surpresa', f'📊 {ev["evento"]}: saiu {ev["resultado"]}', f'Em linha com o consenso ({ev["consenso"]}).', site + '#pregao', 'resultado-' + tg.chave(ev))
        t = hora_evento(ev)
        if forte(ev) and t and not ev.get('resultado'):
            quando = t - dt.timedelta(minutes=5)
            if agora < quando < agora + dt.timedelta(days=7):
                imp = ' · '.join(f'{k.upper()} {tg_seta}' for k, v in (ev.get('impacto') or {}).items() for tg_seta in [{'alta': '▲', 'baixa': '▼', 'volatil': '↕'}.get(v, '')] if tg_seta)
                h = historico(ev.get('tipo'))
                enviar('agenda', f'⏱ {ev["evento"]} em 5 min', f'{ev.get("hora")} de Brasília' + (f' · cons. {ev["consenso"]}' if ev.get('consenso') else '') +
                       (f'. Antes, quando veio {h}' if h else (f' · {imp}' if imp else '')), site + '#pregao', f'agenda5-{tg.chave(ev)}', quando=quando)


if __name__ == '__main__':
    main()
