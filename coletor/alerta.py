"""Manda o texto de TEXTO para o chat privado do Telegram (TELEGRAM_ADMIN_CHAT_ID). Usado pelo workflow "Alerta de falha"."""
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
    print('::warning::Sem TELEGRAM_ADMIN_CHAT_ID (chat privado): alerta não enviado.')
    sys.exit(0)
req = urllib.request.Request(f'https://api.telegram.org/bot{token}/sendMessage',
                             data=json.dumps({'chat_id': chat, 'text': texto, 'disable_web_page_preview': True}).encode(),
                             headers={'Content-Type': 'application/json'})
try:
    urllib.request.urlopen(req, timeout=20).read()
    print('Alerta enviado.')
except urllib.error.HTTPError as ex:
    print(f'::error::Telegram respondeu HTTP {ex.code}')
    sys.exit(1)
