"""Lembrete de postagem no Telegram PRIVADO do dono, na hora de postar (pelo Relógio).
Momentos: manha (8h30, pregão), noite (20h, pregão), fds (10h05, sábado, domingo e feriado), domingo (18h, domingo e feriado).
Segue o mesmo padrão do roteiro: Termo e reel do dia às segundas e quartas, gráfico do dia às terças e quintas,
reel da semana e placar no último pregão da semana, Antes do dado quando houver evento forte.
Uso: python3 scripts/lembrete.py manha|noite|fds|domingo [AAAA-MM-DD]
"""
import datetime as dt
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from ultimo_pregao import pregao, ultimo_da_semana  # noqa: E402

BRT = dt.timezone(dt.timedelta(hours=-3))
ROTEIRO = ('2026-11-23', 'https://claude.ai/artifact/Adh5fxQJ9HpEPCW1qgmQkp')


def itens(momento, d):
    seg_qua, ter_qui = d.weekday() in (0, 2), d.weekday() in (1, 3)
    out = []
    if momento == 'manha':
        out.append('Story da <b>Leitura do Dia</b> (mensagem das ~7h50, com o link do sticker)')
        try:
            a = json.load(open('data/antes.json', encoding='utf-8'))
            if a.get('data') == d.isoformat() and not a.get('vazio'):
                out.append(f'Story <b>Antes do dado</b> ({a.get("curto") or a.get("evento")}, mensagem das 7h20)')
        except Exception:
            pass
        if seg_qua:
            out.append('Story do <b>Termo do dia</b> (mensagem das 8h05)')
    elif momento == 'noite':
        out.append('Story do <b>fechamento</b> (no Kit do dia)')
        if ultimo_da_semana(d):
            out += ['<b>Reel da semana</b> (no Kit: vídeo, capa e legenda)', 'Story do <b>placar da semana</b> (sticker com lectnex.com.br/placar)']
        elif seg_qua:
            out.append('<b>Reel do dia</b> (no Kit: vídeo, capa e legenda com pergunta)')
        elif ter_qui:
            out.append('Post do <b>gráfico do dia</b> no feed (no Kit: imagem e legenda)')
    elif momento == 'fds':
        if d.weekday() == 5:
            out += ['<b>Carrossel da semana</b> no feed (chegou às 9h47)', 'Compartilhar o carrossel nos seus stories']
        else:
            out.append('Story da <b>Leitura</b> de ' + ('domingo' if d.weekday() == 6 else 'feriado') + ' (o que esperar do próximo pregão)')
    elif momento == 'domingo':
        out.append('Repostar nos stories o <b>reel mais visto da semana</b> ("Viu esse?")')
        if d.weekday() == 6:
            out.append('Anotar os números da semana no painel de desempenho: https://claude.ai/artifact/4hS34kNEt73oUn6z999hyW')
    return out


def main():
    momento = sys.argv[1] if len(sys.argv) > 1 else 'manha'
    d = dt.date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else dt.datetime.now(BRT).date()
    if momento in ('manha', 'noite') and not pregao(d):
        print('Sem pregão hoje: lembrete de pregão não enviado.')
        return
    lst = itens(momento, d)
    if not lst:
        print('Nada a postar agora.')
        return
    tit = {'manha': 'manhã', 'noite': 'noite', 'fds': 'hoje', 'domingo': 'fim de tarde'}[momento]
    msg = f'⏰ <b>Hora de postar ({tit})</b>\n' + '\n'.join(f'{i}. {x}' for i, x in enumerate(lst, 1))
    if d.isoformat() <= ROTEIRO[0]:
        msg += f'\n\nMarque no roteiro: {ROTEIRO[1]}'
    print(msg)
    tok, chat = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip(), os.environ.get('TELEGRAM_ADMIN_CHAT_ID', '').strip()
    if tok and chat and not chat.startswith('@'):
        req = urllib.request.Request(f'https://api.telegram.org/bot{tok}/sendMessage', headers={'Content-Type': 'application/json'},
                                     data=json.dumps({'chat_id': chat, 'text': msg, 'parse_mode': 'HTML', 'disable_web_page_preview': True}).encode())
        urllib.request.urlopen(req, timeout=20).read()


if __name__ == '__main__':
    main()
