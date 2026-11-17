"""Monta e envia a Leitura do Dia por e-mail via Buttondown (API versão 2026-04-01).

Roda no workflow "Newsletter" quando data/leitura.json muda. Só envia quando a edição é de um dia
diferente da versão anterior do arquivo (correções no mesmo dia não reenviam), a não ser em disparo manual.
Requer o segredo BUTTONDOWN_API_KEY. Só biblioteca padrão.
"""
import json, os, subprocess, sys, urllib.error, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

KEY = os.environ.get('BUTTONDOWN_API_KEY', '').strip()
SITE = 'https://lectnex.com.br/'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def anterior():
    try:
        return json.loads(subprocess.check_output(['git', 'show', 'HEAD~1:data/leitura.json'], cwd=ROOT, stderr=subprocess.DEVNULL))
    except Exception:
        return {}


def corpo(d):
    """Leitura do Dia em HTML de e-mail (modelo da marca em email_html.py)."""
    import email_html as H
    imp = {'alta': ('▲', H.VERDE), 'baixa': ('▼', H.VERM), 'neutro': ('●', H.CINZA)}
    blocos = []
    if d.get('tipo') == 'sem-pregao':
        pp = d.get('proximo_pregao') or {}
        dt = pp.get('data', '')
        dt = f'{dt[8:]}/{dt[5:7]}' if len(dt) == 10 else dt
        blocos.append(H.secao(f'Edição sem pregão · próximo pregão {dt}', H.paragrafo(H.e(pp.get('o_que_esperar', '')))))
    else:
        t = d.get('termometro') or {}
        vs = ''.join(H.vies(nome, t[k].get('leitura'), t[k].get('motivo', '')) for k, nome in (('win', 'WIN · mini índice'), ('wdo', 'WDO · mini dólar')) if t.get(k))
        if vs:
            blocos.append(H.secao('Viés do modelo na abertura (experimental)', vs))
    if d.get('resumo'):
        blocos.append(H.secao('O que importa hoje', H.lista([H.e(x) for x in d['resumo']])))
    if d.get('destaques'):
        linhas = ''.join(f'<tr><td width="64" valign="top" style="padding:8px 8px 8px 0;border-bottom:1px solid {H.LINHA};{H.MONO}font-size:13px;font-weight:700;color:{H.ORANGE}">{H.e(x.get("hora", ""))}</td>'
                         f'<td style="padding:8px 0;border-bottom:1px solid {H.LINHA};font-size:14px;line-height:1.5"><strong>{H.e(x.get("evento", ""))}</strong><br><span style="color:{H.CINZA}">{H.e(x.get("por_que", ""))}</span></td></tr>'
                         for x in d['destaques'])
        blocos.append(H.secao('Agenda do dia', f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{linhas}</table>', H.ORANGE))
    if d.get('noticias'):
        itens = []
        for n in d['noticias']:
            tags = ' '.join(f'<span style="{H.MONO}font-size:11px;font-weight:700;color:{imp.get(v, ("", H.CINZA))[1]};border:1px solid {imp.get(v, ("", H.CINZA))[1]};padding:1px 5px">{k.upper()} {imp.get(v, ("", ""))[0]}</span>'
                            for k, v in (n.get('impacto') or {}).items())
            tit = f'<a href="{H.e(n["url"])}" style="color:{H.NAVY};font-weight:700;text-decoration:underline">{H.e(n.get("titulo", ""))}</a>' if n.get('url') else f'<strong>{H.e(n.get("titulo", ""))}</strong>'
            itens.append(f'{tit} <span style="color:{H.CINZA};font-size:13px">({H.e(n.get("fonte", ""))})</span> {tags}<br><span style="color:{H.CINZA};font-size:14px">{H.e(n.get("por_que", ""))}</span>')
        blocos.append(H.secao('Notícias que importam', H.lista(itens)))
    blocos.append(H.botao('ABRIR O TERMINAL LECTNEX →', SITE + '?utm_source=newsletter&utm_medium=email'))
    blocos.append(H.destaque(
        f'<div style="{H.MONO}font-size:11px;letter-spacing:1.5px;color:#00B4A2;font-weight:700">SIMULADOR DE PREGÃO · GRÁTIS</div>'
        f'<div style="font-size:17px;font-weight:800;margin:6px 0">Treine um dia real de WIN ou WDO</div>'
        f'<div style="font-size:14px;color:#CBD5E1;line-height:1.5">Replay com as manchetes no horário, dinheiro fictício e treinador no fim. Ranking toda semana no Discord.</div>'
        + H.botao('JOGAR AGORA', SITE + 'simulador.html?utm_source=newsletter&utm_medium=email', H.TEAL, '#FFFFFF')))
    blocos.append(H.paragrafo(f'👑 A Lectnex Pro está em construção. <a href="{SITE}pro.html?utm_source=newsletter&amp;utm_medium=email" style="color:{H.TEAL_D};font-weight:700">Entre na lista de fundadores (grátis)</a> e vote no que vem primeiro.', 14))
    return H.documento(d.get('titulo', 'Leitura do Dia'), (d.get('resumo') or [''])[0][:140], blocos)


def main():
    if not KEY:
        print('::warning title=Newsletter::Sem o segredo BUTTONDOWN_API_KEY — nada foi enviado.'); return
    d = json.load(open(os.path.join(ROOT, 'data', 'leitura.json'), encoding='utf-8'))
    if not os.environ.get('MANUAL') and anterior().get('data') == d.get('data'):
        print('::notice title=Newsletter::Mesma edição do dia (correção) — não reenviado.'); return
    def post(status):
        payload = {'subject': f"Leitura do Dia · {d.get('titulo', '')}", 'body': corpo(d), 'status': status}
        req = urllib.request.Request('https://api.buttondown.com/v1/emails', data=json.dumps(payload).encode(), method='POST', headers={
            'Authorization': f'Token {KEY}', 'Content-Type': 'application/json', 'X-API-Version': '2026-04-01',
            'X-Buttondown-Live-Dangerously': 'true'})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    if os.environ.get('RASCUNHO'):
        st = post('draft')
        print(f"::notice title=Newsletter em rascunho::Prévia criada no Buttondown (HTTP {st}): confira em Emails → Drafts."); return
    try:
        st = post('about_to_send')
        print(f"::notice title=Newsletter enviada::{d.get('data')} · {d.get('titulo', '')} (HTTP {st})")
    except urllib.error.HTTPError as e:
        msg = e.read().decode()[:400]
        if e.code == 403:
            # Sem permissão de envio (chave sem 'Emails: Write' ou conta ainda não liberada): deixa como rascunho para envio manual
            try:
                st = post('draft')
                print(f"::warning title=Newsletter em rascunho::Envio recusado ({msg}). Rascunho criado no Buttondown (HTTP {st}) — envie pelo painel.")
                return
            except urllib.error.HTTPError as e2:
                print(f'::error title=Buttondown rascunho {e2.code}::{e2.read().decode()[:400]}')
        print(f'::error title=Buttondown {e.code}::{msg}'); sys.exit(1)


if __name__ == '__main__':
    main()
