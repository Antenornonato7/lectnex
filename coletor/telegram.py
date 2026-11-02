"""Publica no canal do Telegram do Lectnex.

- Leitura do Dia: quando data/leitura.json de um NOVO dia é publicado.
- Surpresas: quando um evento de data/calendario.json ganha "surpresa" (comparado ao commit anterior).
- TESTE=1: manda uma mensagem de teste.

Precisa dos segredos TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID (ex.: @lectnex). Sem eles, não faz nada.
"""
import html, json, os, subprocess, sys, urllib.request, urllib.error

SITE = 'https://lectnex.com.br/'
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


def enviar(texto, previa=None):
    req = urllib.request.Request(
        f'https://api.telegram.org/bot{TOKEN}/sendMessage',
        data=json.dumps({'chat_id': CHAT, 'text': texto, 'parse_mode': 'HTML', **({'link_preview_options': {'url': previa, 'prefer_large_media': True, 'show_above_text': True}} if previa else {'disable_web_page_preview': True})}).encode(),
        headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            j = json.load(r)
            if j.get('ok'):
                note('notice', f'Mensagem {j["result"]["message_id"]} publicada')
            return j.get('ok', False)
    except urllib.error.HTTPError as err:
        note('warning', f'Telegram recusou ({err.code}): {err.read().decode()[:200]}')
        return False


def msg_leitura(d, link=None):
    dd = '/'.join(reversed(d['data'].split('-')[1:]))
    linhas = [f'📊 <b>Leitura do Dia · {dd}</b>', f'<b>{e(d.get("titulo"))}</b>', '']
    linhas += [f'• {e(x)}' for x in d.get('resumo', [])]
    t = d.get('termometro')
    if t:
        linhas += ['', '<b>Termômetro</b>'] + [f'{k.upper()}: {TERM.get(t[k].get("leitura"), e(t[k].get("leitura")))} — {e(t[k].get("motivo"))}' for k in ('win', 'wdo') if k in t]
    if d.get('proximo_pregao'):
        p = d['proximo_pregao']
        linhas += ['', f'<b>Próximo pregão ({e("/".join(reversed(p.get("data", "").split("-")[1:])))})</b>: {e(p.get("o_que_esperar"))}']
    linhas += ['', f'<a href="{link or SITE + "#leitura"}">Leitura completa, agenda e notícias →</a>', '<i>Conteúdo educacional. Não é recomendação de investimento.</i>']
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


def api(metodo, dados):
    req = urllib.request.Request(f'https://api.telegram.org/bot{TOKEN}/{metodo}', data=json.dumps(dados).encode(), headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)
    except urllib.error.HTTPError as err:
        return {'ok': False, 'description': err.read().decode()[:200]}


def boas_vindas():
    texto = '\n'.join([
        '👋 <b>Bem-vindo ao Lectnex</b>',
        'Educação conectada ao mercado, para quem opera <b>mini índice (WIN)</b>, <b>mini dólar (WDO)</b> e <b>juros (DI)</b>.',
        '',
        '<b>O que chega aqui</b>',
        '📊 <b>Leitura do Dia</b> · todo dia por volta das 7h45: resumo, termômetro de WIN e WDO e o que esperar do pregão.',
        '⚡ <b>Alertas de surpresa</b> · quando um dado (IPCA, payroll, Copom…) sai fora do consenso, com a reação típica dos ativos.',
        '',
        '<b>No site</b>',
        f'• <a href="{SITE}">Mercado Hoje</a>: calendário, mapa da bolsa e notícias',
        f'• <a href="{SITE}#pregao">Modo Pregão</a>: tela única para deixar aberta no celular',
        f'• <a href="{SITE}futuros.html#plano">Plano do Dia e Diário de Trades</a>',
        f'• <a href="{SITE}#leitura">Leitura do Dia por e-mail</a>',
        '',
        '<i>Conteúdo educacional. Não é recomendação de investimento. Operar derivativos envolve risco de perdas.</i>'])
    r = api('sendMessage', {'chat_id': CHAT, 'text': texto, 'parse_mode': 'HTML', 'disable_web_page_preview': True})
    if not r.get('ok'):
        note('warning', 'Boas-vindas não enviada: ' + str(r.get('description'))); return
    p = api('pinChatMessage', {'chat_id': CHAT, 'message_id': r['result']['message_id'], 'disable_notification': True})
    note('notice' if p.get('ok') else 'warning', 'Boas-vindas enviada e fixada' if p.get('ok') else 'Boas-vindas enviada, mas sem permissão para fixar: ' + str(p.get('description')))


def contar():
    r = api('getChatMemberCount', {'chat_id': CHAT})
    if not r.get('ok'):
        note('warning', 'Não consegui contar seguidores: ' + str(r.get('description'))); return
    import datetime
    json.dump({'seguidores': r['result'], 'atualizado_em': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')},
              open('data/telegram.json', 'w', encoding='utf-8'), ensure_ascii=False)
    note('notice', f'Telegram: {r["result"]} seguidores')


def main():
    if not TOKEN or not CHAT:
        note('warning', 'Telegram não configurado: falta ' + ' e '.join(n for n, v in (('TELEGRAM_BOT_TOKEN', TOKEN), ('TELEGRAM_CHAT_ID', CHAT)) if not v))
        return
    if os.environ.get('TOKEN_EM_VARIABLES'):
        note('warning', 'O token do Telegram está em Variables (visível). Mova para Secrets com o nome TELEGRAM_BOT_TOKEN.')
    acao = os.environ.get('ACAO', '')
    if acao == 'push-teste':
        return
    if acao == 'leitura-arquivo':  # chamado pelo workflow do Arquivo, depois que a página e a imagem da edição estão no ar
        d = atual('data/leitura.json')
        if d and d.get('data'):
            link = f"{SITE}leitura/{d['data']}.html"
            ok = enviar(msg_leitura(d, link), previa=link)
            note('notice' if ok else 'warning', 'Leitura no Telegram com imagem' if ok else 'Leitura no Telegram falhou')
        return
    if acao == 'boas-vindas':
        boas_vindas(); return
    if acao == 'contar':
        contar(); return
    if acao == 'info':
        r = api('getChat', {'chat_id': CHAT}); pm = (r.get('result') or {}).get('pinned_message') or {}
        me = (api('getMe', {}).get('result') or {})
        note('notice', f'Bot: @{me.get("username")} ({me.get("first_name")}) · Mensagem fixada: {pm.get("message_id")}'); return
    if acao == 'apagar':
        mid = os.environ.get('MSG_ID', '').strip()
        r = api('deleteMessage', {'chat_id': CHAT, 'message_id': int(mid)}) if mid.isdigit() else {'ok': False, 'description': 'informe o número da mensagem'}
        note('notice' if r.get('ok') else 'warning', f'Mensagem {mid} apagada' if r.get('ok') else f'Não apaguei {mid}: {r.get("description")}'); return
    if os.environ.get('TESTE'):
        ok = enviar('✅ <b>Canal do Lectnex conectado.</b>\nAqui vão chegar a Leitura do Dia e os alertas de surpresa do calendário.\n' + f'<a href="{SITE}">{SITE}</a>')
        note('notice' if ok else 'warning', 'Teste do Telegram enviado' if ok else 'Teste do Telegram falhou')
        return
    enviados = 0
    l, la = atual('data/leitura.json'), anterior('data/leitura.json')
    if not os.environ.get('SEM_LEITURA') and l and l.get('data') and (not la or la.get('data') != l['data']):
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
