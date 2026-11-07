"""Confere às 21h45 (dias úteis) se algum evento forte de hoje já passou do horário e continua sem resultado no calendário.
Se houver, avisa no Telegram PRIVADO do dono (a rodada de resultados da noite falhou ou não achou fonte). Não publica nada.
"""
import datetime as dt
import json
import os
import re
import urllib.request

BRT = dt.timezone(dt.timedelta(hours=-3))


def main():
    agora = dt.datetime.now(BRT)
    cal = json.load(open('data/calendario.json', encoding='utf-8')).get('eventos', [])
    pend = []
    for e in cal:
        if e.get('data') != agora.date().isoformat() or (e.get('importancia') or 1) < 3 or e.get('resultado') not in (None, ''):
            continue
        if e.get('tipo') in ('feriado', 'vencimento-win', 'vencimento-wdo') or 'B3 fechada' in (e.get('evento') or ''):
            continue
        m = re.match(r'^(\d{1,2})h(\d{2})?$', e.get('hora') or '')
        if m and agora < agora.replace(hour=int(m[1]), minute=int(m[2] or 0)) + dt.timedelta(minutes=45):
            continue
        pend.append(f'{e.get("hora") or "?"} · {e["evento"]}')
    if e_copom := [p for p in pend if 'Copom' in p]:
        try:
            c = json.load(open('data/copom.json', encoding='utf-8'))
            if c.get('data') == agora.date().isoformat() and c.get('resultado'):
                pend = [p for p in pend if p not in e_copom]
        except Exception:
            pass
    if not pend:
        print('::notice::Resultados de hoje em dia.')
        return
    msg = ('⚠️ <b>Resultado não publicado</b>\nEstes eventos fortes de hoje já passaram do horário e continuam sem resultado no site:\n'
           + '\n'.join(f'• {p}' for p in pend) + '\n\nPeça ao Claude: "publica o resultado de hoje".')
    tok, chat = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip(), os.environ.get('TELEGRAM_ADMIN_CHAT_ID', '').strip()
    print(f'::warning::Sem resultado: {"; ".join(pend)}')
    if tok and chat and not chat.startswith('@'):
        req = urllib.request.Request(f'https://api.telegram.org/bot{tok}/sendMessage', headers={'Content-Type': 'application/json'},
                                     data=json.dumps({'chat_id': chat, 'text': msg, 'parse_mode': 'HTML'}).encode())
        urllib.request.urlopen(req, timeout=20).read()


if __name__ == '__main__':
    main()
