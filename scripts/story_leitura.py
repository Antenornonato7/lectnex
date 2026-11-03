"""Story da Leitura do Dia (1080×1920) para Instagram, enviado no Telegram PRIVADO do dono.

Título, termômetro WIN/WDO (ou próximo pregão) e 3 destaques da agenda, no visual da marca.
Áreas de segurança do Instagram respeitadas (topo e base livres) e espaço tracejado para o sticker de link.
Uso: python3 scripts/story_leitura.py [data/leitura.json] [saida.png]
Com TELEGRAM_BOT_TOKEN e TELEGRAM_ADMIN_CHAT_ID no ambiente, envia a imagem (como foto e como arquivo, sem compressão).
"""
import datetime as dt
import json
import os
import sys
import urllib.request
import uuid

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
from og_leitura import BG, CARD, DIAS, LINE, MUTED, ORANGE, TEAL_L, TERM, WHITE, fonte, quebrar  # noqa: E402

W, H, M = 1080, 1920, 84


def tracejado(dr, caixa, cor, traco=18, vao=12, w=3):
    x0, y0, x1, y1 = caixa
    for x in range(x0, x1, traco + vao):
        dr.line([(x, y0), (min(x + traco, x1), y0)], fill=cor, width=w)
        dr.line([(x, y1), (min(x + traco, x1), y1)], fill=cor, width=w)
    for y in range(y0, y1, traco + vao):
        dr.line([(x0, y), (x0, min(y + traco, y1))], fill=cor, width=w)
        dr.line([(x1, y), (x1, min(y + traco, y1))], fill=cor, width=w)


def gerar(d, saida):
    im = Image.new('RGB', (W, H), BG)
    dr = ImageDraw.Draw(im)
    for x in range(0, W, 48):
        dr.line([(x, 0), (x, H)], fill='#0A1422')
    for y in range(0, H, 48):
        dr.line([(0, y), (W, y)], fill='#0A1422')
    dr.rectangle([0, 0, 14, H], fill=ORANGE)

    # marca (abaixo da faixa de 250 px que o Instagram cobre)
    y = 250
    try:
        logo = Image.open('assets/brand/icon-192.png').convert('RGBA').resize((76, 76))
        im.paste(logo, (M, y), logo)
    except Exception:
        pass
    fb = fonte('InterDisplay-Bold.otf', 50)
    dr.text((M + 96, y + 8), 'Lect', font=fb, fill=WHITE)
    dr.text((M + 96 + dr.textlength('Lect', font=fb), y + 8), 'nex', font=fb, fill=TEAL_L)

    dia = dt.date.fromisoformat(d['data'])
    y += 130
    dr.text((M, y), f'LEITURA DO DIA · {DIAS[dia.weekday()]} {dia:%d/%m}', font=fonte('JetBrainsMono-Bold.ttf', 32), fill=ORANGE)

    y += 64
    ft = fonte('InterDisplay-Bold.otf', 76)
    for linha in quebrar(dr, d.get('titulo', ''), ft, W - 2 * M, 4):
        dr.text((M, y), linha, font=ft, fill=WHITE)
        y += 92

    # termômetro ou próximo pregão
    y += 40
    fl, fv, fm = fonte('JetBrainsMono-Bold.ttf', 26), fonte('JetBrainsMono-Bold.ttf', 40), fonte('Inter-Medium.otf', 28)
    t = d.get('termometro')
    if t:
        for k, nome in (('win', 'WIN · mini índice'), ('wdo', 'WDO · mini dólar')):
            if k not in t:
                continue
            txt, cor = TERM.get(t[k].get('leitura'), TERM['neutro'])
            motivo = quebrar(dr, t[k].get('motivo', ''), fm, W - 2 * M - 64, 2)
            alt = 150 + 38 * len(motivo)
            dr.rectangle([M, y, W - M, y + alt], fill=CARD, outline=LINE, width=2)
            dr.rectangle([M, y, M + 8, y + alt], fill=cor)
            dr.text((M + 36, y + 26), nome.upper(), font=fl, fill=MUTED)
            dr.text((M + 36, y + 64), txt, font=fv, fill=cor)
            yy = y + 124
            for linha in motivo:
                dr.text((M + 36, yy), linha, font=fm, fill='#CBD5E1')
                yy += 38
            y += alt + 24
    elif d.get('proximo_pregao'):
        p = d['proximo_pregao']
        pd = dt.date.fromisoformat(p['data'])
        esperar = quebrar(dr, p.get('o_que_esperar', ''), fm, W - 2 * M - 64, 3)
        alt = 150 + 38 * len(esperar)
        dr.rectangle([M, y, W - M, y + alt], fill=CARD, outline=LINE, width=2)
        dr.rectangle([M, y, M + 8, y + alt], fill=ORANGE)
        dr.text((M + 36, y + 26), 'SEM PREGÃO HOJE', font=fl, fill=MUTED)
        dr.text((M + 36, y + 64), f'Próximo: {DIAS[pd.weekday()].lower()} {pd:%d/%m}', font=fv, fill=WHITE)
        yy = y + 124
        for linha in esperar:
            dr.text((M + 36, yy), linha, font=fm, fill='#CBD5E1')
            yy += 38
        y += alt + 24

    # agenda (até 3 itens, enquanto couber acima da área do sticker)
    limite = 1440
    dest = [x for x in d.get('destaques', []) if x.get('evento')][:3]
    if dest and y + 120 < limite:
        y += 16
        dr.text((M, y), 'NA AGENDA', font=fl, fill=TEAL_L)
        y += 50
        fh, fe = fonte('JetBrainsMono-Bold.ttf', 30), fonte('Inter-Medium.otf', 34)
        for x in dest:
            linhas = quebrar(dr, x['evento'], fe, W - 2 * M - 190, 2)
            if y + 46 * len(linhas) > limite:
                break
            dr.text((M, y + 2), (x.get('hora') or '').strip()[:9], font=fh, fill=TEAL_L)
            for linha in linhas:
                dr.text((M + 190, y), linha, font=fe, fill=WHITE)
                y += 46
            y += 18

    # espaço para o sticker de link (o Instagram não deixa colocar link pela imagem)
    caixa = (M, 1480, W - M, 1630)
    tracejado(dr, caixa, '#334155')
    fs = fonte('JetBrainsMono-Bold.ttf', 26)
    s = 'COLOQUE AQUI O STICKER DE LINK'
    dr.text(((W - dr.textlength(s, font=fs)) / 2, 1540), s, font=fs, fill='#475569')

    fr = fonte('Inter-Medium.otf', 28)
    r = 'Leitura completa em lectnex.com.br · conteúdo educacional'
    dr.text(((W - dr.textlength(r, font=fr)) / 2, 1660), r, font=fr, fill=MUTED)

    os.makedirs(os.path.dirname(os.path.abspath(saida)), exist_ok=True)
    im.save(saida, 'PNG', optimize=True)
    return saida


def enviar(caminho, legenda):
    token = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
    chat = os.environ.get('TELEGRAM_ADMIN_CHAT_ID', '').strip()
    if not token or not chat or chat.startswith('@'):
        print('::warning::Sem TELEGRAM_ADMIN_CHAT_ID (chat privado): story gerado, mas não enviado.')
        return False
    dados = open(caminho, 'rb').read()
    for metodo, campo in (('sendPhoto', 'photo'), ('sendDocument', 'document')):
        b = uuid.uuid4().hex
        partes = [(k, v) for k, v in (('chat_id', chat), ('caption', legenda if metodo == 'sendPhoto' else 'Mesma imagem em qualidade original (sem compressão).'), ('parse_mode', 'HTML'))]
        corpo = b''.join(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in partes)
        corpo += f'--{b}\r\nContent-Disposition: form-data; name="{campo}"; filename="lectnex-story.png"\r\nContent-Type: image/png\r\n\r\n'.encode() + dados + f'\r\n--{b}--\r\n'.encode()
        req = urllib.request.Request(f'https://api.telegram.org/bot{token}/{metodo}', data=corpo,
                                     headers={'Content-Type': f'multipart/form-data; boundary={b}'})
        urllib.request.urlopen(req, timeout=60).read()
    print('Story enviado no Telegram privado.')
    return True


def main():
    entrada = sys.argv[1] if len(sys.argv) > 1 else 'data/leitura.json'
    saida = sys.argv[2] if len(sys.argv) > 2 else 'story-leitura.png'
    d = json.load(open(entrada, encoding='utf-8'))
    gerar(d, saida)
    dia = dt.date.fromisoformat(d['data'])
    legenda = (f'📲 <b>Story de hoje pronto</b> · {DIAS[dia.weekday()].lower()} {dia:%d/%m}\n'
               f'{d.get("titulo", "")}\n\n'
               'No Instagram: poste a imagem, adicione o <b>sticker de link</b> na área tracejada com '
               '<code>lectnex.com.br/comece.html</code> e escreva "Leitura do Dia" no sticker.')
    enviar(saida, legenda)


if __name__ == '__main__':
    main()
