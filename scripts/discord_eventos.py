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
        try:
            dc._req('POST', f'/guilds/{dc.GUILD}/scheduled-events', corpo)
            criados += 1
            print(f'Evento criado: {e["evento"]} · {t:%d/%m %Hh%M}')
        except Exception as ex:
            print(f'::warning::Não criei o evento "{e["evento"]}": {ex}' + (' · ligue "Criar eventos" no cargo do bot' if '50013' in str(ex) else ''))
            if '50013' in str(ex):
                break
    print(f'{criados} evento(s) criado(s).')


if __name__ == '__main__':
    main()
