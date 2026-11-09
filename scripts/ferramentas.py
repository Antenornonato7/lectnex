"""Gera as páginas de ferramenta de resposta rápida (uma busca, uma página):

  vencimento-mini-indice-mini-dolar.html      datas de vencimento e último pregão de WIN e WDO
  calculadora-ir-day-trade.html               imposto de day trade e valor do DARF
  valor-do-ponto-mini-indice-mini-dolar.html  quanto vale o ponto e o tick de WIN e WDO

Cada página tem o texto de resposta no próprio HTML (para o Google) e a ferramenta em JavaScript usando o núcleo
do site (LX). Rode: python3 scripts/ferramentas.py  — e edite os textos aqui, não nos .html gerados."""
import html, json, re

BASE = 'https://lectnex.com.br/'
VER = re.search(r'tailwind\.css\?v=([0-9a-z]+)', open('index.html', encoding='utf-8').read()).group(1)
e = lambda s: html.escape(s, quote=True)

HEAD = '''<!DOCTYPE html>
<html lang="pt-BR" class="scroll-smooth">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{T}}</title>
    <meta name="description" content="{{D}}">
    <link rel="canonical" href="{{U}}">
    <meta name="theme-color" content="#060D17">
    <link rel="icon" href="assets/brand/favicon.svg" type="image/svg+xml">
    <link rel="icon" href="assets/brand/favicon-32.png" sizes="32x32" type="image/png">
    <link rel="apple-touch-icon" href="assets/brand/apple-touch-icon.png">
    <link rel="manifest" href="manifest.webmanifest">
    <meta property="og:type" content="website">
    <meta property="og:site_name" content="Lectnex Terminal">
    <meta property="og:locale" content="pt_BR">
    <meta property="og:title" content="{{T}}">
    <meta property="og:description" content="{{D}}">
    <meta property="og:url" content="{{U}}">
    <meta property="og:image" content="https://lectnex.com.br/assets/brand/og-futuros.jpg">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{{T}}">
    <meta name="twitter:description" content="{{D}}">
    <meta name="twitter:image" content="https://lectnex.com.br/assets/brand/og-futuros.jpg">
    <script type="application/ld+json">{{LD}}</script>
    <script>try{if(localStorage.getItem('lectnex-theme')!=='light')document.documentElement.classList.add('dark');if(localStorage.getItem('lectnex-hc')==='1')document.documentElement.classList.add('lx-hc')}catch(e){document.documentElement.classList.add('dark')}</script>
    <link rel="stylesheet" href="assets/tailwind.css?v={{V}}">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Space+Grotesk:wght@600;700&display=swap" rel="stylesheet" media="print" onload="this.media='all'">
    <noscript><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Space+Grotesk:wght@600;700&display=swap" rel="stylesheet"></noscript>
    <link rel="stylesheet" href="assets/icons/phosphor.css?v={{V}}">
    <link rel="stylesheet" href="assets/lectnex.css?v={{V}}">
</head>
<body data-page="futuros" class="bg-[#F4F6F9] text-lect-navy dark:bg-lect-bgDark dark:text-slate-100 font-sans antialiased selection:bg-lect-teal selection:text-white">
    <!-- Gerado por scripts/ferramentas.py. Não edite à mão. -->
    <div id="lx-topbar"></div>
    <header id="lx-header"></header>
    <main>
        <section class="border-b border-slate-300 dark:border-lect-borderDark grid-bg"><div class="max-w-4xl mx-auto px-4 sm:px-6 py-10">
            <nav class="font-mono text-[11px] text-slate-500"><a href="futuros.html" class="hover:text-lect-teal">Futuros B3</a> / {{CRUMB}}</nav>
            <span class="term-label text-lect-teal font-bold block mt-3">{{EYEBROW}}</span>
            <h1 class="font-display text-2xl sm:text-4xl font-bold tracking-tight mt-1">{{H1}}</h1>
            <p class="mt-3 text-sm sm:text-base text-slate-600 dark:text-slate-300 leading-relaxed">{{LEAD}}</p>
        </div></section>
        <div class="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-6">
{{BODY}}
            <section class="term-panel p-5">
                <h2 class="font-display text-lg font-bold">Perguntas frequentes</h2>
                <dl class="mt-3 space-y-4 text-sm leading-relaxed">{{FAQ}}</dl>
            </section>
            <section><h2 class="term-label font-bold mb-2">FERRAMENTAS RELACIONADAS</h2><div class="grid grid-cols-1 sm:grid-cols-3 gap-3">{{REL}}</div></section>
            <div class="hidden" data-lx-news="chamada" data-titulo="Receba a leitura do WIN e do WDO todo dia de manhã."></div>
            <p class="text-[11px] text-slate-500">{{NOTA}}</p>
        </div>
    </main>
    <div id="lx-footer"></div>
    <script src="assets/lectnex-core.js?v={{V}}"></script>
    <script>
    (function () {
        const $ = id => document.getElementById(id);
{{JS}}
    })();
    </script>
</body>
</html>
'''

TODAS = {
    'venc': ('vencimento-mini-indice-mini-dolar.html', 'Vencimento do WIN e do WDO', 'Datas, último pregão e contrato vigente', 'ph-calendar-check'),
    'ponto': ('valor-do-ponto-mini-indice-mini-dolar.html', 'Valor do ponto: WIN e WDO', 'Converta pontos em reais', 'ph-coins'),
    'ir': ('calculadora-ir-day-trade.html', 'Calculadora de IR day trade', 'Imposto do mês e valor do DARF', 'ph-receipt'),
    'risco': ('futuros.html#risco', 'Calculadora de risco', 'Contratos, stop e alvo por operação', 'ph-shield-check'),
}


def rel(*chaves):
    return ''.join(f'<a href="{TODAS[k][0]}" class="term-panel p-4 hover:border-lect-teal flex items-start gap-3"><i class="ph-bold {TODAS[k][3]} text-xl text-lect-teal"></i><span><strong class="font-display block leading-snug">{TODAS[k][1]}</strong><span class="text-xs text-slate-500">{TODAS[k][2]}</span></span></a>' for k in chaves)


def pagina(arq, t, d, crumb, eyebrow, h1, lead, body, faq, relacionadas, nota, js):
    url = BASE + arq
    ld = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'Organization', '@id': BASE + '#org', 'name': 'Lectnex', 'url': BASE, 'logo': BASE + 'assets/brand/icon-512.png'},
        {'@type': 'WebPage', 'name': h1, 'description': d, 'url': url, 'inLanguage': 'pt-BR', 'publisher': {'@id': BASE + '#org'}},
        {'@type': 'BreadcrumbList', 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'Futuros B3', 'item': BASE + 'futuros.html'},
            {'@type': 'ListItem', 'position': 2, 'name': crumb, 'item': url}]},
        {'@type': 'FAQPage', 'mainEntity': [{'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': re.sub(r'<[^>]+>', '', a)}} for q, a in faq]}]}
    faq_html = ''.join(f'<div><dt class="font-semibold">{q}</dt><dd class="mt-1 text-slate-600 dark:text-slate-300">{a}</dd></div>' for q, a in faq)
    out = HEAD
    for k, v in (('T', e(t)), ('D', e(d)), ('U', url), ('LD', json.dumps(ld, ensure_ascii=False)), ('V', VER), ('CRUMB', crumb), ('EYEBROW', eyebrow),
                 ('H1', h1), ('LEAD', lead), ('BODY', body), ('FAQ', faq_html), ('REL', rel(*relacionadas)), ('NOTA', nota), ('JS', js)):
        out = out.replace('{{' + k + '}}', v)
    open(arq, 'w', encoding='utf-8').write(out)
    print(arq)


NOTA = 'Conteúdo educacional, não é recomendação de investimento. Datas calculadas pelas regras dos contratos e pelos feriados nacionais; em caso de mudança extraordinária, vale o calendário oficial da B3.'

# =============================================================================== 1. Vencimentos
pagina(
    'vencimento-mini-indice-mini-dolar.html',
    'Vencimento do mini índice (WIN) e mini dólar (WDO): datas e último pregão | Lectnex',
    'Datas de vencimento do mini índice e do mini dólar, último dia de negociação, contrato vigente e letra de cada mês. Tabela calculada pelas regras da B3 e atualizada todo dia.',
    'Vencimento do WIN e do WDO', 'CALENDÁRIO DE VENCIMENTOS · REGRAS DA B3',
    'Vencimento do mini índice (WIN) e do mini dólar (WDO)',
    'O <strong>mini índice vence nos meses pares, na quarta-feira mais próxima do dia 15</strong>. O <strong>mini dólar vence todo mês, no primeiro dia útil</strong>, e o último pregão dele é o dia útil anterior. Abaixo estão o contrato vigente e as próximas datas, já com os feriados.',
    '''            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3" id="vc-cards"><div class="term-panel p-5 min-h-[132px]"></div><div class="term-panel p-5 min-h-[132px]"></div></div>
            <section class="term-panel overflow-hidden">
                <h2 class="px-5 py-3 border-b border-slate-200 dark:border-lect-borderDark font-display font-bold">Próximos vencimentos do mini índice (WIN)</h2>
                <div class="overflow-x-auto"><table class="w-full text-left font-mono tabular-nums text-xs"><thead class="quote-head uppercase"><tr><th class="py-2 px-3">Contrato</th><th class="py-2 px-3">Mês</th><th class="py-2 px-3">Vencimento e último pregão</th><th class="py-2 px-3 text-right">Dias úteis</th></tr></thead>
                <tbody id="vc-win" class="divide-y divide-slate-100 dark:divide-lect-borderDark"><tr><td colspan="4" class="py-3 px-3 text-slate-500">Calculando as datas…</td></tr></tbody></table></div>
            </section>
            <section class="term-panel overflow-hidden">
                <h2 class="px-5 py-3 border-b border-slate-200 dark:border-lect-borderDark font-display font-bold">Próximos vencimentos do mini dólar (WDO)</h2>
                <div class="overflow-x-auto"><table class="w-full text-left font-mono tabular-nums text-xs"><thead class="quote-head uppercase"><tr><th class="py-2 px-3">Contrato</th><th class="py-2 px-3">Mês</th><th class="py-2 px-3">Último pregão</th><th class="py-2 px-3">Vencimento</th><th class="py-2 px-3 text-right">Dias úteis</th></tr></thead>
                <tbody id="vc-wdo" class="divide-y divide-slate-100 dark:divide-lect-borderDark"><tr><td colspan="5" class="py-3 px-3 text-slate-500">Calculando as datas…</td></tr></tbody></table></div>
            </section>
            <noscript><p class="text-sm text-slate-500">As tabelas de datas precisam de JavaScript. As regras estão no texto abaixo.</p></noscript>
            <section class="term-panel p-5 text-sm text-slate-600 dark:text-slate-300 leading-relaxed space-y-3">
                <h2 class="font-display text-lg font-bold text-lect-navy dark:text-white">As regras de vencimento</h2>
                <p><strong>Mini índice (WIN):</strong> vence só nos meses pares (fevereiro, abril, junho, agosto, outubro e dezembro), na quarta-feira mais próxima do dia 15. Se não houver pregão nesse dia, passa para o dia útil seguinte. O contrato é negociado até o próprio dia do vencimento.</p>
                <p><strong>Mini dólar (WDO):</strong> vence em todos os meses, no primeiro dia útil. O último dia de negociação é o dia útil anterior, e a liquidação usa a PTAX desse dia. Na prática, o contrato de dezembro é negociado até o último pregão de novembro.</p>
                <p><strong>Como ler o código:</strong> <span class="font-mono">WINZ26</span> é mini índice (WIN) com vencimento em dezembro (Z) de 2026. A letra indica o mês:</p>
                <div class="grid grid-cols-4 sm:grid-cols-6 gap-1.5 font-mono text-xs text-center">
                    <span class="p-2 border border-slate-200 dark:border-lect-borderDark"><strong>F</strong> jan</span><span class="p-2 border border-slate-200 dark:border-lect-borderDark"><strong>G</strong> fev</span><span class="p-2 border border-slate-200 dark:border-lect-borderDark"><strong>H</strong> mar</span><span class="p-2 border border-slate-200 dark:border-lect-borderDark"><strong>J</strong> abr</span><span class="p-2 border border-slate-200 dark:border-lect-borderDark"><strong>K</strong> mai</span><span class="p-2 border border-slate-200 dark:border-lect-borderDark"><strong>M</strong> jun</span>
                    <span class="p-2 border border-slate-200 dark:border-lect-borderDark"><strong>N</strong> jul</span><span class="p-2 border border-slate-200 dark:border-lect-borderDark"><strong>Q</strong> ago</span><span class="p-2 border border-slate-200 dark:border-lect-borderDark"><strong>U</strong> set</span><span class="p-2 border border-slate-200 dark:border-lect-borderDark"><strong>V</strong> out</span><span class="p-2 border border-slate-200 dark:border-lect-borderDark"><strong>X</strong> nov</span><span class="p-2 border border-slate-200 dark:border-lect-borderDark"><strong>Z</strong> dez</span>
                </div>
                <p><strong>Rolagem:</strong> alguns dias antes do vencimento a liquidez migra para o contrato seguinte. Operar o contrato antigo nesses dias significa book mais fino e spread maior. <a href="futuros.html#placar" class="text-lect-teal underline">O placar de vencimento</a> mostra a contagem regressiva até o último pregão.</p>
            </section>''',
    [('Quando vence o mini índice?', 'Nos meses pares, na quarta-feira mais próxima do dia 15. Se a quarta-feira não tiver pregão, o vencimento passa para o dia útil seguinte.'),
     ('Quando vence o mini dólar?', 'No primeiro dia útil de cada mês. O último dia para negociar o contrato é o dia útil anterior.'),
     ('O que acontece se eu ficar com o contrato até o vencimento?', 'A posição é encerrada com liquidação financeira: você recebe ou paga a diferença em dinheiro. No WIN vale o Ibovespa de liquidação do dia do vencimento; no WDO, a PTAX do último dia útil do mês anterior. Não há entrega de ações nem de dólares.'),
     ('Posso operar day trade no dia do vencimento?', 'Pode, mas a liquidez já estará no contrato seguinte. O mais comum é passar a operar o próximo vencimento alguns dias antes.')],
    ('ponto', 'ir', 'risco'), NOTA,
    '''        const hoje = LX.todayBRT();
        const prevBiz = d => { let x = LX.addDays(d, -1); while (!LX.isBusinessDay(x)) x = LX.addDays(x, -1); return x; };
        const dia = d => `${LX.weekday(d)} ${LX.br(d)}`;
        const mes = c => `${LX.monthName[c.month]}/${c.year}`;
        const du = d => { const n = LX.businessDaysBetween(hoje, d, true); return d < hoje ? 'encerrado' : n === 0 ? 'hoje' : n; };
        const lc = LX.liveContracts();
        $('vc-win').innerHTML = LX.upcomingWIN(8).map(c => `<tr class="${c.code === lc.WIN.code ? 'bg-lect-teal/10 font-bold' : ''}"><td class="py-2 px-3">${c.code}</td><td class="py-2 px-3">${mes(c)}</td><td class="py-2 px-3">${dia(c.expiry)}</td><td class="py-2 px-3 text-right">${du(c.expiry)}</td></tr>`).join('');
        $('vc-wdo').innerHTML = LX.upcomingWDO(14).map(c => { const u = prevBiz(c.expiry); return `<tr class="${c.code === lc.WDO.code ? 'bg-lect-teal/10 font-bold' : ''}"><td class="py-2 px-3">${c.code}</td><td class="py-2 px-3">${mes(c)}</td><td class="py-2 px-3">${dia(u)}</td><td class="py-2 px-3">${dia(c.expiry)}</td><td class="py-2 px-3 text-right">${du(u)}</td></tr>`; }).join('');
        const card = (nome, c) => `<div class="term-panel p-5"><span class="term-label">${nome} · CONTRATO VIGENTE</span><strong class="block font-mono text-3xl font-bold mt-1">${c.code}</strong>
            <span class="block text-sm mt-1">Último pregão: <strong>${dia(c.lastTrade)}</strong></span>
            <span class="block text-xs text-slate-500 mt-0.5">${c.duLeft === 0 ? 'É hoje.' : c.duLeft === 1 ? 'Falta 1 dia útil.' : 'Faltam ' + c.duLeft + ' dias úteis.'}${c.next ? ' Depois: ' + c.next.code + '.' : ''}</span></div>`;
        $('vc-cards').innerHTML = card('MINI ÍNDICE', lc.WIN) + card('MINI DÓLAR', lc.WDO);''')

# =============================================================================== 2. IR day trade
pagina(
    'calculadora-ir-day-trade.html',
    'Calculadora de IR day trade: imposto do mês e valor do DARF | Lectnex',
    'Calcule o imposto de renda do day trade em mini índice, mini dólar e ações: 20% sobre o lucro líquido do mês, menos o IRRF de 1%, com compensação de prejuízo. Veja o valor do DARF 6015.',
    'Calculadora de IR day trade', 'IMPOSTO DE RENDA · PESSOA FÍSICA · REGRAS DE 2026',
    'Calculadora de imposto de renda do day trade',
    'No day trade o imposto é de <strong>20% sobre o lucro líquido do mês</strong>, sem faixa de isenção. A corretora retém 1% na fonte, que você abate do DARF. Preencha os valores do mês para ver quanto pagar.',
    '''            <section class="term-panel p-5">
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 font-mono text-xs">
                    <label><span class="term-label block mb-1">Resultado bruto do mês em day trade (R$)</span><input id="ir-bruto" type="number" step="50" value="3500" class="lx-input"><span class="block mt-1 text-[10px] text-slate-500 font-sans">Soma dos ganhos menos as perdas. Use negativo se o mês foi de prejuízo.</span></label>
                    <label><span class="term-label block mb-1">Custos do mês (R$)</span><input id="ir-custos" type="number" step="10" min="0" value="120" class="lx-input"><span class="block mt-1 text-[10px] text-slate-500 font-sans">Corretagem, emolumentos e taxas da B3.</span></label>
                    <label><span class="term-label block mb-1">Prejuízo de day trade de meses anteriores (R$)</span><input id="ir-prej" type="number" step="50" min="0" value="0" class="lx-input"><span class="block mt-1 text-[10px] text-slate-500 font-sans">Ainda não compensado.</span></label>
                    <label><span class="term-label block mb-1">IRRF de 1% retido no mês (R$)</span><input id="ir-irrf" type="number" step="1" min="0" placeholder="automático" class="lx-input"><span class="block mt-1 text-[10px] text-slate-500 font-sans">Está nas notas de corretagem. Em branco, a calculadora estima 1% do lucro líquido.</span></label>
                </div>
                <div id="ir-saida" class="mt-5 grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono tabular-nums text-xs min-h-[76px]"></div>
                <p id="ir-texto" class="mt-4 text-sm text-slate-600 dark:text-slate-300 leading-relaxed"></p>
            </section>
            <section class="term-panel p-5 text-sm text-slate-600 dark:text-slate-300 leading-relaxed space-y-3">
                <h2 class="font-display text-lg font-bold text-lect-navy dark:text-white">Como o imposto do day trade é calculado</h2>
                <ol class="list-decimal pl-5 space-y-1.5">
                    <li>Some o resultado de todas as operações de day trade do mês e desconte os custos. Esse é o <strong>lucro líquido</strong>.</li>
                    <li>Abata o <strong>prejuízo de day trade</strong> acumulado de meses anteriores. Prejuízo de day trade só compensa lucro de day trade.</li>
                    <li>Aplique <strong>20%</strong> sobre o que sobrou.</li>
                    <li>Desconte o <strong>IRRF de 1%</strong> que a corretora já reteve (o "dedo-duro").</li>
                    <li>Pague o restante em um <strong>DARF com código 6015</strong> até o último dia útil do mês seguinte.</li>
                </ol>
                <p><strong>Exemplo:</strong> lucro bruto de R$ 3.500 e custos de R$ 120 dão lucro líquido de R$ 3.380. Imposto de 20%: R$ 676. Com R$ 33,80 de IRRF já retido, o DARF é de R$ 642,20.</p>
                <p>DARF abaixo de R$ 10 não é pago: o valor acumula para o mês seguinte. Em mês de prejuízo não há imposto, e o prejuízo fica guardado para abater lucros futuros. Para controlar isso mês a mês, o <a href="futuros.html#diario" class="text-lect-teal underline">Diário de Trades</a> calcula o DARF sozinho a partir das suas operações.</p>
            </section>''',
    [('Day trade tem isenção de R$ 20 mil?', 'Não. A isenção para vendas de até R$ 20 mil no mês vale só para operações comuns com ações no mercado à vista. Day trade paga 20% sobre qualquer lucro, e futuros como mini índice e mini dólar não têm isenção em nenhuma modalidade.'),
     ('Qual é o código do DARF de day trade?', 'Código 6015, para pessoa física. O vencimento é o último dia útil do mês seguinte ao do lucro.'),
     ('O que é o IRRF de 1%, o "dedo-duro"?', 'É o imposto que a corretora retém na fonte sobre o lucro de cada dia de day trade. Ele não é um imposto a mais: o valor retido é abatido do DARF do mês.'),
     ('Posso compensar prejuízo de day trade com lucro de swing trade?', 'Não. Prejuízo de day trade só compensa lucro de day trade, e prejuízo de operações comuns só compensa lucro de operações comuns. Não há prazo para usar o prejuízo acumulado.')],
    ('ponto', 'venc', 'risco'),
    'Estimativa educacional com as regras de 2026 para pessoa física. Não substitui a apuração oficial nem a orientação de um contador; confirme as regras na Receita Federal.',
    '''        const v = id => parseFloat($(id).value) || 0;
        function calc() {
            const liquido = v('ir-bruto') - v('ir-custos'), prej = v('ir-prej');
            const base = Math.max(0, liquido - prej);
            const irrf = $('ir-irrf').value === '' ? Math.max(0, liquido) * 0.01 : v('ir-irrf');
            const imposto = base * 0.20, darf = Math.max(0, imposto - irrf);
            const sobra = liquido < 0 ? prej - liquido : Math.max(0, prej - liquido);
            const cx = (r, val, cls = '') => `<div class="p-3 bg-slate-50 dark:bg-lect-bgDark border border-slate-200 dark:border-lect-borderDark"><span class="term-label block">${r}</span><strong class="block mt-0.5 text-sm ${cls}">${val}</strong></div>`;
            $('ir-saida').innerHTML = cx('Lucro líquido', LX.brl(liquido), LX.signClass(liquido)) + cx('Base de cálculo', LX.brl(base)) + cx('Imposto (20%)', LX.brl(imposto)) + cx('DARF 6015', LX.brl(darf), 'text-lect-orange');
            $('ir-texto').innerHTML = liquido <= 0
                ? `Mês sem lucro: <strong>não há imposto a pagar</strong>. Prejuízo acumulado para abater nos próximos meses: <strong>${LX.brl(sobra)}</strong>.`
                : base === 0 ? `O prejuízo anterior cobre todo o lucro do mês: <strong>não há imposto a pagar</strong>. Ainda sobram <strong>${LX.brl(sobra)}</strong> de prejuízo para compensar.`
                : darf > 0 && darf < 10 ? `O DARF ficou em ${LX.brl(darf)}, abaixo de R$ 10: <strong>não é pago agora</strong> e acumula para o mês seguinte.`
                : `Imposto de ${LX.brl(imposto)} menos ${LX.brl(irrf)} de IRRF já retido: <strong>DARF de ${LX.brl(darf)}</strong>, código 6015, com vencimento no último dia útil do mês seguinte.${prej > 0 ? ' O prejuízo anterior foi todo usado.' : ''}`;
        }
        ['ir-bruto', 'ir-custos', 'ir-prej', 'ir-irrf'].forEach(id => $(id).addEventListener('input', calc));
        calc();''')

# =============================================================================== 3. Valor do ponto
pagina(
    'valor-do-ponto-mini-indice-mini-dolar.html',
    'Quanto vale o ponto do mini índice (WIN) e do mini dólar (WDO) | Lectnex',
    'Cada ponto do mini índice vale R$ 0,20 e cada ponto do mini dólar vale R$ 10 por contrato. Converta pontos em reais, veja o valor do tick e quantos pontos faltam para a sua meta.',
    'Valor do ponto do WIN e do WDO', 'MINI ÍNDICE E MINI DÓLAR · PONTOS EM REAIS',
    'Quanto vale o ponto do mini índice e do mini dólar',
    'Cada ponto do <strong>mini índice (WIN) vale R$ 0,20</strong> por contrato. Cada ponto do <strong>mini dólar (WDO) vale R$ 10,00</strong> por contrato. Use o conversor para transformar pontos em reais, ou reais em pontos.',
    '''            <section class="term-panel p-5">
                <div class="grid grid-cols-2 gap-1 font-mono text-xs max-w-sm" id="vp-ativo"><button type="button" data-a="WIN" class="py-2 font-bold">WIN · R$ 0,20/ponto</button><button type="button" data-a="WDO" class="py-2 font-bold">WDO · R$ 10/ponto</button></div>
                <div class="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-4 font-mono text-xs">
                    <label><span class="term-label block mb-1">Contratos</span><input id="vp-qtd" type="number" min="1" step="1" value="1" class="lx-input"></label>
                    <label><span class="term-label block mb-1">Pontos</span><input id="vp-pts" type="number" step="5" value="200" class="lx-input"></label>
                    <label><span class="term-label block mb-1">Valor em reais (R$)</span><input id="vp-brl" type="number" step="1" class="lx-input"></label>
                </div>
                <p id="vp-texto" class="mt-4 text-sm text-slate-600 dark:text-slate-300 leading-relaxed min-h-[44px]"></p>
            </section>
            <section class="term-panel overflow-hidden">
                <h2 class="px-5 py-3 border-b border-slate-200 dark:border-lect-borderDark font-display font-bold">Tabela: pontos em reais</h2>
                <div class="overflow-x-auto"><table class="w-full text-left font-mono tabular-nums text-xs"><thead class="quote-head uppercase"><tr><th class="py-2 px-3">Mini índice (WIN)</th><th class="py-2 px-3 text-right">1 contrato</th><th class="py-2 px-3 text-right">5 contratos</th><th class="py-2 px-3 text-right">10 contratos</th></tr></thead>
                <tbody class="divide-y divide-slate-100 dark:divide-lect-borderDark">
                    <tr><td class="py-2 px-3">5 pontos (1 tick)</td><td class="py-2 px-3 text-right">R$ 1,00</td><td class="py-2 px-3 text-right">R$ 5,00</td><td class="py-2 px-3 text-right">R$ 10,00</td></tr>
                    <tr><td class="py-2 px-3">100 pontos</td><td class="py-2 px-3 text-right">R$ 20,00</td><td class="py-2 px-3 text-right">R$ 100,00</td><td class="py-2 px-3 text-right">R$ 200,00</td></tr>
                    <tr><td class="py-2 px-3">250 pontos</td><td class="py-2 px-3 text-right">R$ 50,00</td><td class="py-2 px-3 text-right">R$ 250,00</td><td class="py-2 px-3 text-right">R$ 500,00</td></tr>
                    <tr><td class="py-2 px-3">500 pontos</td><td class="py-2 px-3 text-right">R$ 100,00</td><td class="py-2 px-3 text-right">R$ 500,00</td><td class="py-2 px-3 text-right">R$ 1.000,00</td></tr>
                    <tr><td class="py-2 px-3">1.000 pontos</td><td class="py-2 px-3 text-right">R$ 200,00</td><td class="py-2 px-3 text-right">R$ 1.000,00</td><td class="py-2 px-3 text-right">R$ 2.000,00</td></tr>
                </tbody>
                <thead class="quote-head uppercase"><tr><th class="py-2 px-3">Mini dólar (WDO)</th><th class="py-2 px-3 text-right">1 contrato</th><th class="py-2 px-3 text-right">5 contratos</th><th class="py-2 px-3 text-right">10 contratos</th></tr></thead>
                <tbody class="divide-y divide-slate-100 dark:divide-lect-borderDark">
                    <tr><td class="py-2 px-3">0,5 ponto (1 tick)</td><td class="py-2 px-3 text-right">R$ 5,00</td><td class="py-2 px-3 text-right">R$ 25,00</td><td class="py-2 px-3 text-right">R$ 50,00</td></tr>
                    <tr><td class="py-2 px-3">5 pontos</td><td class="py-2 px-3 text-right">R$ 50,00</td><td class="py-2 px-3 text-right">R$ 250,00</td><td class="py-2 px-3 text-right">R$ 500,00</td></tr>
                    <tr><td class="py-2 px-3">10 pontos</td><td class="py-2 px-3 text-right">R$ 100,00</td><td class="py-2 px-3 text-right">R$ 500,00</td><td class="py-2 px-3 text-right">R$ 1.000,00</td></tr>
                    <tr><td class="py-2 px-3">25 pontos</td><td class="py-2 px-3 text-right">R$ 250,00</td><td class="py-2 px-3 text-right">R$ 1.250,00</td><td class="py-2 px-3 text-right">R$ 2.500,00</td></tr>
                    <tr><td class="py-2 px-3">50 pontos</td><td class="py-2 px-3 text-right">R$ 500,00</td><td class="py-2 px-3 text-right">R$ 2.500,00</td><td class="py-2 px-3 text-right">R$ 5.000,00</td></tr>
                </tbody></table></div>
            </section>
            <section class="term-panel p-5 text-sm text-slate-600 dark:text-slate-300 leading-relaxed space-y-3">
                <h2 class="font-display text-lg font-bold text-lect-navy dark:text-white">De onde vem o valor do ponto</h2>
                <p><strong>Mini índice:</strong> o contrato vale a pontuação do Ibovespa futuro multiplicada por R$ 0,20. Com o índice a 130.000 pontos, 1 contrato representa R$ 26.000. O preço anda de 5 em 5 pontos, então a menor variação (o tick) vale R$ 1,00 por contrato.</p>
                <p><strong>Mini dólar:</strong> o contrato tem tamanho de US$ 10.000 e é cotado em reais por mil dólares. Com o dólar a R$ 5,40, a cotação é 5.400 pontos e 1 contrato representa R$ 54.000. O preço anda de 0,5 em 0,5 ponto, e cada tick vale R$ 5,00 por contrato.</p>
                <p><strong>Os contratos cheios valem 5 vezes mais:</strong> no índice cheio (IND) cada ponto vale R$ 1,00, e no dólar cheio (DOL), R$ 50,00.</p>
                <p>O valor em reais é bruto: dele ainda saem os custos da operação e o imposto de 20% sobre o lucro do mês no day trade. Para definir quantos contratos operar sem arriscar demais, use a <a href="futuros.html#risco" class="text-lect-teal underline">calculadora de risco</a>.</p>
            </section>''',
    [('Quanto vale 1 ponto do mini índice?', 'R$ 0,20 por contrato. Como o preço anda de 5 em 5 pontos, a menor variação possível vale R$ 1,00 por contrato.'),
     ('Quanto vale 1 ponto do mini dólar?', 'R$ 10,00 por contrato. O preço anda de 0,5 em 0,5 ponto, então cada tick vale R$ 5,00 por contrato.'),
     ('Quanto ganho com 100 pontos no mini índice?', 'R$ 20,00 por contrato, antes de custos e imposto. Com 5 contratos, R$ 100,00.'),
     ('Quantos pontos preciso para ganhar R$ 100 no mini dólar?', '10 pontos com 1 contrato, ou 5 pontos com 2 contratos, antes de custos e imposto.')],
    ('venc', 'ir', 'risco'),
    'Conteúdo educacional, não é recomendação de investimento. Valores brutos, sem custos e imposto. Especificações dos contratos conforme a B3.',
    '''        const ATIVO = { WIN: { pv: 0.2, tick: 5, pts: 200, casas: 0 }, WDO: { pv: 10, tick: 0.5, pts: 10, casas: 1 } };
        let ativo = 'WIN';
        const num = id => parseFloat($(id).value) || 0;
        function texto() {
            const a = ATIVO[ativo], q = Math.max(1, Math.floor(num('vp-qtd'))), p = num('vp-pts'), r = p * a.pv * q;
            $('vp-texto').innerHTML = `<strong>${LX.num(p, a.casas)} pontos</strong> no ${ativo} com <strong>${q} contrato${q > 1 ? 's' : ''}</strong> valem <strong class="${LX.signClass(r)}">${LX.brl(r)}</strong>. Cada ponto vale ${LX.brl(a.pv * q)} e cada tick (${LX.num(a.tick, a.casas)} ponto${a.tick > 1 ? 's' : ''}) vale ${LX.brl(a.tick * a.pv * q)}. Valor bruto, antes de custos e imposto.`;
        }
        function dePontos() { const a = ATIVO[ativo], q = Math.max(1, Math.floor(num('vp-qtd'))); $('vp-brl').value = (num('vp-pts') * a.pv * q).toFixed(2); texto(); }
        function deReais() { const a = ATIVO[ativo], q = Math.max(1, Math.floor(num('vp-qtd'))); $('vp-pts').value = +(num('vp-brl') / (a.pv * q)).toFixed(a.casas === 0 ? 0 : 1); texto(); }
        function escolher(k, manter) {
            ativo = k;
            document.querySelectorAll('#vp-ativo button').forEach(b => b.className = 'py-2 font-bold ' + (b.dataset.a === k ? 'bg-lect-teal text-white' : 'bg-slate-100 dark:bg-lect-bgDark text-slate-600 dark:text-slate-300'));
            $('vp-pts').step = ATIVO[k].tick;
            if (!manter) $('vp-pts').value = ATIVO[k].pts;
            dePontos();
        }
        document.querySelectorAll('#vp-ativo button').forEach(b => b.onclick = () => escolher(b.dataset.a));
        $('vp-pts').addEventListener('input', dePontos); $('vp-qtd').addEventListener('input', dePontos); $('vp-brl').addEventListener('input', deReais);
        escolher('WIN');''')

# sitemap
sm = open('sitemap.xml', encoding='utf-8').read()
import datetime as dt
hoje = dt.date.today().isoformat()
for arq in ('vencimento-mini-indice-mini-dolar.html', 'calculadora-ir-day-trade.html', 'valor-do-ponto-mini-indice-mini-dolar.html'):
    if BASE + arq not in sm:
        sm = sm.replace('\n\n', f'\n  <url><loc>{BASE}{arq}</loc><lastmod>{hoje}</lastmod><changefreq>monthly</changefreq><priority>0.8</priority></url>\n\n', 1)
open('sitemap.xml', 'w', encoding='utf-8').write(sm)
