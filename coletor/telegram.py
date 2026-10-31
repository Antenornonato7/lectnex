"""Publica no canal do Telegram do Lectnex.

- Leitura do Dia: quando data/leitura.json de um NOVO dia é publicado.
- Surpresas: quando um evento de data/calendario.json ganha "surpresa" (comparado ao commit anterior).
- TESTE=1: manda uma mensagem de teste.

Precisa dos segredos TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID (ex.: @lectnex). Sem eles, não faz nada.
"""
import html, json, os, subprocess, sys, urllib.request, urllib.error

SITE = 'https://antenornonato7.github.io/lectnex/'
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
CHAT = os.environ.get('TELEGRAM_CHAT_ID', '').strip()
FLAG = {'BR': '🇧🇷', 'US': '🇺🇸', 'CN': '🇨🇳', 'EU': '🇪🇺', 'JP': '🇯🇵', 'UK': '🇬🇧'}
TERM = {'bullish': '🟢 viés de alta', 'bearish': '🔴 viés de baixa', 'neutro': '⚪ neutro'}
e = lambda s: html.escape(str(s or ''), quote=False)


def note(kind, msg):
    print(f'::{kind}::{msg}')


def atual(path):
    try:
        return json.load(open(path, encoding='utf-8'))
    except Exception:
        return None


def anterior(path):
    try:
        return json.loads(subprocess.run(['git', 'show', f'HEAD^:{path}'], capture_output=True, text=True, check=True).stdout)
    except Exception:
        return None


def enviar(texto):
    req = urllib.request.Request(
        f'https://api.telegram.org/bot{TOKEN}/sendMessage',
        data=json.dumps({'chat_id': CHAT, 'text': texto, 'parse_mode': 'HTML', 'disable_web_page_preview': True}).encode(),
        headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r).get('ok', False)
    except urllib.error.HTTPError as err:
        note('warning', f'Telegram recusou ({err.code}): {err.read().decode()[:200]}')
        return False


def msg_leitura(d):
    dd = '/'.join(reversed(d['data'].split('-')[1:]))
    linhas = [f'📊 <b>Leitura do Dia · {dd}</b>', f'<b>{e(d.get("titulo"))}</b>', '']
    linhas += [f'• {e(x)}' for x in d.get('resumo', [])]
    t = d.get('termometro')
    if t:
        linhas += ['', '<b>Termômetro</b>'] + [f'{k.upper()}: {TERM.get(t[k].get("leitura"), e(t[k].get("leitura")))} — {e(t[k].get("motivo"))}' for k in ('win', 'wdo') if k in t]
    if d.get('proximo_pregao'):
        p = d['proximo_pregao']
        linhas += ['', f'<b>Próximo pregão ({e("/".join(reversed(p.get("data", "").split("-")[1:])))})</b>: {e(p.get("o_que_esperar"))}']
    linhas += ['', f'<a href="{SITE}#leitura">Leitura completa, agenda e notícias →</a>', '<i>Conteúdo educacional. Não é recomendação de investimento.</i>']
    return '\n'.join(linhas)


def chave(ev):
    return f"{ev.get('data')}|{ev.get('hora')}|{ev.get('evento')}"


def msg_surpresa(ev):
    s = ev['surpresa']
    seta = '▲ acima' if s.get('direcao') == 'acima' else '▼ abaixo'
    linhas = [f'⚡ <b>SURPRESA {seta} do consenso</b>',
              f'{FLAG.get(ev.get("pais"), "")} <b>{e(ev.get("evento"))}</b> · {e(ev.get("hora"))}',
              f'Saiu <b>{e(ev.get("resultado"))}</b>' + (f' · consenso {e(ev.get("consenso"))}' if ev.get('consenso') else '') + (f' · anterior {e(ev.get("anterior"))}' if ev.get('anterior') else '')]
    if s.get('reacao'):
        linhas += ['', f'Reação típica: {e(s["reacao"])}']
    linhas += ['', f'<a href="{SITE}#cal-wrap">Calendário completo →</a>', '<i>Educacional. Não é recomendação.</i>']
    return '\n'.join(linhas)


def main():
    if not TOKEN or not CHAT:
        note('notice', 'Telegram não configurado (faltam TELEGRAM_BOT_TOKEN e/ou TELEGRAM_CHAT_ID).')
        return
    if os.environ.get('TESTE'):
        ok = enviar('✅ <b>Canal do Lectnex conectado.</b>\nAqui vão chegar a Leitura do Dia e os alertas de surpresa do calendário.\n' + f'<a href="{SITE}">{SITE}</a>')
        note('notice' if ok else 'warning', 'Teste do Telegram enviado' if ok else 'Teste do Telegram falhou')
        return
    enviados = 0
    l, la = atual('data/leitura.json'), anterior('data/leitura.json')
    if l and l.get('data') and (not la or la.get('data') != l['data']):
        enviados += enviar(msg_leitura(l))
    c, ca = atual('data/calendario.json'), anterior('data/calendario.json')
    if c:
        ja = {chave(ev) for ev in (ca or {}).get('eventos', []) if ev.get('surpresa')}
        for ev in c.get('eventos', []):
            s = ev.get('surpresa')
            if s and s.get('direcao') in ('acima', 'abaixo') and ev.get('resultado') and chave(ev) not in ja:
                enviados += enviar(msg_surpresa(ev))
    note('notice', f'Telegram: {enviados} mensagem(ns) enviada(s)')


if __name__ == '__main__':
    main()
