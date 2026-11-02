"""Resumo do dono: todo dia às 19h25 (Brasília), no chat PRIVADO do Telegram (TELEGRAM_ADMIN_CHAT_ID).

Junta o que o site já registra: Leitura do Dia (hora em que saiu), fechamento/placar do termômetro,
atualizações de cotação, falhas do monitor no dia, seguidores do canal e os eventos fortes de amanhã.
Nunca vai para o canal público. TESTE=1 manda mesmo assim (e marca como teste).
"""
import datetime as dt
import html
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

BRT = dt.timezone(dt.timedelta(hours=-3))
AGORA = dt.datetime.now(BRT)
HOJE = AGORA.date()
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
CHAT = os.environ.get('TELEGRAM_ADMIN_CHAT_ID', '').strip()
TESTE = os.environ.get('TESTE') == '1'
DIAS = ['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom']
e = lambda s: html.escape(str(s or ''), quote=False)


def ler(p):
    try:
        return json.load(open(p, encoding='utf-8'))
    except Exception:
        return None


def git(*a):
    return subprocess.run(['git', *a], capture_output=True, text=True).stdout.strip()


def brt(iso):
    t = dt.datetime.fromisoformat(iso)
    return (t if t.tzinfo else t.replace(tzinfo=BRT)).astimezone(BRT)


def leitura():
    """Hora do 1º commit do dia em que data/leitura.json passou a ter a data de hoje."""
    for linha in reversed(git('log', '--since=2 days ago', '--format=%H %cI', '--', 'data/leitura.json').splitlines()):
        h, t = linha.split(' ', 1)
        try:
            d = json.loads(git('show', f'{h}:data/leitura.json'))
        except Exception:
            continue
        if d.get('data') == HOJE.isoformat():
            return brt(t).strftime('%Hh%M'), d.get('titulo'), d.get('tipo')
    return None, None, None


def seguidores():
    atual = (ler('data/telegram.json') or {}).get('seguidores')
    antes = None
    h = git('log', '-1', '--before', (AGORA - dt.timedelta(days=1)).isoformat(), '--format=%H', '--', 'data/telegram.json')
    if h:
        try:
            antes = json.loads(git('show', f'{h}:data/telegram.json')).get('seguidores')
        except Exception:
            pass
    return atual, antes


def main():
    cal = ler('data/calendario.json') or {}
    eventos = cal.get('eventos', [])
    feriado = any(ev.get('data') == HOJE.isoformat() and 'B3 fechada' in (ev.get('evento') or '') for ev in eventos)
    pregao = HOJE.weekday() < 5 and not feriado

    L = [f'📋 <b>Resumo do dia · {DIAS[HOJE.weekday()]} {HOJE:%d/%m}</b>' + (' <i>(teste)</i>' if TESTE else '')]
    L.append('🟢 Dia de pregão' if pregao else '⚪ Sem pregão hoje' + (' (feriado)' if feriado else ''))

    hora, titulo, tipo = leitura()
    if hora:
        atraso = ' ⚠️ depois das 9h' if int(hora[:2]) >= 9 else ''
        L.append(f'📰 Leitura saiu às {hora}{atraso}: “{e(titulo)}”')
    else:
        L.append('📰 ❌ Leitura de hoje <b>não saiu</b>')

    if pregao:
        dia = next((d for d in (ler('data/placar-termometro.json') or {}).get('dias', []) if d.get('data') == HOJE.isoformat()), None)
        if dia:
            partes = [f"{k.upper()} {'✅' if dia[k].get('acerto') else '❌'} ({dia[k].get('var_pct'):+.2f}%)".replace('.', ',') for k in ('win', 'wdo') if k in dia]
            L.append('🎯 Fechamento publicado · termômetro: ' + ' · '.join(partes))
        else:
            L.append('🎯 ⚠️ Sem registro do fechamento/placar de hoje (sai às 19h05)')
        n = sum(1 for t in git('log', '--since=1 day ago', '--format=%cI', '--', 'data/cotacoes.json').splitlines() if brt(t).date() == HOJE)
        L.append(f"💹 Cotações atualizadas {n}× no pregão" + (' ⚠️ (esperado ~18)' if n < 10 else ''))

    st = ler('data/status.json') or {}
    hoje_checks = [f for t, f in st.get('checks', []) if brt(t).date() == HOJE]
    falhas = {}
    for f in hoje_checks:
        for k in f:
            falhas[k] = falhas.get(k, 0) + 1
    if not hoje_checks:
        L.append('🩺 Monitor sem registros hoje')
    elif not falhas:
        L.append(f'🩺 Site: {len(hoje_checks)} verificações, nenhuma falha')
    else:
        L.append(f'🩺 Site: falhas em {len(falhas)} item(ns) — ' + '; '.join(f'{e(k)} ({n}h)' for k, n in sorted(falhas.items(), key=lambda x: -x[1])))

    atual, antes = seguidores()
    if atual is not None:
        delta = f' ({atual - antes:+d} em 24h)' if antes is not None else ''
        L.append(f'👥 Canal @lectnex: {atual} seguidores{delta}')

    amanha = HOJE + dt.timedelta(days=1)
    fortes = [ev for ev in eventos if ev.get('data') == amanha.isoformat() and (ev.get('importancia') or 0) >= 3]
    if fortes:
        L.append(f'\n🗓️ <b>Amanhã ({DIAS[amanha.weekday()]})</b>')
        L += [f"• {e(ev.get('hora') or 'dia todo')} · {e(ev.get('evento'))}" for ev in sorted(fortes, key=lambda x: x.get('hora') or '')[:5]]

    L.append('\n<a href="https://lectnex.com.br/status.html">Status do site</a>')
    texto = '\n'.join(L)
    print(texto)

    if not (TOKEN and CHAT) or CHAT.startswith('@'):
        print('::warning::Sem TELEGRAM_ADMIN_CHAT_ID (chat privado): resumo não enviado.')
        return
    req = urllib.request.Request(f'https://api.telegram.org/bot{TOKEN}/sendMessage',
                                 data=json.dumps({'chat_id': CHAT, 'text': texto, 'parse_mode': 'HTML', 'disable_web_page_preview': True}).encode(),
                                 headers={'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(req, timeout=20).read()
        print('Resumo enviado.')
    except urllib.error.HTTPError as ex:
        print(f'::error::Telegram respondeu HTTP {ex.code}')
        sys.exit(1)


if __name__ == '__main__':
    main()
