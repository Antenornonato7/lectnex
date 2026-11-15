"""Eventos do servidor Discord para os dados que mais mexem no mercado (Copom, payroll, IPCA, ata do FOMC…).

Lê data/calendario.json e, para os próximos 7 dias, cria um "Evento do servidor" na Sala do pregão no horário da
divulgação. Os membros recebem o lembrete do próprio Discord. Não duplica (compara nome e horário) e nunca apaga.
Critério: importância 3, ou importância 2 que mexe em pelo menos dois de WIN/WDO/DI e sai entre 9h e 18h30.
Precisa da permissão "Criar eventos" no cargo do bot.
"""
import datetime as dt
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'coletor'))
import discord_post as dc  # noqa: E402

BRT = dt.timezone(dt.timedelta(hours=-3))
BANDEIRA = {'BR': '🇧🇷', 'US': '🇺🇸', 'CN': '🇨🇳', 'EU': '🇪🇺', 'JP': '🇯🇵', 'UK': '🇬🇧'}
NOME_ATIVO = {'win': 'WIN', 'wdo': 'WDO', 'di': 'DI'}


def inicio(e):
    m = re.match(r'^(\d{1,2})h(\d{2})?', e.get('hora') or '')
    if not m:
        return None
    return dt.datetime.fromisoformat(f'{e["data"]}T{int(m.group(1)):02d}:{m.group(2) or "00"}:00').replace(tzinfo=BRT)


def escolher(cal, agora):
    out = []
    for e in (cal or {}).get('eventos', []):
        t = inicio(e)
        if not t or not (agora < t <= agora + dt.timedelta(days=7)):
            continue
        imp, ativos = e.get('importancia') or 1, [k for k in ('win', 'wdo', 'di') if (e.get('impacto') or {}).get(k)]
        no_pregao = dt.time(9, 0) <= t.time() <= dt.time(18, 30)
        if imp >= 3 or (imp >= 2 and len(ativos) >= 2 and no_pregao):
            out.append((t, e, ativos))
    return sorted(out, key=lambda x: x[0])


def ficha(tipo, nome, saida):
    """Imagem de capa do evento: as últimas 6 divulgações desse dado, surpresa contra o consenso e quanto WIN e WDO
    andaram nos 30 min seguintes, e o DI de 2 anos no dia (data/reacoes.json). Sem pelo menos 3 registros do mesmo tipo, não gera."""
    try:
        regs = [r for r in json.load(open('data/reacoes.json', encoding='utf-8'))['registros'] if r.get('tipo') == tipo]
    except Exception:
        return None
    regs = sorted(regs, key=lambda r: r['data'])[-6:]
    if len(regs) < 3:
        return None
    from PIL import Image, ImageDraw
    sys.path.insert(0, os.path.dirname(__file__))
    from og_leitura import fonte
    W, H = 1000, 400
    im = Image.new('RGB', (W, H), (8, 16, 28))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 8, H], fill=(0, 153, 136))
    ft, fc, fr, fs = fonte('InterDisplay-Bold.otf', 30), fonte('JetBrainsMono-Bold.ttf', 15), fonte('JetBrainsMono-Bold.ttf', 19), fonte('JetBrainsMono-Bold.ttf', 14)
    titulo = re.sub(r'\s*\(.*?\)', '', nome)[:44]
    d.text((32, 22), f'{titulo} · últimas {len(regs)} divulgações', font=ft, fill=(255, 255, 255))
    d.text((32, 64), 'WIN/WDO: 30 min seguintes (1 h antes de set/2026) · DI: taxa de 2 anos no dia · histórico não garante o próximo', font=fs, fill=(148, 163, 184))
    cols = [32, 150, 290, 430, 570, 730, 880]
    for x, t in zip(cols, ['DATA', 'SAIU', 'CONSENSO', 'SURPRESA', 'WIN', 'WDO', 'DI 2a/dia']):
        d.text((x, 100), t, font=fc, fill=(100, 116, 139))
    y = 128
    for r in reversed(regs):
        sup = r.get('surpresa')
        d.text((cols[0], y), '/'.join(reversed(r['data'].split('-'))), font=fr, fill=(226, 232, 240))
        d.text((cols[1], y), str(r.get('resultado') or '—')[:12], font=fr, fill=(255, 255, 255))
        d.text((cols[2], y), str(r.get('consenso') or '—')[:12], font=fr, fill=(148, 163, 184))
        d.text((cols[3], y), {'acima': '▲ acima', 'abaixo': '▼ abaixo'}.get(sup, '— em linha'), font=fr,
               fill={'acima': (243, 146, 0), 'abaixo': (59, 130, 246)}.get(sup, (148, 163, 184)))
        for x, k in ((cols[4], 'win'), (cols[5], 'wdo')):
            v = r.get(k)
            if v is None:
                d.text((x, y), '—', font=fr, fill=(100, 116, 139)); continue
            cor = (0, 201, 181) if v >= 0 else (244, 63, 94)
            larg = min(60, abs(v) * 60)
            d.rectangle([x, y + 4, x + max(3, larg), y + 20], fill=cor)
            d.text((x + max(3, larg) + 8, y), ('+' if v > 0 else '−' if v < 0 else '') + f'{abs(v):.2f}%'.replace('.', ','), font=fr, fill=cor)
        di = r.get('di_bps')
        d.text((cols[6], y), '—' if di is None else ('+' if di > 0 else '−' if di < 0 else '') + f'{abs(di):.0f} bps', font=fr,
               fill=(100, 116, 139) if di is None else (244, 63, 94) if di > 0 else (0, 201, 181))
        y += 42
    d.text((32, H - 26), 'lectnex.com.br · conteúdo educacional, não é recomendação', font=fs, fill=(100, 116, 139))
    im.save(saida)
    return saida


def main():
    if not dc.TOKEN:
        sys.exit('::error::Falta DISCORD_BOT_TOKEN.')
    cal = json.load(open('data/calendario.json', encoding='utf-8'))
    agora = dt.datetime.now(BRT)
    sala = dc.canal('Sala do pregão')
    if not sala:
        sys.exit('::warning::Sala do pregão não encontrada.')
    existentes = {(x['name'], x['scheduled_start_time'][:16]) for x in dc._req('GET', f'/guilds/{dc.GUILD}/scheduled-events')}
    criados = 0
    for t, e, ativos in escolher(cal, agora):
        nome = f'🔴 Ao vivo: {e["evento"]}'[:100]
        ini = (t - dt.timedelta(minutes=5)).astimezone(dt.timezone.utc)
        if (nome, ini.strftime('%Y-%m-%dT%H:%M')) in existentes:
            continue
        desc = '\n'.join(filter(None, [
            f'{BANDEIRA.get(e.get("pais"), "")} {e["evento"]} · divulgação às {e.get("hora")} (Brasília)',
            f'Consenso: {e["consenso"]} · anterior: {e.get("anterior") or "—"}' if e.get('consenso') else None,
            f'Costuma mexer em: {", ".join(NOME_ATIVO[a] for a in ativos)}' if ativos else None,
            e.get('nota'),
            'Acompanhe junto na Sala do pregão. O resultado e a reação típica saem em #agenda-e-alertas.',
            'Conteúdo educacional, não é recomendação de investimento.']))[:1000]
        corpo = {'name': nome, 'channel_id': sala, 'entity_type': 2, 'privacy_level': 2,
                 'scheduled_start_time': ini.isoformat().replace('+00:00', 'Z'),
                 'scheduled_end_time': (ini + dt.timedelta(minutes=45)).isoformat().replace('+00:00', 'Z'), 'description': desc}
        capa = ficha(e.get('tipo'), e['evento'], os.path.join(os.environ.get('RUNNER_TEMP', '.'), f'ficha-{e.get("tipo")}.png'))
        if capa:
            import base64
            corpo['image'] = 'data:image/png;base64,' + base64.b64encode(open(capa, 'rb').read()).decode()
        try:
            dc._req('POST', f'/guilds/{dc.GUILD}/scheduled-events', corpo)
            criados += 1
            print(f'Evento criado: {e["evento"]} · {t:%d/%m %Hh%M}' + (' · com ficha do histórico' if capa else ''))
        except Exception as ex:
            print(f'::warning::Não criei o evento "{e["evento"]}": {ex}' + (' · ligue "Criar eventos" no cargo do bot' if '50013' in str(ex) else ''))
            if '50013' in str(ex):
                break
    print(f'{criados} evento(s) criado(s).')


if __name__ == '__main__':
    main()
