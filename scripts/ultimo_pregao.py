"""É o último pregão da semana? (sexta, ou quinta quando a sexta é feriado da B3, como 20/11.)
Feriados lidos de assets/lectnex-core.js (entradas 'feriado' do calendário) e de data/calendario.json ('B3 fechada').
Uso no shell: python3 scripts/ultimo_pregao.py [AAAA-MM-DD] → código de saída 0 se for, 1 se não for.
"""
import datetime as dt
import json
import os
import re
import sys

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


def _pascoa(y):
    a, b, c = y % 19, y // 100, y % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes, dia = divmod(h + l - 7 * m + 114, 31)
    return dt.date(y, mes, dia + 1)


def b3(y):
    """Mesma regra do site (LX.b3Holidays): feriados nacionais ANBIMA + 24/12 e 31/12."""
    e = _pascoa(y)
    ds = [dt.date(y, 1, 1), e - dt.timedelta(48), e - dt.timedelta(47), e - dt.timedelta(2), dt.date(y, 4, 21), dt.date(y, 5, 1),
          e + dt.timedelta(60), dt.date(y, 9, 7), dt.date(y, 10, 12), dt.date(y, 11, 2), dt.date(y, 11, 15), dt.date(y, 12, 24),
          dt.date(y, 12, 25), dt.date(y, 12, 31)] + ([dt.date(y, 11, 20)] if y >= 2024 else [])
    return {d.isoformat() for d in ds}


def feriados():
    hoje = dt.date.today()
    f = b3(hoje.year) | b3(hoje.year + 1) | b3(hoje.year - 1)
    try:
        f |= set(re.findall(r"\['(\d{4}-\d{2}-\d{2})', 'feriado'", open(os.path.join(RAIZ, 'assets/lectnex-core.js'), encoding='utf-8').read()))
    except Exception:
        pass
    try:
        cal = json.load(open(os.path.join(RAIZ, 'data/calendario.json'), encoding='utf-8')).get('eventos', [])
        f |= {e['data'] for e in cal if 'B3 fechada' in (e.get('evento') or '')}
    except Exception:
        pass
    return f


def pregao(d, fer=None):
    return d.weekday() < 5 and d.isoformat() not in (fer if fer is not None else feriados())


def ultimo_da_semana(d):
    fer = feriados()
    if not pregao(d, fer):
        return False
    prox = d + dt.timedelta(days=1)
    while not pregao(prox, fer):
        prox += dt.timedelta(days=1)
    return prox.isocalendar()[1] != d.isocalendar()[1]


if __name__ == '__main__':
    d = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).date()
    sys.exit(0 if ultimo_da_semana(d) else 1)
