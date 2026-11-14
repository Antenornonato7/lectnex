"""Manda o texto de TEXTO para o chat privado do Telegram (TELEGRAM_ADMIN_CHAT_ID).
Usado pelos workflows "Alerta de falha" (texto puro) e "Aviso ao dono" (HTML=1: <b>/<i>; se o Telegram recusar o HTML,
reenvia como texto puro sem as tags). EXIGIR=1 faz a execução falhar quando não há chat privado configurado."""
import re
import json
import os
import sys
import urllib.error
import urllib.request

token = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
chat = os.environ.get('TELEGRAM_ADMIN_CHAT_ID', '').strip()
texto = os.environ.get('TEXTO', '').strip()[:3900]
print(texto)
if not (token and chat) or chat.startswith('@'):
    exigir = os.environ.get('EXIGIR') == '1'
    print(('::error::' if exigir else '::warning::') + 'Sem TELEGRAM_ADMIN_CHAT_ID (chat privado): alerta não enviado.')
    sys.exit(1 if exigir else 0)


def enviar(corpo):
    req = urllib.request.Request(f'https://api.telegram.org/bot{token}/sendMessage',
                                 data=json.dumps(corpo).encode(), headers={'Content-Type': 'application/json'})
    urllib.request.urlopen(req, timeout=20).read()


corpo = {'chat_id': chat, 'text': texto, 'disable_web_page_preview': True}
if os.environ.get('HTML') == '1':
    corpo['parse_mode'] = 'HTML'
try:
    enviar(corpo)
    print('Alerta enviado.')
except urllib.error.HTTPError as ex:
    if ex.code == 400 and 'parse_mode' in corpo:  # HTML malformado: manda sem formatação
        print('::warning::Telegram recusou o HTML; reenviando como texto puro.')
        corpo.pop('parse_mode')
        corpo['text'] = re.sub(r'</?(b|i)>', '', texto).replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        try:
            enviar(corpo)
            print('Alerta enviado (texto puro).')
            sys.exit(0)
        except urllib.error.HTTPError as ex2:
            ex = ex2
    print(f'::error::Telegram respondeu HTTP {ex.code}')
    sys.exit(1)
