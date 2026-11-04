"""Preenche resultado, consenso e surpresa das divulgações antigas (payroll, CPI e IPCA) em data/reacoes.json.

Consenso de mercado conferido em dois calendários econômicos públicos (FXBlue e EnergyExch, consulta em 04/11/2026);
quando os dois discordam na direção da surpresa, a surpresa fica em branco. Só preenche registros sem surpresa.
Regra de "em linha": payroll com diferença de até 10 mil vagas; CPI igual na primeira casa decimal;
IPCA com diferença de até 0,01 ponto. IPCA: consenso de mercado conferido em uma fonte por divulgação (indicada na linha).
"""
import json

# data: (resultado, consenso) — payroll em milhares de vagas, CPI em % no mês (dez/2025: só a/a foi divulgado)
PAYROLL = {
    '2024-11-01': (12, 113), '2024-12-06': (227, 200), '2025-01-10': (256, 160), '2025-02-07': (143, 170), '2025-03-07': (151, 160),
    '2025-04-04': (228, 135), '2025-05-02': (177, 130), '2025-06-06': (139, 130), '2025-07-03': (147, 110), '2025-08-01': (73, 110),
    '2025-09-05': (22, 75), '2025-11-20': (119, 50), '2025-12-16': (64, 50), '2026-01-09': (50, 60), '2026-02-11': (130, 66),
    '2026-03-06': (-92, 58), '2026-04-03': (178, 65), '2026-05-08': (115, 65), '2026-06-05': (172, 85), '2026-07-02': (57, 114),
    '2026-08-07': (-23, 85),
}
CPI = {
    '2024-11-13': (0.2, 0.2), '2024-12-11': (0.3, 0.3), '2025-01-15': (0.4, 0.3), '2025-02-12': (0.5, 0.3), '2025-03-12': (0.2, 0.3),
    '2025-04-10': (-0.1, 0.1), '2025-05-13': (0.2, 0.3), '2025-06-11': (0.1, 0.2), '2025-07-15': (0.3, 0.3), '2025-08-12': (0.2, 0.2),
    '2025-09-11': (0.4, 0.3), '2025-10-24': (0.3, 0.4), '2026-01-13': (0.3, 0.3), '2026-02-13': (0.2, 0.3), '2026-03-11': (0.3, 0.3),
    '2026-04-10': (0.9, None),  # fontes divergem (0,9% e 1,0%)
    '2026-05-12': (0.6, 0.6), '2026-06-10': (0.5, 0.5), '2026-07-14': (-0.4, -0.1), '2026-08-12': (0.1, 0.1),
}
# IPCA: data de divulgação → (resultado % no mês, consenso de mercado, fonte do consenso)
IPCA = {
    '2024-11-08': (0.56, 0.54, 'Nord Research'), '2024-12-10': (0.39, 0.38, 'Itaú Macro'), '2025-01-10': (0.52, 0.57, 'Reuters'),
    '2025-02-11': (0.16, 0.17, 'Itaú Macro'), '2025-03-12': (1.31, 1.31, 'Itaú Macro'), '2025-04-11': (0.56, 0.56, 'VT Markets'),
    '2025-05-09': (0.43, 0.42, 'Itaú Macro'), '2025-06-10': (0.26, 0.32, 'Investing.com'), '2025-07-10': (0.24, 0.20, 'Itaú Macro'),
    '2025-08-12': (0.26, 0.37, 'Invezz'), '2025-09-10': (-0.11, -0.15, 'Itaú Macro'), '2025-10-09': (0.48, 0.52, 'VT Markets'),
    '2025-11-11': (0.09, 0.16, 'VT Markets'), '2025-12-10': (0.18, 0.19, 'Itaú Macro'), '2026-01-09': (0.33, 0.32, 'Itaú Macro'),
    '2026-02-10': (0.33, 0.32, 'Itaú Macro'), '2026-03-12': (0.70, 0.65, 'FXStreet'), '2026-04-10': (0.88, 0.77, 'FXStreet'),
    '2026-05-12': (0.67, 0.70, 'SBT News'), '2026-06-12': (0.58, 0.53, 'Itaú Macro'), '2026-07-10': (0.16, 0.31, 'FXStreet'),
    '2026-08-11': (0.07, 0.03, 'The Rio Times'),
}
CPI_AA = {'2025-12-18': ('2,7% a/a', '3,1% a/a', 'abaixo')}


def mil(v):
    return f'{v} mil'


def pc(v):
    return f'{v:.1f}%'.replace('.', ',').replace('-', '−')


def main():
    base = json.load(open('data/reacoes.json', encoding='utf-8'))
    n = 0
    for r in base['registros']:
        if r.get('surpresa'):
            continue
        d, t = r['data'], r['tipo']
        if t == 'payroll' and d in PAYROLL:
            a, c = PAYROLL[d]
            r['resultado'], r['consenso'] = mil(a), mil(c)
            r['surpresa'] = 'em linha' if abs(a - c) <= 10 else 'acima' if a > c else 'abaixo'
        elif t == 'cpi-eua' and d in CPI:
            a, c = CPI[d]
            r['resultado'], r['consenso'] = pc(a), (pc(c) if c is not None else None)
            r['surpresa'] = None if c is None else 'em linha' if round(a, 1) == round(c, 1) else 'acima' if a > c else 'abaixo'
        elif t == 'ipca' and d in IPCA:
            a, c, f = IPCA[d]
            pp = lambda v: f'{v:.2f}%'.replace('.', ',').replace('-', '−')
            r['resultado'], r['consenso'] = pp(a), pp(c)
            r['surpresa'] = 'em linha' if abs(a - c) <= 0.011 else 'acima' if a > c else 'abaixo'
            r['fonte_consenso'] = f
            n += 1
            continue
        elif t == 'cpi-eua' and d in CPI_AA:
            r['resultado'], r['consenso'], r['surpresa'] = CPI_AA[d]
        else:
            continue
        r['fonte_consenso'] = 'FXBlue e EnergyExch'
        n += 1
    json.dump(base, open('data/reacoes.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'Surpresas preenchidas: {n}')


if __name__ == '__main__':
    main()
