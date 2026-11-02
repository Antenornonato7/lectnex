"""Monta e envia a Leitura do Dia por e-mail via Buttondown (API versão 2026-04-01).

Roda no workflow "Newsletter" quando data/leitura.json muda. Só envia quando a edição é de um dia
diferente da versão anterior do arquivo (correções no mesmo dia não reenviam), a não ser em disparo manual.
Requer o segredo BUTTONDOWN_API_KEY. Só biblioteca padrão.
"""
import json, os, subprocess, sys, urllib.request

KEY = os.environ.get('BUTTONDOWN_API_KEY', '').strip()
SITE = 'https://lectnex.com.br/'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def anterior():
    try:
        return json.loads(subprocess.check_output(['git', 'show', 'HEAD~1:data/leitura.json'], cwd=ROOT, stderr=subprocess.DEVNULL))
    except Exception:
        return {}


def corpo(d):
    TH = {'bullish': '🟢 comprador', 'neutro': '⚪ neutro', 'bearish': '🔴 vendedor'}
    imp = {'alta': '▲', 'baixa': '▼', 'neutro': '●'}
    L = []
    if d.get('tipo') == 'sem-pregao':
        pp = d.get('proximo_pregao') or {}
        dt = pp.get('data', '')
        if len(dt) == 10:
            dt = f'{dt[8:]}/{dt[5:7]}'
        L += ['**Edição sem pregão** · próximo pregão: ' + dt, '', pp.get('o_que_esperar', ''), '']
    else:
        t = d.get('termometro') or {}
        L += ['**Termômetro do dia**', '']
        for k, nome in (('win', 'WIN (mini índice)'), ('wdo', 'WDO (mini dólar)')):
            if t.get(k):
                L.append(f"- **{nome}:** {TH.get(t[k].get('leitura'), t[k].get('leitura', ''))} — {t[k].get('motivo', '')}")
        L.append('')
    L += ['**O que importa**', ''] + [f'- {x}' for x in d.get('resumo', [])] + ['']
    if d.get('destaques'):
        L += ['**Agenda**', ''] + [f"- **{x.get('hora', '')}** · {x.get('evento', '')} — {x.get('por_que', '')}" for x in d['destaques']] + ['']
    if d.get('noticias'):
        L += ['**Notícias que importam**', '']
        for n in d['noticias']:
            tags = ' '.join(f"{k.upper()} {imp.get(v, '')}" for k, v in (n.get('impacto') or {}).items())
            tit = f"[{n.get('titulo', '')}]({n['url']})" if n.get('url') else n.get('titulo', '')
            L.append(f"- {tit} ({n.get('fonte', '')}){' · ' + tags if tags else ''}  \n  {n.get('por_que', '')}")
        L.append('')
    L += [f'[Abrir o Lectnex Terminal]({SITE}) · mapa de calor, placar de vencimento, Plano do Dia e mais.', '',
          '_Conteúdo educacional gerado com apoio de IA a partir de fontes públicas. Não é recomendação de investimento._']
    return '\n'.join(L)


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
