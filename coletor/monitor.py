"""Monitor do lectnex.com.br: confere o site no ar como um visitante veria e avisa no Telegram (privado).

Checagens:
- Site: HTTPS válido (cadeado), página inicial respondendo e com a marca.
- Redirecionamentos: endereço antigo (github.io) e www levam a lectnex.com.br.
- Arquivos do site: CSS e JS principais carregam.
- Dados: cotações frescas no pregão, calendário do dia, Leitura do Dia publicada, curva de juros recente.

Avisa só quando algo MUDA (quebrou / voltou) e relembra a cada 6 h enquanto continuar quebrado.
Estado anterior em .monitor/estado.json (guardado pelo cache do Actions).

Segredos: TELEGRAM_BOT_TOKEN e TELEGRAM_ADMIN_CHAT_ID (seu chat PRIVADO com o bot, nunca o canal público).
Sem o chat privado, o job fica vermelho quando algo quebra (o GitHub avisa por e-mail).
TESTE=1 manda uma mensagem de teste.
"""
import datetime as dt
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

SITE = 'https://lectnex.com.br/'
BRT = dt.timezone(dt.timedelta(hours=-3))
AGORA = dt.datetime.now(BRT)
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
CHAT = os.environ.get('TELEGRAM_ADMIN_CHAT_ID', '').strip()
TESTE = os.environ.get('TESTE') == '1'
ESTADO = '.monitor/estado.json'
UA = {'User-Agent': 'LectnexMonitor/1.0 (+https://lectnex.com.br/)', 'Cache-Control': 'no-cache'}


def get(url, timeout=20):
    sep = '&' if '?' in url else '?'
    req = urllib.request.Request(f'{url}{sep}m={int(AGORA.timestamp())}', headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.geturl(), r.read()


def erro_legivel(ex):
    if isinstance(ex, urllib.error.URLError) and isinstance(ex.reason, ssl.SSLError):
        return f'certificado HTTPS inválido ({ex.reason.__class__.__name__})'
    if isinstance(ex, ssl.SSLError) or 'CERTIFICATE' in str(ex).upper():
        return 'certificado HTTPS inválido'
    if isinstance(ex, urllib.error.HTTPError):
        return f'HTTP {ex.code}'
    if isinstance(ex, urllib.error.URLError):
        return f'sem resposta ({ex.reason})'
    return f'{ex.__class__.__name__}: {ex}'


def idade_h(iso):
    t = dt.datetime.fromisoformat(iso)
    if t.tzinfo is None:
        t = t.replace(tzinfo=BRT)
    return (AGORA - t).total_seconds() / 3600


def checar():
    """Devolve {nome: (ok: bool|None, detalhe)}; None = não se aplica agora."""
    r = {}
    html = ''
    try:
        st, final, corpo = get(SITE)
        html = corpo.decode('utf-8', 'replace')
        r['Site no ar (HTTPS)'] = (st == 200 and 'Lectnex' in html, f'HTTP {st}' + ('' if 'Lectnex' in html else ', página sem a marca'))
    except Exception as ex:
        r['Site no ar (HTTPS)'] = (False, erro_legivel(ex))

    for nome, url in (('Endereço antigo redireciona', 'https://antenornonato7.github.io/lectnex/'), ('www redireciona', 'https://www.lectnex.com.br/')):
        try:
            _, final, _ = get(url)
            host = urllib.parse.urlsplit(final).hostname
            r[nome] = (host == 'lectnex.com.br', f'termina em {host}')
        except Exception as ex:
            r[nome] = (False, erro_legivel(ex))

    if html:
        faltando = []
        for pat in (r'assets/lectnex-core\.js[^"\']*', r'assets/tailwind\.css[^"\']*', r'assets/lectnex\.css[^"\']*'):
            m = re.search(pat, html)
            if not m:
                continue
            try:
                st, _, b = get(SITE + m.group(0))
                if st != 200 or len(b) < 500:
                    faltando.append(m.group(0).split('?')[0])
            except Exception:
                faltando.append(m.group(0).split('?')[0])
        r['Arquivos do site (CSS/JS)'] = (not faltando, 'ok' if not faltando else 'falhou: ' + ', '.join(faltando))

    def dados(arq):
        _, _, b = get(SITE + 'data/' + arq)
        return json.loads(b)

    hoje = AGORA.date().isoformat()
    try:
        cal = dados('calendario.json')
        h = idade_h(cal['atualizado_em'])
        r['Calendário econômico'] = (h < 28, f'atualizado há {h:.0f} h')
        feriado = any(e.get('data') == hoje and 'B3 fechada' in (e.get('evento') or '') for e in cal.get('eventos', []))
    except Exception as ex:
        r['Calendário econômico'] = (False, erro_legivel(ex))
        feriado = False

    pregao = AGORA.weekday() < 5 and not feriado
    minutos = AGORA.hour * 60 + AGORA.minute
    try:
        cot = dados('cotacoes.json')
        h = idade_h(cot['atualizado_em'])
        if pregao and 10 * 60 + 45 <= minutos <= 18 * 60 + 45:
            r['Cotações das ações'] = (h < 1.5, f'atualizadas há {h * 60:.0f} min')
        else:
            r['Cotações das ações'] = (None, 'fora do pregão')
    except Exception as ex:
        r['Cotações das ações'] = (False, erro_legivel(ex))

    try:
        lei = dados('leitura.json')
        if minutos >= 9 * 60:
            r['Leitura do Dia'] = (lei.get('data') == hoje, f"edição de {lei.get('data')}")
        else:
            r['Leitura do Dia'] = (None, 'ainda não é 9h')
    except Exception as ex:
        r['Leitura do Dia'] = (False, erro_legivel(ex))

    try:
        cur = dados('curva.json')
        h = idade_h(cur['atualizado_em'])
        r['Curva de juros'] = (h < 96, f'atualizada há {h / 24:.1f} dias')
    except Exception as ex:
        r['Curva de juros'] = (False, erro_legivel(ex))
    return r


def telegram(texto):
    if not (TOKEN and CHAT):
        return False
    if CHAT.startswith('@'):
        print('::error::TELEGRAM_ADMIN_CHAT_ID deve ser o seu chat privado (número), não um canal público.')
        return False
    req = urllib.request.Request(
        f'https://api.telegram.org/bot{TOKEN}/sendMessage',
        data=json.dumps({'chat_id': CHAT, 'text': texto, 'parse_mode': 'HTML', 'disable_web_page_preview': True}).encode(),
        headers={'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(req, timeout=20).read()
        return True
    except urllib.error.HTTPError as ex:
        print(f'::warning::Telegram respondeu HTTP {ex.code} (abra o bot no Telegram e toque em Iniciar).')
    except Exception as ex:
        print(f'::warning::Telegram indisponível: {ex.__class__.__name__}')
    return False


def main():
    if TESTE:
        ok = telegram('🩺 <b>Monitor Lectnex</b>\nTeste: os alertas do site vão chegar aqui, só para você.')
        print('Teste enviado.' if ok else '::error::Não consegui enviar o teste (confira TELEGRAM_ADMIN_CHAT_ID e se você tocou em Iniciar no bot).')
        sys.exit(0 if ok else 1)

    res = checar()
    try:
        antes = json.load(open(ESTADO, encoding='utf-8'))
    except Exception:
        antes = {}
    falhas_antes = set(antes.get('falhas', []))
    falhas = {k for k, (ok, _) in res.items() if ok is False}
    novas, voltaram = falhas - falhas_antes, falhas_antes - falhas
    ultimo = antes.get('ultimo_alerta')
    lembrar = bool(falhas) and not novas and (not ultimo or idade_h(ultimo) >= 6)

    linhas = []
    for k, (ok, det) in res.items():
        icone = '✅' if ok else ('⚪' if ok is None else '❌')
        linhas.append(f'{icone} {k}: {det}')
    print('\n'.join(linhas))
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as f:
            f.write(f"### Monitor lectnex.com.br · {AGORA:%d/%m %H:%M} (Brasília)\n\n" + '\n'.join(f'- {l}' for l in linhas) + '\n')

    enviado, entregue = None, False
    if novas or voltaram or lembrar:
        partes = []
        if novas or lembrar:
            partes.append('🚨 <b>Algo quebrou no lectnex.com.br</b>' if novas else '⏰ <b>Ainda com problema no lectnex.com.br</b>')
            partes += [f'❌ {k}: {res[k][1]}' for k in sorted(falhas)]
        if voltaram:
            partes.append('✅ <b>Voltou ao normal</b>')
            partes += [f'✅ {k}' for k in sorted(voltaram)]
        partes.append(f'\n<i>{AGORA:%d/%m %H:%M} (Brasília)</i> · {SITE}')
        entregue = telegram('\n'.join(partes))
        if novas or lembrar:
            enviado = AGORA.isoformat(timespec='minutes')

    os.makedirs(os.path.dirname(ESTADO), exist_ok=True)
    json.dump({'falhas': sorted(falhas), 'ultimo_alerta': enviado or (ultimo if falhas else None), 'em': AGORA.isoformat(timespec='minutes')},
              open(ESTADO, 'w', encoding='utf-8'), ensure_ascii=False)

    if not CHAT:
        print('::warning::Sem TELEGRAM_ADMIN_CHAT_ID: os alertas não chegam no Telegram (veja o passo a passo no topo de coletor/monitor.py).')
    for k in sorted(falhas):
        print(f'::error::{k}: {res[k][1]}')
    # Job vermelho (o GitHub avisa por e-mail) só quando há alerta novo/lembrete que não chegou no Telegram.
    if (novas or lembrar) and not entregue:
        sys.exit(1)


if __name__ == '__main__':
    main()
