"""Notificações no celular (OneSignal), disparadas junto com o workflow do Telegram.

- leitura: Leitura do Dia de um NOVO dia → assinantes com a tag leitura=1
- surpresa: evento que ganhou "surpresa" no calendário → tag surpresa=1
- agenda: eventos de alto impacto com horário → agendados para 15 min antes (send_after) → tag agenda=1
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
            enviar(tag, '✅ Alertas do Lectnex ativos', 'Teste: é assim que os alertas vão chegar.', site, f'teste-{tag}-{dt.datetime.now().isoformat()}')
        return
    l, la = tg.atual('data/leitura.json'), tg.anterior('data/leitura.json')
    if l and l.get('data') and (not la or la.get('data') != l['data']):
        enviar('leitura', '📊 Leitura do Dia', l.get('titulo') or 'A leitura de hoje está no ar', site + '#leitura', 'leitura-' + l['data'])
    c, ca = tg.atual('data/calendario.json'), tg.anterior('data/calendario.json')
    if not c:
        return
    ja = {tg.chave(ev) for ev in (ca or {}).get('eventos', []) if ev.get('surpresa')}
    agora = dt.datetime.now(BRT)
    for ev in c.get('eventos', []):
        s = ev.get('surpresa')
        if s and s.get('direcao') in ('acima', 'abaixo') and ev.get('resultado') and tg.chave(ev) not in ja:
            seta = '▲ acima' if s['direcao'] == 'acima' else '▼ abaixo'
            texto = f'Saiu {ev["resultado"]}' + (f' · consenso {ev["consenso"]}' if ev.get('consenso') else '') + (f'. {s["reacao"]}' if s.get('reacao') else '')
            enviar('surpresa', f'⚡ {ev["evento"]}: {seta} do consenso', texto, site + '#cal-wrap', 'surpresa-' + tg.chave(ev))
        t = hora_evento(ev)
        if (ev.get('importancia') or 1) >= 3 and t and not ev.get('resultado'):
            quando = t - dt.timedelta(minutes=15)
            if agora < quando < agora + dt.timedelta(days=7):
                imp = ' · '.join(f'{k.upper()} {tg_seta}' for k, v in (ev.get('impacto') or {}).items() for tg_seta in [{'alta': '▲', 'baixa': '▼', 'volatil': '↕'}.get(v, '')] if tg_seta)
                enviar('agenda', f'⏱ {ev["evento"]} em 15 min', f'{ev.get("hora")} de Brasília' + (f' · cons. {ev["consenso"]}' if ev.get('consenso') else '') + (f' · {imp}' if imp else ''),
                       site + '#pregao', f'agenda2-{tg.chave(ev)}', quando=quando)


if __name__ == '__main__':
    main()
