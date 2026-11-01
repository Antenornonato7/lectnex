"""Alerta no celular quando uma ação favorita passa de ±3% (e de novo ±6%) no dia.
Lê data/cotacoes.json (atraso ~30 min) e envia via OneSignal para quem marcou a ação (etiquetas a1, a2, a3).
A chave de idempotência por dia/ação/nível evita alerta repetido. Sem ONESIGNAL_API_KEY, não faz nada."""
import datetime as dt, json, os, sys

sys.path.insert(0, os.path.dirname(__file__))
import push  # reaproveita APP, KEY, envio com fallback Key/Basic
import telegram as tg

BRT = dt.timezone(dt.timedelta(hours=-3))
NIVEIS = (3, 6)


def main():
    if not push.APP or not push.KEY or not push.KEY.startswith('os_v2_'):
        tg.note('notice', 'Alertas de ações: OneSignal não configurado.'); return
    c = json.load(open('data/cotacoes.json', encoding='utf-8'))
    hoje = dt.datetime.now(BRT).date().isoformat()
    if not str(c.get('atualizado_em', '')).startswith(hoje):  # só com cotação do próprio dia (nada de alerta com o fechamento de sexta no sábado)
        tg.note('notice', 'Alertas de ações: cotação não é de hoje.'); return
    vistos = {}
    for x in c.get('mapa', []) + c.get('itens', []):  # itens (a cada 30 min) sobrescrevem o mapa (de hora em hora)
        if x.get('ticker') and x['ticker'] != 'IBOV' and isinstance(x.get('var_pct'), (int, float)):
            vistos[x['ticker']] = {**vistos.get(x['ticker'], {}), **{k: v for k, v in x.items() if v is not None}}
    enviados = 0
    for t, x in vistos.items():
        v = x['var_pct']
        for n in NIVEIS:
            if abs(v) < n:
                continue
            sinal = '+' if v > 0 else '−'
            corpo = {'filters': [{'field': 'tag', 'key': 'a1', 'relation': '=', 'value': t}, {'operator': 'OR'},
                                 {'field': 'tag', 'key': 'a2', 'relation': '=', 'value': t}, {'operator': 'OR'},
                                 {'field': 'tag', 'key': 'a3', 'relation': '=', 'value': t}]}
            ok = push.enviar_filtro(corpo['filters'], f'⚡ {t} {sinal}{abs(v):.1f}% hoje'.replace('.', ','),
                                    f'{x.get("setor") or "Ação"} · R$ {x.get("preco", 0):.2f}'.replace('.', ',') + ' · cotação com atraso de ~30 min',
                                    f'{tg.SITE}acoes.html?ticker={t}', f'acao-{hoje}-{t}-{n}-{sinal}')
            enviados += ok
    tg.note('notice', f'Alertas de ações: {enviados} enviado(s)')


if __name__ == '__main__':
    main()
