"""Reação dos juros (DI) a cada divulgação de data/reacoes.json, com a curva pública do Tesouro Direto.

O Tesouro publica uma taxa por dia (a da manhã), então a medida é do DIA, não de 30 minutos:
taxa prefixada de ~2 anos na manhã do dia da divulgação → manhã do pregão seguinte, em pontos-base (bps).
Para dado divulgado à noite (ex.: Copom às 18h30) é a reação completa; para dado da manhã, inclui o resto do dia.
O vértice de 2 anos é interpolado entre os títulos prefixados disponíveis (mesma referência do DI jan/2 anos à frente).
Grava em cada registro: di_bps e di_janela. Não mexe nos registros que já têm di_bps (DI_REFAZER=1 refaz).
Roda no workflow da curva (precisa baixar o CSV do Tesouro Transparente).
"""
import csv
import datetime as dt
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'coletor'))
import curva  # noqa: E402  (mesmo download e mesmo filtro de títulos do coletor da curva)

ARQ = 'data/reacoes.json'
ALVO = 2.0  # anos
JANELA = 'dia: taxa prefixada de 2 anos (Tesouro, manhã) do dia do dado ao pregão seguinte'


def curvas_pre(texto):
    por_dia = {}
    for l in csv.DictReader(io.StringIO(texto), delimiter=';'):
        try:
            if curva.tipo(l.get('Tipo Titulo', '')) != 'pre':
                continue
            base = dt.datetime.strptime(l['Data Base'], '%d/%m/%Y').date()
            venc = dt.datetime.strptime(l['Data Vencimento'], '%d/%m/%Y').date()
            taxa = float(l['Taxa Compra Manha'].replace(',', '.'))
        except (KeyError, ValueError):
            continue
        anos = (venc - base).days / 365.25
        if anos > 0.05 and 0 < taxa < 40:
            por_dia.setdefault(base, {})[round(anos, 4)] = taxa
    return por_dia


def taxa_2a(pontos):
    xs = sorted(pontos)
    if not xs or xs[0] > ALVO or xs[-1] < ALVO:
        return None
    for a, b in zip(xs, xs[1:]):
        if a <= ALVO <= b:
            return pontos[a] + (pontos[b] - pontos[a]) * (ALVO - a) / ((b - a) or 1)
    return pontos[xs[0]] if xs[0] == ALVO else None


def main():
    dados = json.load(open(ARQ, encoding='utf-8'))
    regs = dados.get('registros', [])
    refazer = os.environ.get('DI_REFAZER') == '1'
    faltam = [r for r in regs if refazer or 'di_bps' not in r]
    if not faltam:
        print('Reação do DI: nada a medir.')
        return
    try:  # dias de salto da curva por outro motivo (ex.: eleição): a medida do dia não é do dado
        saltos = set(json.load(open('data/juros-saltos.json', encoding='utf-8')).get('dias', {}))
    except Exception:
        saltos = set()
    por_dia = curvas_pre(curva.get(curva.CSV_URL, 180).decode('latin-1'))
    dias = sorted(por_dia)
    feitos = 0
    for r in faltam:
        d = dt.date.fromisoformat(r['data'])
        if d not in por_dia:
            continue
        depois = next((x for x in dias if x > d), None)
        if not depois or (depois - d).days > 5:
            continue  # pregão seguinte ainda não publicado: tenta de novo amanhã
        a, b = taxa_2a(por_dia[d]), taxa_2a(por_dia[depois])
        if a is None or b is None:
            continue
        if depois.isoformat() in saltos and depois != d:
            r['di_bps'] = None
            r['di_obs'] = f'não medido: a curva saltou em {depois:%d/%m} por outro motivo (ver lectnex.com.br/juros/)'
        else:
            r['di_bps'] = round((b - a) * 100, 1)
        r['di_janela'] = JANELA
        feitos += 1
    if feitos:
        dados['metodo_di'] = JANELA + '. Fonte: Tesouro Transparente (preços e taxas do Tesouro Direto).'
        json.dump(dados, open(ARQ, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'::notice::Reação do DI medida em {feitos} divulgação(ões); {len(faltam) - feitos} ainda sem dado.')


if __name__ == '__main__':
    main()
