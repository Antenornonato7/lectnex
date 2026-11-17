"""Modelo de e-mail da Lectnex (Leitura do Dia e Resumo da semana) em HTML de e-mail: tabelas e estilos inline, que funcionam no
Gmail, Outlook e Apple Mail, claro ou escuro. Vai para o Buttondown com o marcador "fancy" (corpo tratado como HTML, dentro do
modelo do Buttondown, que já põe o link de descadastro).
"""
import html

NAVY, TEAL, TEAL_D, ORANGE, VERDE, VERM, CINZA, LINHA, FUNDO = '#0C1A2A', '#009988', '#00756C', '#F39200', '#059669', '#E11D48', '#64748B', '#E2E8F0', '#F4F6F9'
SITE = 'https://lectnex.com.br/'
FONTE = "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;"
MONO = "font-family:'SFMono-Regular',Menlo,Consolas,'Liberation Mono',monospace;"
MARCA = '<!-- buttondown-editor-mode: fancy -->'
e = lambda s: html.escape(str(s or ''), quote=True)


def documento(titulo, pre, blocos, utm='email'):
    """Corpo completo: faixa da marca, título, blocos e rodapé."""
    pre_html = f'<div style="display:none;max-height:0;overflow:hidden;opacity:0">{e(pre)}</div>' if pre else ''
    return MARCA + f'''
{pre_html}<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:640px;margin:0 auto;{FONTE}color:{NAVY}">
<tr><td style="background:{NAVY};padding:18px 22px;border-left:4px solid {ORANGE}">
  <a href="{SITE}?utm_source=newsletter&amp;utm_medium={utm}" style="text-decoration:none;font-size:22px;font-weight:800;color:#FFFFFF;{FONTE}">Lect<span style="color:#00B4A2">nex</span></a>
  <div style="{MONO}font-size:11px;letter-spacing:1.5px;color:#94A3B8;margin-top:2px">EDUCAÇÃO CONECTADA AO MERCADO</div>
</td></tr>
<tr><td style="padding:22px 22px 6px"><h1 style="margin:0;font-size:24px;line-height:1.25;font-weight:800;color:{NAVY};{FONTE}">{e(titulo)}</h1></td></tr>
{''.join(f'<tr><td style="padding:10px 22px">{b}</td></tr>' for b in blocos if b)}
<tr><td style="padding:22px;border-top:1px solid {LINHA}">
  <p style="margin:0;font-size:12px;line-height:1.5;color:{CINZA}">Conteúdo educacional, gerado com apoio de IA a partir de fontes públicas. Não é recomendação de investimento.</p>
  <p style="margin:8px 0 0;font-size:12px;color:{CINZA}"><a href="{SITE}" style="color:{TEAL_D}">lectnex.com.br</a> · <a href="https://discord.gg/kM6YcQA82P" style="color:{TEAL_D}">Discord</a> · <a href="https://t.me/lectnex" style="color:{TEAL_D}">Telegram</a> · <a href="https://www.instagram.com/lectnex.oficial/" style="color:{TEAL_D}">Instagram</a></p>
</td></tr>
</table>'''


def rotulo(t, cor=TEAL_D):
    return f'<div style="{MONO}font-size:11px;font-weight:700;letter-spacing:1.5px;color:{cor};text-transform:uppercase;margin:6px 0 8px">{e(t)}</div>'


def secao(titulo, conteudo, cor=TEAL_D):
    return rotulo(titulo, cor) + conteudo


def paragrafo(t, tam=15, cor=NAVY):
    return f'<p style="margin:0 0 10px;font-size:{tam}px;line-height:1.55;color:{cor}">{t}</p>'


def lista(itens):
    return ''.join(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 10px"><tr>'
                   f'<td width="14" valign="top" style="padding-top:8px"><div style="width:6px;height:6px;background:{TEAL}"></div></td>'
                   f'<td style="font-size:15px;line-height:1.55;color:{NAVY}">{i}</td></tr></table>' for i in itens)


def numeros(cards):
    """cards: [(rótulo, valor, variação_texto, cor_da_variação)] em até 3 colunas."""
    tds = ''.join(f'<td width="{100 // len(cards)}%" valign="top" style="padding:4px"><div style="border:1px solid {LINHA};background:{FUNDO};padding:12px">'
                  f'<div style="{MONO}font-size:10px;letter-spacing:1px;color:{CINZA}">{e(r)}</div>'
                  f'<div style="{MONO}font-size:20px;font-weight:700;color:{NAVY};margin-top:4px">{e(v)}</div>'
                  f'<div style="{MONO}font-size:13px;font-weight:700;color:{c}">{e(x)}</div></div></td>' for r, v, x, c in cards)
    return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>{tds}</tr></table>'


def vies(nome, leitura, motivo):
    cor, txt = {'bullish': (VERDE, '▲ VIÉS DE ALTA'), 'bearish': (VERM, '▼ VIÉS DE BAIXA')}.get(leitura, (CINZA, '● NEUTRO'))
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 8px;border:1px solid {LINHA}"><tr>'
            f'<td width="112" valign="top" style="padding:10px;background:{FUNDO};border-right:3px solid {cor}"><div style="{MONO}font-size:12px;font-weight:700;color:{NAVY}">{e(nome)}</div>'
            f'<div style="{MONO}font-size:11px;font-weight:700;color:{cor};margin-top:3px">{txt}</div></td>'
            f'<td valign="top" style="padding:10px;font-size:14px;line-height:1.5;color:{NAVY}">{e(motivo)}</td></tr></table>')


def botao(texto, url, cor=ORANGE, cor_txt=NAVY):
    return (f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:6px 0"><tr><td style="background:{cor}">'
            f'<a href="{e(url)}" style="display:inline-block;padding:12px 20px;{MONO}font-size:13px;font-weight:700;color:{cor_txt};text-decoration:none">{e(texto)}</a></td></tr></table>')


def destaque(conteudo, cor=TEAL):
    return f'<div style="background:{NAVY};border-left:4px solid {cor};padding:16px;color:#FFFFFF">{conteudo}</div>'


def var(v):
    """Variação em % com sinal e cor."""
    if v is None:
        return '—', CINZA
    return ('+' if v > 0 else '−' if v < 0 else '') + f'{abs(v):.2f}%'.replace('.', ','), (VERDE if v > 0 else VERM if v < 0 else CINZA)
