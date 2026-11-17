"""Stories fixos para os destaques do Instagram (Comece, Educação, Ferramentas, Método): 1080×1920, nas cores da marca, com o
mesmo ícone das capas. Conteúdo educacional e atemporal (não depende do dia).
Uso: python3 scripts/destaques.py pasta_saida   (requer o Phosphor em /tmp/phosphor-web, baixado por scripts/icones.py)
"""
import os
import re
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
from og_leitura import BG, CARD, LINE, MUTED, ORANGE, TEAL_L, WHITE, fonte, quebrar  # noqa: E402

W, H, M = 1080, 1920, 90
PH = os.path.join(tempfile.gettempdir(), 'phosphor-web', 'src', 'fill')
_css = open(os.path.join(PH, 'style.css')).read()
ICONE = lambda n: chr(int(re.search(r'\.ph-fill\.ph-%s:before\s*\{\s*content:\s*"\\([0-9a-f]+)"' % n, _css).group(1), 16))

# destaque → (ícone da capa, [(ícone, título, texto, destaque_em_caixa, rodapé)])
CONTEUDO = {
    'comece': ('rocket-launch', [
        ('hand-waving', 'Bem-vindo à Lectnex', 'Educação conectada ao mercado para quem estuda mini índice e mini dólar.', 'Tudo grátis, sem cadastro.', 'lectnex.com.br'),
        ('envelope-simple', 'Todo dia às 7h40', 'A Leitura do Dia chega no seu e-mail antes da abertura: viés de WIN e WDO, agenda com horários e as notícias que mexem no preço.', 'Inscreva-se no site.', 'lectnex.com.br'),
        ('game-controller', 'Treine sem arriscar', 'O simulador de pregão repete dias reais de WIN e WDO, com as manchetes aparecendo no horário. Dinheiro fictício e treinador no fim.', '56 pregões para treinar.', 'lectnex.com.br/simulador'),
        ('discord-logo', 'Entre na comunidade', 'Desafio diário SUBIU ou CAIU, ranking semanal do simulador e um lugar para tirar dúvidas com quem também estuda o mercado.', 'Grátis no Discord.', 'discord.gg/kM6YcQA82P'),
    ]),
    'educacao': ('graduation-cap', [
        ('chart-line-up', 'O que é o mini índice (WIN)?', 'É o contrato futuro do Ibovespa negociado na B3. Você ganha ou perde conforme os pontos sobem ou caem.', 'Cada ponto vale R$ 0,20. A menor oscilação é de 5 pontos = R$ 1,00 por contrato.', 'lectnex.com.br/glossario'),
        ('currency-dollar', 'O que é o mini dólar (WDO)?', 'É o contrato futuro do dólar comercial na B3, cotado em pontos (reais por mil dólares).', 'Cada ponto vale R$ 10. A menor oscilação é de 0,5 ponto = R$ 5,00 por contrato.', 'lectnex.com.br/glossario'),
        ('scales', 'Ajuste diário', 'Todo fim de pregão, a B3 acerta na sua conta, em dinheiro, o ganho ou a perda das posições que ficaram abertas.', 'Por isso operar futuro exige margem em garantia.', 'lectnex.com.br/glossario'),
        ('calendar-check', 'Quando vence?', 'Contrato futuro tem data para acabar. Perto do vencimento, quem quer continuar troca para o próximo (a rolagem).', 'WIN: meses pares, quarta-feira mais próxima do dia 15. WDO: todo mês, no 1º dia útil.', 'lectnex.com.br'),
    ]),
    'ferramentas': ('calculator', [
        ('calculator', 'Calculadora de risco', 'Antes de entrar: quantos contratos cabem na sua conta, quanto custa o stop em reais e quanto da conta você arrisca.', 'Responde em segundos.', 'lectnex.com.br/futuros.html'),
        ('game-controller', 'Simulador de pregão', 'Opere um dia real em replay, com stop e limite de perda. No fim, o resultado, os erros de risco e os momentos-chave.', 'Funciona até sem internet.', 'lectnex.com.br/simulador'),
        ('receipt', 'IR do day trade', 'No day trade, o imposto é de 20% sobre o lucro do mês, com 1% retido na fonte. O DARF usa o código 6015.', 'A calculadora faz a conta e mostra o prejuízo para compensar.', 'lectnex.com.br'),
        ('newspaper', 'O que mexeu hoje', 'O gráfico do Ibovespa e do dólar com cada manchete marcada no horário em que saiu, e a reação nos 30 minutos seguintes.', 'Atualizado a cada pregão.', 'lectnex.com.br/hoje.html'),
    ]),
    'metodo': ('target', [
        ('clipboard-text', 'Antes do pregão: o plano', 'Quem opera no improviso decide no calor do momento. O plano define antes: eventos do dia, contrato vigente, limite de perda e máximo de operações.', 'Plano do Dia pronto no site.', 'lectnex.com.br/futuros.html'),
        ('shield-check', 'Arrisque pouco por operação', 'Muitos traders limitam a perda de cada operação a 1% da conta.', 'Conta de R$ 5.000 → R$ 50. Stop de 100 pontos no WIN = R$ 20 por contrato → até 2 contratos.', 'lectnex.com.br/futuros.html'),
        ('hand', 'Limite de perda do dia', 'Definir antes quanto pode perder no dia (por exemplo, 2% da conta) evita que um dia ruim vire uma semana ruim.', 'Bateu o limite? Desliga a tela.', 'lectnex.com.br/simulador'),
        ('notebook', 'Anote cada trade', 'Entrada, saída, motivo e o que deu errado. Rever as anotações é o jeito mais barato de parar de repetir o mesmo erro.', 'Diário de trades grátis no site.', 'lectnex.com.br/futuros.html'),
    ]),
}
NOMES = {'comece': 'COMECE', 'educacao': 'EDUCAÇÃO', 'ferramentas': 'FERRAMENTAS', 'metodo': 'MÉTODO'}


def fundo():
    im = Image.new('RGB', (W, H), '#0C1A2A')
    glow = Image.new('L', (W, H), 0)
    ImageDraw.Draw(glow).ellipse([-200, 300, W + 200, 1300], fill=70)
    im.paste(Image.new('RGB', (W, H), '#00756C'), (0, 0), glow.filter(ImageFilter.GaussianBlur(220)))
    d = ImageDraw.Draw(im)
    for x in range(0, W, 60):
        d.line([(x, 0), (x, H)], fill='#0F2133')
    for y in range(0, H, 60):
        d.line([(0, y), (W, y)], fill='#0F2133')
    return im, d


def caber(d, txt, nome, tam, larg, linhas):
    while tam > 30:
        f = fonte(nome, tam)
        ls = quebrar(d, txt, f, larg, 20)
        if len(ls) <= linhas:
            return f, ls
        tam -= 2
    f = fonte(nome, 30)
    return f, quebrar(d, txt, f, larg, linhas)


def story(chave, n, total, ic, tit, txt, caixa, rodape, saida):
    im, d = fundo()
    d.rectangle([0, 0, W, 12], fill=ORANGE)
    # barra de progresso do destaque (mostra que tem mais)
    bw = (W - 2 * M - (total - 1) * 12) / total
    for k in range(total):
        x = M + k * (bw + 12)
        d.rectangle([x, 250, x + bw, 258], fill=TEAL_L if k <= n else LINE)
    fl = fonte('JetBrainsMono-Bold.ttf', 30)
    d.text((M, 290), f'{NOMES[chave]} · {n + 1}/{total}', font=fl, fill=TEAL_L)
    fb = fonte('InterDisplay-Bold.otf', 40)
    marca = 'Lectnex'
    d.text((W - M - d.textlength(marca, font=fb), 282), 'Lect', font=fb, fill=WHITE)
    d.text((W - M - d.textlength('nex', font=fb), 282), 'nex', font=fb, fill=TEAL_L)
    # ícone
    cx, cy, r = M + 110, 520, 110
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill='#0F2236', outline=TEAL_L, width=8)
    fi = ImageFont.truetype(os.path.join(PH, 'Phosphor-Fill.ttf'), 120)
    ch = ICONE(ic)
    b = d.textbbox((0, 0), ch, font=fi)
    d.text((cx - (b[2] - b[0]) / 2 - b[0], cy - (b[3] - b[1]) / 2 - b[1]), ch, font=fi, fill=WHITE)
    d.ellipse([cx + 62, cy - 98, cx + 96, cy - 64], fill=ORANGE)
    # título e texto
    ft, lt = caber(d, tit, 'InterDisplay-Bold.otf', 108, W - 2 * M, 3)
    y = 690
    for l in lt:
        d.text((M, y), l, font=ft, fill=WHITE); y += int(ft.size * 1.12)
    y += 30
    fx, lx = caber(d, txt, 'Inter-Medium.otf', 56, W - 2 * M, 7)
    for l in lx:
        d.text((M, y), l, font=fx, fill='#CBD5E1'); y += int(fx.size * 1.38)
    if caixa:
        y += 40
        fc, lc = caber(d, caixa, 'InterDisplay-Bold.otf', 56, W - 2 * M - 80, 4)
        alt = len(lc) * int(fc.size * 1.3) + 70
        d.rectangle([M, y, W - M, y + alt], fill=CARD, outline=ORANGE, width=4)
        d.rectangle([M, y, M + 12, y + alt], fill=ORANGE)
        yy = y + 35
        for l in lc:
            d.text((M + 45, yy), l, font=fc, fill=WHITE); yy += int(fc.size * 1.3)
    # rodapé (story não tem link clicável: o endereço fica escrito)
    fr = fonte('JetBrainsMono-Bold.ttf', 40 if len(rodape) <= 26 else 32)
    d.rectangle([M, 1580, W - M, 1680], fill=TEAL_L)
    d.text(((W - d.textlength(rodape, font=fr)) / 2, 1630 - fr.size / 2 - 4), rodape, font=fr, fill='#060D17')
    nota = 'conteúdo educacional · não é recomendação'
    fn = fonte('JetBrainsMono-Bold.ttf', 24)
    d.text(((W - d.textlength(nota, font=fn)) / 2, 1710), nota, font=fn, fill=MUTED)
    im.save(saida, quality=92)


if __name__ == '__main__':
    pasta = sys.argv[1] if len(sys.argv) > 1 else '.'
    os.makedirs(pasta, exist_ok=True)
    for chave, (_, slides) in CONTEUDO.items():
        for n, s in enumerate(slides):
            story(chave, n, len(slides), *s, os.path.join(pasta, f'{chave}-{n + 1}.jpg'))
    print('ok')
