/* =====================================================================
   LECTNEX ACADEMIA — trilhas, lições interativas, quiz e glossário
   Conteúdo educacional. Para editar uma lição, altere o array LESSONS.
   Cada lição: id, trail, title, min (minutos), intro, points[], widget, practice, quiz{q, opts[], a, why}
   ===================================================================== */
(function () {
    'use strict';
    const $ = id => document.getElementById(id);
    const n2 = (v, d = 2) => LX.num(v, d);
    const brl = (v, d = 2) => LX.brl(v, d);
    const STORE = 'lectnex-academia';
    const load = () => { try { return JSON.parse(localStorage.getItem(STORE) || '{}'); } catch (_) { return {}; } };
    const save = st => { try { localStorage.setItem(STORE, JSON.stringify(st)); } catch (_) { } };
    let state = Object.assign({ done: {}, last: null }, load());
    if (typeof state.done !== 'object' || !state.done) state.done = {};

    const TRAILS = [
        { id: 'A', title: 'Fundamentos do dinheiro', desc: 'Quem manda no sistema, Selic e CDI, juros compostos e renda fixa.', icon: 'ph-bank', color: '#009988', tw: 'text-lect-teal' },
        { id: 'B', title: 'Ações na B3', desc: 'Tipos de ação, dividendos e JCP, e os indicadores que importam.', icon: 'ph-chart-bar', color: '#F39200', tw: 'text-lect-orange' },
        { id: 'C', title: 'Day trade de futuros', desc: 'WIN e WDO na prática: ponto, alavancagem, risco e imposto.', icon: 'ph-lightning', color: '#6366F1', tw: 'text-indigo-500' }
    ];

    /* ------------------------------------------------------------ LIÇÕES */
    const LESSONS = [
        {
            id: 'A1', trail: 'A', title: 'Quem manda no mercado', min: 4,
            intro: 'Todo real que circula em conta, título público ou bolsa passa por uma cadeia de órgãos. Saber quem faz o quê explica por que uma decisão do Copom mexe no seu CDB e no WIN no mesmo dia.',
            points: [
                '<strong>CMN</strong> define a meta de inflação. <strong>Banco Central</strong> persegue essa meta mudando a Selic nas reuniões do <strong>Copom</strong> (8 por ano, a cada ~45 dias).',
                '<strong>CVM</strong> é o “xerife” do mercado de capitais: fiscaliza empresas abertas, fundos, corretoras e ofertas, e pune <em>insider trading</em>.',
                '<strong>B3</strong> é onde se negociam ações, opções e futuros (WIN, WDO, DI) e onde ficam custodiados seus ativos, no seu CPF.',
                '<strong>FGC</strong> protege até R$ 250 mil por CPF e por instituição (teto de R$ 1 milhão a cada 4 anos) em CDB, LCI, LCA e poupança. Não cobre ações, fundos nem debêntures.'
            ],
            widget: 'sfn',
            practice: 'Quando o Copom corta a Selic, o CDI cai junto, a renda fixa pós-fixada rende menos e parte do dinheiro migra para a bolsa — é a mesma decisão chegando a três lugares diferentes.',
            quiz: { q: 'Quem fiscaliza as empresas abertas e os fundos de investimento?', opts: ['Banco Central', 'CVM', 'B3', 'FGC'], a: 1, why: 'A CVM regula e fiscaliza o mercado de capitais. O Banco Central cuida da moeda, dos juros e dos bancos.' }
        },
        {
            id: 'A2', trail: 'A', title: 'Selic e CDI: a régua de tudo', min: 5,
            intro: 'A Selic é o preço do dinheiro no Brasil. O CDI acompanha a Selic quase colado e virou a régua para medir qualquer investimento: se não bate o CDI, precisa de um bom motivo.',
            points: [
                '<strong>Selic Meta</strong> é decidida pelo Copom. <strong>Selic Over</strong> é a taxa efetiva que os bancos praticam entre si, com lastro em títulos públicos — fica um pouco abaixo da meta.',
                '<strong>CDI</strong> nasce dos empréstimos de um dia entre bancos (nenhum banco pode fechar o dia no negativo). Por isso fica praticamente igual à Selic Over.',
                'O rendimento é por <strong>dia útil</strong>, numa base de 252 dias: fator diário = (1 + CDI)<sup>1/252</sup> − 1.'
            ],
            widget: 'cdi',
            practice: 'Um CDB de “100% do CDI” rende exatamente a taxa do CDI de cada dia útil. Um de 110% rende 10% a mais que isso — antes do imposto.',
            quiz: { q: 'Por que o CDI fica quase igual à Selic Over?', opts: ['Porque o governo fixa os dois por lei', 'Porque ambos refletem empréstimos de curtíssimo prazo entre bancos', 'Porque o CDI é a média da poupança', 'Por coincidência'], a: 1, why: 'Os dois são taxas de empréstimos de um dia entre instituições financeiras — um com lastro em títulos públicos (Selic Over), outro em CDI. Por isso andam juntos.' }
        },
        {
            id: 'A3', trail: 'A', title: 'Juros compostos', min: 5,
            intro: 'Juros sobre juros: o rendimento de cada mês passa a render também. No começo quase não se nota; com o tempo, os juros superam o dinheiro que você colocou.',
            points: [
                'Fórmula: <strong>Valor final = Inicial × (1 + taxa)<sup>tempo</sup></strong>, somada aos aportes, que também compõem.',
                '<strong>Regra dos 72</strong>: divida 72 pela taxa anual e você tem, aproximadamente, em quantos anos o dinheiro dobra.',
                'O fator que mais pesa é o <strong>tempo</strong>. Dobrar o prazo costuma fazer mais diferença que dobrar o aporte.'
            ],
            widget: 'juros',
            practice: 'Mexa no prazo da ferramenta: repare como a parte laranja (juros) cresce muito mais rápido que a parte verde (o que você aportou) depois de uns 10 anos.',
            quiz: { q: 'Pela regra dos 72, a 12% ao ano, em quanto tempo o dinheiro dobra?', opts: ['Cerca de 3 anos', 'Cerca de 6 anos', 'Cerca de 12 anos', 'Cerca de 72 meses... ou seja, 12 anos'], a: 1, why: '72 ÷ 12 = 6. Conferindo: 1,12⁶ ≈ 1,97, praticamente o dobro.' }
        },
        {
            id: 'A4', trail: 'A', title: 'Renda fixa e imposto', min: 6,
            intro: 'Na renda fixa você empresta dinheiro: ao governo (Tesouro), a um banco (CDB, LCI, LCA) ou a uma empresa (debêntures, CRI, CRA). O que muda é quem paga, como o juro é calculado e quanto de imposto sai.',
            points: [
                '<strong>Pós-fixado</strong> (Tesouro Selic, CDB % do CDI): acompanha os juros do dia a dia. Ideal para reserva e margem na B3.',
                '<strong>Prefixado</strong>: taxa travada na compra. Ganha se os juros caírem, perde na marcação a mercado se subirem.',
                '<strong>IPCA+</strong> (Tesouro IPCA+, NTN-B): inflação mais um juro real. Protege o poder de compra no longo prazo.',
                '<strong>IR regressivo</strong> (CDB, Tesouro, debêntures comuns): 22,5% até 180 dias · 20% até 360 · 17,5% até 720 · 15% acima disso. <strong>LCI, LCA, CRI, CRA</strong> e debêntures incentivadas são isentas para pessoa física.'
            ],
            widget: 'lci',
            practice: 'Por isso uma LCI de 90% do CDI pode render mais que um CDB de 100%: compare sempre o rendimento líquido no mesmo prazo.',
            quiz: { q: 'Num CDB resgatado depois de 2 anos e meio, qual alíquota de IR incide sobre o lucro?', opts: ['22,5%', '20%', '17,5%', '15%'], a: 3, why: 'Acima de 720 dias a alíquota é a mínima da tabela regressiva: 15%.' }
        },
        {
            id: 'B1', trail: 'B', title: 'Decifrando o código da ação', min: 4,
            intro: 'Quatro letras identificam a empresa; o número no final diz que tipo de papel é. Saber ler isso evita comprar o ativo errado.',
            points: [
                '<strong>3 — ON (ordinária)</strong>: dá direito a voto e a <em>tag along</em>. No Novo Mercado, todas as ações são ON. Ex.: VALE3, WEGE3.',
                '<strong>4, 5, 6 — PN (preferencial)</strong>: preferência nos dividendos, em geral sem voto. Ex.: PETR4, ITUB4.',
                '<strong>11 — Units</strong> (pacotes de ON + PN, ex.: TAEE11), mas também <strong>FIIs</strong> e <strong>ETFs</strong> usam final 11.',
                '<strong>Desdobramento</strong> (split) multiplica a quantidade e divide o preço; <strong>grupamento</strong> faz o contrário. Seu patrimônio não muda.'
            ],
            widget: 'ticker',
            practice: 'Antes de comprar, confira se a empresa tem ON e PN e qual tem mais liquidez — às vezes a diferença de preço e de dividendo entre as duas é grande.',
            quiz: { q: 'O que significa o final “3” em VALE3?', opts: ['Ação preferencial', 'Ação ordinária, com direito a voto', 'Fundo imobiliário', 'Terceira emissão da empresa'], a: 1, why: 'Final 3 é ação ordinária (ON): direito a voto em assembleia e a tag along.' }
        },
        {
            id: 'B2', trail: 'B', title: 'Dividendos, JCP e a Data Ex', min: 5,
            intro: 'Como sócio, você recebe parte do lucro. Mas o preço da ação se ajusta no dia em que o direito ao provento acaba — não existe dinheiro de graça.',
            points: [
                '<strong>Dividendos</strong>: saem do lucro já tributado na empresa. Isentos para pessoa física até R$ 50 mil por mês da mesma empresa; acima disso, retenção de 10% (regra em vigor desde jan/2026).',
                '<strong>JCP</strong>: calculado sobre o patrimônio líquido e lançado como despesa pela empresa. Retenção de <strong>17,5% na fonte</strong> desde jan/2026 — você recebe 82,5%.',
                'Quem tem a ação no fim da <strong>Data Com</strong> recebe. Na <strong>Data Ex</strong>, a B3 desconta o provento do preço de referência.'
            ],
            widget: 'dataex',
            practice: 'Comprar na véspera da Data Com só para receber o dividendo raramente compensa: o preço cai o valor do provento na Data Ex, e no JCP ainda sai o imposto.',
            quiz: { q: 'Uma ação fechou a R$ 30,00 na Data Com e vai pagar R$ 1,50 de dividendo. Qual o preço de referência na abertura da Data Ex?', opts: ['R$ 30,00', 'R$ 31,50', 'R$ 28,50', 'R$ 28,76'], a: 2, why: 'O caixa sai da empresa e vai para o acionista, então a B3 ajusta: 30,00 − 1,50 = 28,50.' }
        },
        {
            id: 'B3', trail: 'B', title: 'Os indicadores que importam', min: 6,
            intro: 'Quatro números contam boa parte da história de uma empresa: quanto custa em relação ao lucro, ao patrimônio, quanto rende o capital e quanto distribui.',
            points: [
                '<strong>P/L</strong> = preço ÷ lucro por ação. Em quantos anos o lucro atual “pagaria” o preço.',
                '<strong>P/VP</strong> = preço ÷ valor patrimonial por ação. Abaixo de 1, a bolsa paga menos que o patrimônio contábil.',
                '<strong>ROE</strong> = lucro ÷ patrimônio. Quanto a empresa gera sobre o dinheiro dos sócios; acima do CDI é bom sinal.',
                '<strong>DY</strong> = proventos de 12 meses ÷ preço. <strong>Payout</strong> = quanto do lucro vira provento.'
            ],
            widget: 'mult',
            practice: 'Nenhum indicador sozinho decide nada: P/L baixo pode ser pechincha ou lucro prestes a cair. Compare sempre com empresas do mesmo setor e com o histórico da própria empresa.',
            quiz: { q: 'Uma ação custa R$ 40 e o lucro por ação é R$ 5. Qual o P/L?', opts: ['5x', '8x', '12,5%', '45x'], a: 1, why: 'P/L = 40 ÷ 5 = 8. O lucro atual levaria 8 anos para somar o preço da ação.' }
        },
        {
            id: 'C1', trail: 'C', title: 'WIN e WDO: quanto vale um ponto', min: 4,
            intro: 'Minicontratos futuros permitem operar o índice e o dólar com pouco capital. Tudo começa em saber quanto dinheiro cada ponto representa.',
            points: [
                '<strong>WIN (mini índice)</strong>: cada ponto vale <strong>R$ 0,20</strong> por contrato; oscila de 5 em 5 pontos (R$ 1,00 por tick).',
                '<strong>WDO (mini dólar)</strong>: cada ponto vale <strong>R$ 10,00</strong> por contrato; oscila de 0,5 em 0,5 ponto (R$ 5,00 por tick).',
                '<strong>Vencimentos</strong>: WIN vence na quarta-feira mais próxima do dia 15 dos meses pares; WDO no 1º dia útil de cada mês. Perto do vencimento a liquidez migra para o contrato seguinte.'
            ],
            widget: 'ponto',
            practice: 'Antes de clicar em comprar, transforme o stop em reais: 200 pontos de stop em 5 WIN são R$ 200. Pense em dinheiro, não em pontos.',
            quiz: { q: 'Você comprou 2 WIN e o índice subiu 300 pontos. Qual o resultado bruto?', opts: ['R$ 60', 'R$ 120', 'R$ 600', 'R$ 6.000'], a: 1, why: '300 pts × R$ 0,20 × 2 contratos = R$ 120.' }
        },
        {
            id: 'C2', trail: 'C', title: 'Margem, alavancagem e ajuste diário', min: 5,
            intro: 'Com R$ 100 ou R$ 200 de margem de day trade você movimenta um contrato que vale dezenas de milhares de reais. É isso que torna o futuro poderoso — e perigoso.',
            points: [
                '<strong>Valor nocional</strong> do WIN = pontos do índice × R$ 0,20. Com o índice em 140 mil pontos, um contrato “vale” R$ 28 mil.',
                '<strong>Margem</strong> é a garantia exigida, não o preço do contrato. A de day trade é definida pela corretora e é bem menor que a da B3 para carregar posição.',
                '<strong>Ajuste diário</strong>: quem leva posição para o dia seguinte recebe ou paga a diferença em dinheiro todo dia, conforme o preço de ajuste da B3.'
            ],
            widget: 'alav',
            practice: 'Alavancagem alta não é vantagem por si só: ela só aumenta o tamanho do resultado, para cima e para baixo. O controle está no número de contratos e no stop.',
            quiz: { q: 'A margem de day trade é…', opts: ['o preço do contrato', 'uma garantia exigida, bem menor que o valor do contrato', 'o lucro máximo possível', 'uma taxa paga à B3 por operação'], a: 1, why: 'Margem é garantia. O contrato movimenta o valor nocional inteiro, por isso a alavancagem.' }
        },
        {
            id: 'C3', trail: 'C', title: 'Expectativa: acerto não é tudo', min: 5,
            intro: 'Dá para ganhar dinheiro acertando só 35% das operações — e perder acertando 70%. O que decide é a combinação entre taxa de acerto e o tamanho dos ganhos em relação às perdas.',
            points: [
                '<strong>Risco:retorno</strong> = tamanho do alvo ÷ tamanho do stop. Um stop de 100 com alvo de 200 é 1:2.',
                '<strong>Expectativa por trade</strong> (em múltiplos do risco, “R”) = acerto × retorno − erro × 1.',
                '<strong>Acerto mínimo para empatar</strong> = 1 ÷ (1 + retorno). Em 1:2, basta acertar mais de 33,3%.'
            ],
            widget: 'expect',
            practice: 'Depois de achar uma expectativa positiva, o próximo passo é decidir quanto arriscar por trade. A calculadora de risco e a curva de Kelly em Futuros B3 fazem isso com seus números.',
            link: ['Abrir a calculadora de risco e a curva de Kelly', 'futuros.html#risco'],
            quiz: { q: 'Com relação risco:retorno de 1:3, qual o acerto mínimo para não perder dinheiro (sem custos)?', opts: ['50%', '33,3%', '25%', '75%'], a: 2, why: '1 ÷ (1 + 3) = 25%. Acima disso a expectativa é positiva.' }
        },
        {
            id: 'C4', trail: 'C', title: 'Imposto de renda no day trade', min: 4,
            intro: 'Day trade tem regras próprias de imposto. Errar o DARF gera multa e juros — e prejuízo mal controlado é dinheiro que você deixa de abater.',
            points: [
                'Alíquota de <strong>20%</strong> sobre o lucro líquido do mês em day trade (sem isenção de R$ 20 mil, que vale só para venda de ações no swing).',
                'A corretora retém <strong>1% na fonte</strong> (o “dedo-duro”) sobre o resultado positivo do dia; esse valor é descontado do DARF.',
                'Prejuízo de day trade só compensa lucro de <strong>day trade</strong>, nos meses seguintes, sem prazo de validade.',
                'DARF código <strong>6015</strong>, pago até o último dia útil do mês seguinte. Valor abaixo de R$ 10 acumula para o próximo.'
            ],
            widget: 'irdt',
            practice: 'Mantenha uma planilha mês a mês com resultado, IRRF retido e prejuízo a compensar. A nota de corretagem traz os números; a responsabilidade de pagar é sua.',
            quiz: { q: 'Prejuízo em day trade de futuros pode ser compensado com…', opts: ['qualquer lucro em bolsa', 'lucro de day trade nos meses seguintes', 'apenas no mesmo mês', 'nada, o prejuízo se perde'], a: 1, why: 'Prejuízo de day trade só abate lucro de day trade, e pode ser carregado para os meses seguintes.' }
        }
    ];

    /* ------------------------------------------------------------ GLOSSÁRIO */
    const GLOSS = [
        ['Ajuste diário', 'Liquidação financeira diária das posições em futuros que passam de um dia para o outro, pela diferença entre o preço de ajuste da B3 e o do dia anterior.'],
        ['Alavancagem', 'Operar um valor maior do que o capital próprio. No futuro, a margem é uma fração do valor do contrato, o que multiplica ganhos e perdas.'],
        ['Book de ofertas', 'Lista das ordens de compra e venda pendentes em cada preço. Mostra onde há liquidez.'],
        ['BTC', 'Banco de Títulos da B3: aluguel de ações. Quem doa recebe uma taxa; quem toma pode vender a descoberto.'],
        ['Call', 'Opção de compra: dá ao titular o direito de comprar o ativo pelo preço de exercício até o vencimento.'],
        ['CDI', 'Taxa dos empréstimos de um dia entre bancos. Praticamente igual à Selic Over e referência para a renda fixa.'],
        ['Contango', 'Situação em que o futuro negocia acima do preço à vista, refletindo custo de carregamento ou juros.'],
        ['Copom', 'Comitê de Política Monetária do Banco Central. Define a Selic Meta em oito reuniões por ano.'],
        ['Data Com', 'Último dia em que quem tem a ação garante o direito ao provento anunciado.'],
        ['Data Ex', 'Primeiro dia em que a ação é negociada sem o direito ao provento; o preço de referência é ajustado.'],
        ['DARF', 'Documento de arrecadação usado para pagar o IR de renda variável (código 6015 para pessoa física).'],
        ['Day trade', 'Compra e venda do mesmo ativo no mesmo dia. Tributada a 20% sobre o lucro líquido do mês.'],
        ['DI1', 'Contrato futuro de taxa DI na B3. Suas taxas formam a curva de juros do mercado.'],
        ['Dividend Yield (DY)', 'Proventos pagos em 12 meses divididos pelo preço atual da ação.'],
        ['Drawdown', 'Queda do capital a partir do último topo. Mede a dor das sequências de perda.'],
        ['FGC', 'Fundo Garantidor de Créditos: cobre até R$ 250 mil por CPF e instituição em CDB, LCI, LCA e poupança.'],
        ['Focus', 'Boletim semanal do Banco Central com as projeções do mercado para inflação, Selic, PIB e câmbio.'],
        ['Gap', 'Salto de preço entre o fechamento de um dia e a abertura do seguinte, sem negócios no meio.'],
        ['IPCA', 'Índice oficial de inflação do Brasil, medido pelo IBGE. É a referência da meta de inflação.'],
        ['JCP', 'Juros sobre capital próprio: forma de remunerar o acionista lançada como despesa pela empresa; retenção de 17,5% de IR desde 2026.'],
        ['Liquidez', 'Facilidade de comprar ou vender sem mexer muito no preço. Mais negócios e book cheio = mais liquidez.'],
        ['Margem', 'Garantia exigida para manter uma posição em derivativos. Não é o preço do contrato.'],
        ['Marcação a mercado', 'Atualização diária do preço de um título pelo valor que o mercado pagaria hoje.'],
        ['P/L', 'Preço da ação dividido pelo lucro por ação. Indica quantos anos de lucro atual pagariam o preço.'],
        ['P/VP', 'Preço dividido pelo valor patrimonial por ação. Abaixo de 1, negocia abaixo do patrimônio contábil.'],
        ['PTAX', 'Taxa de câmbio oficial calculada pelo Banco Central. Usada para liquidar o dólar futuro no vencimento.'],
        ['Put', 'Opção de venda: dá ao titular o direito de vender o ativo pelo preço de exercício.'],
        ['ROE', 'Retorno sobre o patrimônio: lucro líquido dividido pelo patrimônio líquido.'],
        ['Rolagem', 'Trocar a posição do contrato que vai vencer pelo contrato do vencimento seguinte.'],
        ['Selic', 'Taxa básica de juros da economia, definida pelo Copom. Base para todo o custo do dinheiro no país.'],
        ['Slippage', 'Diferença entre o preço esperado e o preço executado, comum em mercados rápidos ou com pouca liquidez.'],
        ['Stop loss', 'Ordem que encerra a posição num preço pré-definido para limitar a perda.'],
        ['Tag along', 'Direito do minoritário de vender suas ações nas mesmas condições do controlador, se a empresa for vendida.'],
        ['Tick', 'Menor variação de preço permitida num ativo. No WIN, 5 pontos; no WDO, 0,5 ponto.'],
        ['Volatilidade', 'Intensidade das oscilações de preço. Mais volatilidade = movimentos maiores para os dois lados.']
    ];

    /* ------------------------------------------------------------ WIDGETS */
    const field = (id, label, val, attrs = '') => `<label class="block"><span class="term-label block mb-1">${label}</span><input id="${id}" type="number" value="${val}" ${attrs} class="lx-input"></label>`;
    const range = (id, label, val, min, max, step) => `<label class="block"><span class="term-label flex justify-between mb-1"><span>${label}</span><strong id="${id}-v" class="text-lect-navy dark:text-white"></strong></span><input id="${id}" type="range" min="${min}" max="${max}" step="${step}" value="${val}" class="w-full accent-[#009988]"></label>`;
    const out = (label, id, cls = '') => `<div class="p-3 bg-white dark:bg-lect-cardDark border border-slate-200 dark:border-lect-borderDark"><span class="term-label block">${label}</span><strong id="${id}" class="block text-lg font-mono tabular-nums mt-0.5 ${cls}">—</strong></div>`;
    const v = id => parseFloat(($(id) || {}).value) || 0;
    const live = (ids, fn) => { ids.forEach(i => { const el = $(i); if (el) el.addEventListener('input', fn); }); fn(); };

    const WIDGETS = {
        sfn: {
            title: 'Mapa interativo do sistema', html: () => {
                const nodes = [
                    ['CMN', 'Define a meta de inflação e as regras gerais do sistema.', 'ph-gavel', '#0C1A2A'],
                    ['Banco Central', 'Executa a política monetária e fiscaliza os bancos.', 'ph-bank', '#009988'],
                    ['Copom', 'Decide a Selic Meta 8 vezes por ano.', 'ph-percent', '#009988'],
                    ['CVM', 'Regula e fiscaliza empresas abertas, fundos e corretoras.', 'ph-shield-check', '#F39200'],
                    ['B3', 'Bolsa: negociação, liquidação e custódia de ações e derivativos.', 'ph-buildings', '#6366F1'],
                    ['Bancos e corretoras', 'Intermediam: captam (CDB, LCI) e dão acesso à bolsa.', 'ph-handshake', '#64748B'],
                    ['FGC', 'Garante depósitos e títulos bancários até R$ 250 mil.', 'ph-umbrella', '#10B981'],
                    ['Você', 'Investidor: empresta ao governo, a bancos e empresas, ou vira sócio.', 'ph-user', '#E11D48']
                ];
                return `<div class="grid grid-cols-2 sm:grid-cols-4 gap-2">${nodes.map((nd, i) => `<button type="button" data-sfn="${i}" class="text-left p-3 border-2 border-transparent bg-white dark:bg-lect-cardDark hover:border-lect-teal transition-colors"><i class="ph-duotone ${nd[2]} text-2xl" style="color:${nd[3]}"></i><strong class="block text-xs mt-1">${nd[0]}</strong></button>`).join('')}</div>
                <div id="sfn-info" class="mt-3 p-3 bg-lect-navy text-white text-xs border-l-4 border-lect-orange min-h-[44px]">Clique em cada peça para ver o papel dela.</div>`;
            }, bind: () => {
                const info = ['CMN: define a meta de inflação e as regras gerais. Não mexe na Selic diretamente — isso é com o Banco Central.', 'Banco Central: persegue a meta de inflação e supervisiona bancos. Atua no câmbio e publica a PTAX e o Focus.', 'Copom: reúne-se a cada ~45 dias e decide a Selic Meta. Cada decisão mexe no CDI, na curva DI, no dólar e na bolsa.', 'CVM: o “xerife” do mercado de capitais. Fiscaliza empresas abertas, fundos e corretoras; pune insider trading e manipulação.', 'B3: onde as ordens se encontram. Garante a liquidação (contraparte central) e guarda seus ativos no seu CPF.', 'Bancos e corretoras: captam seu dinheiro (CDB, LCI, LCA) e dão acesso à bolsa. A corretora não é dona dos seus ativos — eles ficam na B3.', 'FGC: se um banco quebrar, devolve até R$ 250 mil por CPF por instituição (teto de R$ 1 milhão a cada 4 anos). Não cobre ações nem fundos.', 'Você: decide para quem empresta (Tesouro, banco, empresa) ou de qual empresa vira sócio. Entender a cadeia é o primeiro passo.'];
                document.querySelectorAll('[data-sfn]').forEach(b => b.onclick = () => {
                    document.querySelectorAll('[data-sfn]').forEach(x => x.classList.remove('!border-lect-orange'));
                    b.classList.add('!border-lect-orange'); $('sfn-info').textContent = info[+b.dataset.sfn];
                });
            }
        },
        cdi: {
            title: 'Quanto rende o CDI', html: () => `<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">${range('w-cdi', 'CDI ao ano', (LX.data.cdi.value || 13.65).toFixed(2), 2, 20, 0.05)}${field('w-cdi-val', 'Valor aplicado (R$)', 10000, 'step="1000"')}</div>
                <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-3">${out('Por dia útil', 'w-cdi-d')}${out('Por mês (21 DU)', 'w-cdi-m')}${out('Em 1 ano (bruto)', 'w-cdi-y', 'text-emerald-600')}${out('Em 1 ano (líquido)', 'w-cdi-yl', 'text-lect-teal')}</div>
                <p class="text-[11px] text-slate-500 mt-2">Líquido com IR de 17,5% (resgate entre 361 e 720 dias). Taxa atual do CDI pelo Banco Central: ${LX.pct(LX.data.cdi.value)}.</p>`,
            bind: () => live(['w-cdi', 'w-cdi-val'], () => {
                const r = v('w-cdi') / 100, P = v('w-cdi-val'), d = Math.pow(1 + r, 1 / 252) - 1, m = Math.pow(1 + d, 21) - 1;
                $('w-cdi-v').textContent = LX.pct(r * 100); $('w-cdi-d').textContent = LX.pct(d * 100, 4);
                $('w-cdi-m').textContent = LX.pct(m * 100, 2); $('w-cdi-y').textContent = '+' + brl(P * r); $('w-cdi-yl').textContent = '+' + brl(P * r * 0.825);
            })
        },
        juros: {
            title: 'Simulador de juros compostos', html: () => `<div class="grid grid-cols-2 sm:grid-cols-4 gap-3">${field('w-j-ini', 'Inicial (R$)', 5000, 'step="500"')}${field('w-j-ap', 'Aporte mensal (R$)', 500, 'step="100"')}${field('w-j-tx', 'Taxa ao ano (%)', 11, 'step="0.5"')}${range('w-j-anos', 'Prazo', 20, 1, 40, 1)}</div>
                <div id="w-j-chart" class="mt-3"></div>
                <div class="grid grid-cols-3 gap-2 mt-2">${out('Você aportou', 'w-j-apt', 'text-emerald-600')}${out('Juros ganhos', 'w-j-jur', 'text-lect-orange')}${out('Valor final', 'w-j-fim')}</div>
                <p id="w-j-72" class="text-[11px] text-slate-500 mt-2"></p>`,
            bind: () => live(['w-j-ini', 'w-j-ap', 'w-j-tx', 'w-j-anos'], () => {
                const ini = v('w-j-ini'), ap = v('w-j-ap'), tx = v('w-j-tx') / 100, anos = Math.round(v('w-j-anos')), im = Math.pow(1 + tx, 1 / 12) - 1;
                $('w-j-anos-v').textContent = anos + (anos > 1 ? ' anos' : ' ano');
                let bal = ini, inv = ini; const rows = [];
                for (let y = 1; y <= anos; y++) { for (let k = 0; k < 12; k++) { bal = bal * (1 + im) + ap; inv += ap; } rows.push([inv, bal]); }
                const W = 600, H = 150, L = 4, bw = (W - L) / anos, mx = rows[rows.length - 1][1] || 1;
                let s = `<svg viewBox="0 0 ${W} ${H + 16}" class="w-full h-auto font-mono" role="img" aria-label="Evolução do patrimônio">`;
                rows.forEach(([i, b], k) => { const x = L + k * bw + bw * 0.12, w = bw * 0.76, hb = b / mx * H, hi = i / mx * H; s += `<rect x="${x}" y="${H - hb}" width="${w}" height="${hb - hi}" fill="#F39200"/><rect x="${x}" y="${H - hi}" width="${w}" height="${hi}" fill="#009988"/>`; });
                [1, Math.ceil(anos / 2), anos].filter((x, i, a) => a.indexOf(x) === i).forEach(y => s += `<text x="${L + (y - 0.5) * bw}" y="${H + 12}" font-size="10" text-anchor="middle" fill="#64748B">ano ${y}</text>`);
                $('w-j-chart').innerHTML = s + '</svg>';
                $('w-j-apt').textContent = brl(inv, 0); $('w-j-jur').textContent = brl(bal - inv, 0); $('w-j-fim').textContent = brl(bal, 0);
                $('w-j-72').innerHTML = tx > 0 ? `Regra dos 72: a ${LX.pct(tx * 100, 1)} ao ano, o dinheiro dobra em cerca de <strong>${n2(72 / (tx * 100), 1)} anos</strong>. Os juros já representam <strong>${LX.pct((bal - inv) / bal * 100, 0)}</strong> do valor final.` : '';
            })
        },
        lci: {
            title: 'LCI isenta × CDB tributado', html: () => `<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">${range('w-l-pct', 'LCI/LCA (% do CDI)', 90, 70, 110, 1)}<label class="block"><span class="term-label block mb-1">Prazo do investimento</span><select id="w-l-prazo" class="lx-input"><option value="22.5">até 180 dias</option><option value="20">181 a 360 dias</option><option value="17.5" selected>361 a 720 dias</option><option value="15">acima de 720 dias</option></select></label></div>
                <div class="mt-3 grid grid-cols-4 gap-px bg-slate-200 dark:bg-lect-borderDark font-mono text-[11px] text-center" id="w-l-tab"></div>
                <div class="mt-3 p-4 bg-lect-navy text-white border-l-4 border-lect-orange text-sm" id="w-l-out"></div>`,
            bind: () => live(['w-l-pct', 'w-l-prazo'], () => {
                const p = v('w-l-pct'), ir = v('w-l-prazo');
                $('w-l-pct-v').textContent = p + '% do CDI';
                $('w-l-tab').innerHTML = [['22.5', 'até 180d'], ['20', '181–360d'], ['17.5', '361–720d'], ['15', '+720d']].map(([a, l]) => `<div class="p-2 ${+a === ir ? 'bg-lect-teal text-white font-bold' : 'bg-white dark:bg-lect-cardDark'}"><span class="block text-[9px] opacity-70">${l}</span>${a.replace('.', ',')}%</div>`).join('');
                $('w-l-out').innerHTML = `Uma LCI de <strong>${p}% do CDI</strong> equivale a um CDB de <strong class="text-lect-orange text-lg">${n2(p / (1 - ir / 100), 1)}% do CDI</strong> nesse prazo. Só vale trocar pelo CDB se ele pagar mais que isso.`;
            })
        },
        ticker: {
            title: 'Decodificador de ticker', html: () => `<div class="flex gap-2"><input id="w-t" class="lx-input uppercase" value="PETR4" maxlength="6"></div>
                <div class="flex flex-wrap gap-1.5 mt-2">${['VALE3', 'PETR4', 'CPLE6', 'TAEE11', 'BOVA11', 'AAPL34'].map(t => `<button type="button" data-tk="${t}" class="px-2 py-1 text-[11px] font-mono bg-white dark:bg-lect-cardDark border border-slate-200 dark:border-lect-borderDark hover:border-lect-teal">${t}</button>`).join('')}</div>
                <div id="w-t-out" class="mt-3"></div>`,
            bind: () => {
                const run = () => {
                    const t = $('w-t').value.trim().toUpperCase(), m = t.match(/^([A-Z]{4})(\d{1,2})$/);
                    if (!m) { $('w-t-out').innerHTML = '<p class="text-xs text-slate-500">Digite 4 letras e um número, como PETR4.</p>'; return; }
                    const nmb = +m[2], map = { 3: ['ON · ordinária', 'Direito a voto em assembleia e a tag along. É a única classe no Novo Mercado.', '#009988'], 4: ['PN · preferencial', 'Preferência no recebimento de dividendos; em geral sem voto.', '#F39200'], 5: ['PNA · preferencial classe A', 'Preferencial com direitos específicos definidos no estatuto.', '#F39200'], 6: ['PNB · preferencial classe B', 'Outra classe de preferencial, com direitos próprios no estatuto.', '#F39200'], 11: ['Unit, FII ou ETF', 'Final 11 é usado por units (pacote de ON + PN, ex.: TAEE11), fundos imobiliários e ETFs (ex.: BOVA11). Confira o tipo antes de comprar.', '#6366F1'] };
                    const info = map[nmb] || (nmb >= 32 && nmb <= 35 ? ['BDR', 'Recibo de ação estrangeira negociado na B3 (ex.: AAPL34 = Apple).', '#0EA5E9'] : ['Outro tipo', 'Códigos menos comuns: direitos de subscrição (1, 2), recibos (9, 10) etc.', '#64748B']);
                    $('w-t-out').innerHTML = `<div class="flex items-stretch border border-slate-200 dark:border-lect-borderDark bg-white dark:bg-lect-cardDark"><div class="px-4 py-3 font-mono text-2xl font-bold flex items-center"><span>${m[1]}</span><span style="color:${info[2]}">${m[2]}</span></div><div class="p-3 border-l border-slate-200 dark:border-lect-borderDark"><span class="term-label block">${m[1]} = empresa · ${m[2]} = tipo</span><strong class="block" style="color:${info[2]}">${info[0]}</strong><span class="text-xs text-slate-600 dark:text-slate-300">${info[1]}</span></div></div>`;
                };
                $('w-t').addEventListener('input', run);
                document.querySelectorAll('[data-tk]').forEach(b => b.onclick = () => { $('w-t').value = b.dataset.tk; run(); });
                run();
            }
        },
        dataex: {
            title: 'O que acontece na Data Ex', html: () => `<div class="grid grid-cols-2 sm:grid-cols-4 gap-3">${field('w-d-p', 'Preço na Data Com (R$)', 30, 'step="0.5"')}${field('w-d-v', 'Provento por ação (R$)', 1.5, 'step="0.1"')}${field('w-d-q', 'Ações na carteira', 500, 'step="100"')}<label class="block"><span class="term-label block mb-1">Tipo</span><select id="w-d-t" class="lx-input"><option value="div">Dividendo</option><option value="jcp">JCP</option></select></label></div>
                <div id="w-d-bars" class="mt-4"></div>
                <div class="grid grid-cols-3 gap-2 mt-3">${out('Preço na Data Ex', 'w-d-ex')}${out('Você recebe (líquido)', 'w-d-rec', 'text-emerald-600')}${out('Patrimônio total', 'w-d-pat')}</div>`,
            bind: () => live(['w-d-p', 'w-d-v', 'w-d-q', 'w-d-t'], () => {
                const p = v('w-d-p'), d = v('w-d-v'), q = v('w-d-q'), jcp = $('w-d-t').value === 'jcp', liq = d * (jcp ? 0.825 : 1), ex = p - d;
                const pct = x => Math.max(0, Math.min(100, x / p * 100));
                $('w-d-bars').innerHTML = `<div class="space-y-2 font-mono text-[11px]"><div class="flex items-center gap-2"><span class="w-20 text-slate-500">Data Com</span><div class="flex-1 h-6 bg-lect-teal" style="width:100%"></div><span class="w-20 text-right">${brl(p)}</span></div>
                  <div class="flex items-center gap-2"><span class="w-20 text-slate-500">Data Ex</span><div class="flex-1 flex h-6"><div class="h-full bg-lect-teal" style="width:${pct(ex)}%"></div><div class="h-full bg-emerald-500" style="width:${pct(liq)}%"></div>${jcp ? `<div class="h-full bg-rose-500" style="width:${pct(d - liq)}%"></div>` : ''}</div><span class="w-20 text-right">${brl(ex)}</span></div>
                  <div class="flex gap-4 pl-[88px] text-[10px] text-slate-500"><span><i class="inline-block w-2 h-2 bg-lect-teal"></i> ação</span><span><i class="inline-block w-2 h-2 bg-emerald-500"></i> provento no bolso</span>${jcp ? '<span><i class="inline-block w-2 h-2 bg-rose-500"></i> IR 17,5%</span>' : ''}</div></div>`;
                $('w-d-ex').textContent = brl(ex); $('w-d-rec').textContent = '+' + brl(liq * q);
                $('w-d-pat').innerHTML = `${brl((ex + liq) * q)} <span class="text-[11px] ${jcp ? 'text-rose-600' : 'text-slate-500'}">${jcp ? '(−' + brl((d - liq) * q) + ' de IR)' : '(igual ao de antes)'}</span>`;
            })
        },
        mult: {
            title: 'Calculadora de múltiplos', html: () => `<div class="grid grid-cols-2 sm:grid-cols-4 gap-3">${field('w-m-p', 'Preço (R$)', 40, 'step="0.5"')}${field('w-m-lpa', 'Lucro por ação (R$)', 5, 'step="0.1"')}${field('w-m-vpa', 'Patrimônio por ação (R$)', 32, 'step="0.5"')}${field('w-m-dpa', 'Proventos 12m por ação (R$)', 2.4, 'step="0.1"')}</div>
                <div class="grid grid-cols-2 sm:grid-cols-5 gap-2 mt-3" id="w-m-out"></div>`,
            bind: () => live(['w-m-p', 'w-m-lpa', 'w-m-vpa', 'w-m-dpa'], () => {
                const p = v('w-m-p'), l = v('w-m-lpa'), vp = v('w-m-vpa'), dv = v('w-m-dpa'), cdi = LX.data.cdi.value;
                const pl = l > 0 ? p / l : NaN, pvp = vp > 0 ? p / vp : NaN, roe = vp > 0 ? l / vp * 100 : NaN, dy = p > 0 ? dv / p * 100 : NaN, pay = l > 0 ? dv / l * 100 : NaN;
                const card = (lab, val, note, ok) => `<div class="p-3 bg-white dark:bg-lect-cardDark border-t-4 ${ok === true ? 'border-emerald-500' : ok === false ? 'border-rose-500' : 'border-slate-300'}"><span class="term-label block">${lab}</span><strong class="block text-lg font-mono">${val}</strong><span class="text-[10px] text-slate-500 leading-tight block">${note}</span></div>`;
                $('w-m-out').innerHTML =
                    card('P/L', isFinite(pl) ? n2(pl, 1) + 'x' : '—', isFinite(pl) ? `${n2(pl, 1)} anos de lucro pagam o preço` : 'lucro negativo', isFinite(pl) ? pl < 15 : false) +
                    card('P/VP', isFinite(pvp) ? n2(pvp, 2) + 'x' : '—', pvp < 1 ? 'abaixo do patrimônio' : 'acima do patrimônio', null) +
                    card('ROE', isFinite(roe) ? LX.pct(roe, 1) : '—', `CDI hoje: ${LX.pct(cdi, 1)}`, isFinite(roe) ? roe > cdi : null) +
                    card('Dividend Yield', isFinite(dy) ? LX.pct(dy, 1) : '—', 'proventos ÷ preço', null) +
                    card('Payout', isFinite(pay) ? LX.pct(pay, 0) : '—', pay > 100 ? 'paga mais do que lucra!' : 'do lucro distribuído', isFinite(pay) ? pay <= 100 : null);
            })
        },
        ponto: {
            title: 'Conversor de pontos em reais', html: () => `<div class="grid grid-cols-2 gap-1 font-mono text-xs" id="w-p-a"><button type="button" data-a="WIN" class="py-2 font-bold">WIN · R$ 0,20/pt</button><button type="button" data-a="WDO" class="py-2 font-bold">WDO · R$ 10/pt</button></div>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">${range('w-p-pts', 'Movimento em pontos', 300, 5, 2000, 5)}${range('w-p-n', 'Contratos', 2, 1, 20, 1)}</div>
                <div class="mt-3 p-4 bg-lect-navy text-white border-l-4 border-lect-orange flex flex-wrap items-baseline justify-between gap-2"><span id="w-p-desc" class="text-sm"></span><strong id="w-p-res" class="font-mono text-2xl text-lect-orange"></strong></div>
                <p id="w-p-tick" class="text-[11px] text-slate-500 mt-2"></p>`,
            bind: () => {
                let a = 'WIN'; const cfg = { WIN: { pv: 0.2, tick: 5, max: 2000, step: 5, def: 300 }, WDO: { pv: 10, tick: 0.5, max: 60, step: 0.5, def: 10 } };
                const set = x => { a = x; document.querySelectorAll('#w-p-a button').forEach(b => b.className = 'py-2 font-bold ' + (b.dataset.a === a ? 'bg-lect-navy text-white border-l-2 border-lect-orange' : 'bg-white dark:bg-lect-cardDark text-slate-600 dark:text-slate-300')); const r = $('w-p-pts'), c = cfg[a]; r.max = c.max; r.step = c.step; r.min = c.step; r.value = c.def; calc(); };
                const calc = () => { const c = cfg[a], pts = v('w-p-pts'), n = v('w-p-n'); $('w-p-pts-v').textContent = n2(pts, a === 'WDO' ? 1 : 0) + ' pts'; $('w-p-n-v').textContent = n; $('w-p-desc').innerHTML = `${n2(pts, a === 'WDO' ? 1 : 0)} pts × ${brl(c.pv)} × ${n} contrato${n > 1 ? 's' : ''}`; $('w-p-res').textContent = brl(pts * c.pv * n); $('w-p-tick').textContent = `1 tick do ${a} = ${n2(c.tick, a === 'WDO' ? 1 : 0)} pts = ${brl(c.tick * c.pv)} por contrato · com ${n} contratos, cada tick vale ${brl(c.tick * c.pv * n)}.`; };
                document.querySelectorAll('#w-p-a button').forEach(b => b.onclick = () => set(b.dataset.a));
                ['w-p-pts', 'w-p-n'].forEach(i => $(i).addEventListener('input', calc)); set('WIN');
            }
        },
        alav: {
            title: 'Quanto você realmente movimenta', html: () => `<div class="grid grid-cols-1 sm:grid-cols-3 gap-3">${field('w-a-idx', 'Índice futuro (pontos)', 140000, 'step="1000"')}${field('w-a-mg', 'Margem day trade por contrato (R$)', 150, 'step="10"')}${range('w-a-mv', 'Movimento do índice', 1, 0.25, 3, 0.25)}</div>
                <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-3">${out('Valor de 1 contrato', 'w-a-not')}${out('Alavancagem', 'w-a-lev', 'text-lect-orange')}${out('Movimento em pontos', 'w-a-pts')}${out('Resultado × margem', 'w-a-res', 'text-rose-600')}</div>
                <p id="w-a-txt" class="text-xs text-slate-600 dark:text-slate-300 mt-3 leading-relaxed"></p>`,
            bind: () => live(['w-a-idx', 'w-a-mg', 'w-a-mv'], () => {
                const idx = v('w-a-idx'), mg = v('w-a-mg'), mv = v('w-a-mv') / 100, nt = idx * 0.2, pts = idx * mv, res = pts * 0.2;
                $('w-a-mv-v').textContent = LX.pct(mv * 100, 2); $('w-a-not').textContent = brl(nt, 0);
                $('w-a-lev').textContent = mg > 0 ? n2(nt / mg, 0) + 'x' : '—'; $('w-a-pts').textContent = n2(pts, 0) + ' pts';
                $('w-a-res').textContent = mg > 0 ? LX.pct(res / mg * 100, 0) : '—';
                $('w-a-txt').innerHTML = `Com ${brl(mg, 0)} de margem você movimenta ${brl(nt, 0)}. Um movimento de ${LX.pct(mv * 100, 2)} no índice (${n2(pts, 0)} pontos, comum num único dia) dá <strong>${brl(res)}</strong> por contrato — <strong>${mg > 0 ? LX.pct(res / mg * 100, 0) : '—'} da margem</strong>, para cima ou para baixo.`;
            })
        },
        expect: {
            title: 'Calculadora de expectativa', html: () => `<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">${range('w-e-wr', 'Taxa de acerto', 40, 10, 90, 1)}${range('w-e-rr', 'Risco : retorno', 2, 0.5, 5, 0.25)}</div>
                <div class="mt-4 font-mono text-[11px]"><div class="flex justify-between text-slate-500 mb-1"><span>0%</span><span>acerto</span><span>100%</span></div><div class="relative h-4 bg-slate-200 dark:bg-lect-bgDark"><div id="w-e-zone" class="absolute inset-y-0 right-0 bg-emerald-500/30"></div><div id="w-e-be" class="absolute -top-1 -bottom-1 w-0.5 bg-lect-navy dark:bg-white"></div><div id="w-e-you" class="absolute -top-1.5 w-3 h-7 -ml-1.5 bg-lect-orange border-2 border-white"></div></div><div class="flex justify-between mt-1 text-[10px]"><span id="w-e-bel" class="text-slate-500"></span><span class="text-emerald-600">zona de lucro →</span></div></div>
                <div class="grid grid-cols-3 gap-2 mt-3">${out('Expectativa por trade', 'w-e-ev')}${out('Acerto mínimo', 'w-e-min')}${out('Em 100 trades', 'w-e-100')}</div>`,
            bind: () => live(['w-e-wr', 'w-e-rr'], () => {
                const wr = v('w-e-wr') / 100, rr = v('w-e-rr'), ev = wr * rr - (1 - wr), be = 1 / (1 + rr);
                $('w-e-wr-v').textContent = LX.pct(wr * 100, 0); $('w-e-rr-v').textContent = '1 : ' + n2(rr, 2);
                $('w-e-zone').style.left = be * 100 + '%'; $('w-e-be').style.left = be * 100 + '%'; $('w-e-you').style.left = wr * 100 + '%';
                $('w-e-bel').textContent = 'empate em ' + LX.pct(be * 100, 1);
                $('w-e-ev').textContent = (ev >= 0 ? '+' : '') + n2(ev, 2) + 'R'; $('w-e-ev').className = 'block text-lg font-mono tabular-nums mt-0.5 ' + LX.signClass(ev);
                $('w-e-min').textContent = LX.pct(be * 100, 1);
                $('w-e-100').textContent = (ev >= 0 ? '+' : '') + n2(ev * 100, 0) + 'R'; $('w-e-100').className = 'block text-lg font-mono tabular-nums mt-0.5 ' + LX.signClass(ev);
            })
        },
        irdt: {
            title: 'Calculadora do DARF de day trade', html: () => `<div class="grid grid-cols-2 sm:grid-cols-4 gap-3">${field('w-i-lb', 'Resultado bruto do mês (R$)', 3000, 'step="100"')}${field('w-i-c', 'Custos (corretagem, emolumentos)', 120, 'step="10"')}${field('w-i-pj', 'Prejuízo DT a compensar (R$)', 500, 'step="100"')}${field('w-i-rf', 'IRRF retido (1%)', 30, 'step="1"')}</div>
                <div class="mt-3 border border-slate-200 dark:border-lect-borderDark bg-white dark:bg-lect-cardDark font-mono text-xs divide-y divide-slate-100 dark:divide-lect-borderDark" id="w-i-steps"></div>`,
            bind: () => live(['w-i-lb', 'w-i-c', 'w-i-pj', 'w-i-rf'], () => {
                const lb = v('w-i-lb'), c = v('w-i-c'), pj = v('w-i-pj'), rf = v('w-i-rf'), liq = lb - c, base = Math.max(0, liq - pj), imp = base * 0.2, darf = Math.max(0, imp - rf), sobra = liq < 0 ? pj - liq : Math.max(0, pj - liq);
                const row = (l, val, cls = '') => `<div class="flex justify-between px-3 py-2"><span class="text-slate-500">${l}</span><strong class="${cls}">${val}</strong></div>`;
                $('w-i-steps').innerHTML = row('Resultado líquido (bruto − custos)', brl(liq), LX.signClass(liq)) + row('(−) prejuízo a compensar', '−' + brl(Math.min(pj, Math.max(0, liq)))) + row('Base de cálculo', brl(base)) + row('IR 20%', brl(imp)) + row('(−) IRRF já retido', '−' + brl(Math.min(rf, imp))) +
                    `<div class="flex justify-between px-3 py-3 bg-lect-navy text-white"><span>DARF a pagar · código 6015</span><strong class="text-lect-orange text-base">${darf < 10 && darf > 0 ? brl(darf) + ' (acumula: < R$ 10)' : brl(darf)}</strong></div>` + row('Prejuízo que sobra para os próximos meses', brl(sobra));
            })
        }
    };

    /* ------------------------------------------------------------ RENDER */
    let current = null;
    const trailOf = id => TRAILS.find(t => t.id === id);
    const lessonsOf = tid => LESSONS.filter(l => l.trail === tid);
    const doneCount = tid => (tid ? lessonsOf(tid) : LESSONS).filter(l => state.done[l.id]).length;
    const nextLesson = () => LESSONS.find(l => !state.done[l.id]);

    function ring(pct, size = 86) {
        const r = (size - 10) / 2, c = 2 * Math.PI * r;
        return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}"><circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" stroke="rgba(255,255,255,.12)" stroke-width="8"/><circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" stroke="#F39200" stroke-width="8" stroke-linecap="butt" stroke-dasharray="${c}" stroke-dashoffset="${c * (1 - pct)}" transform="rotate(-90 ${size / 2} ${size / 2})" style="transition:stroke-dashoffset .6s ease"/><text x="50%" y="54%" text-anchor="middle" font-family="Space Grotesk, sans-serif" font-weight="700" font-size="20" fill="#fff">${Math.round(pct * 100)}%</text></svg>`;
    }

    function renderHero() {
        const d = doneCount(), tot = LESSONS.length;
        $('ac-ring').innerHTML = ring(tot ? d / tot : 0);
        $('ac-progress-txt').textContent = `${d} de ${tot}`;
        $('ac-n-lessons').textContent = tot; $('ac-n-terms').textContent = GLOSS.length;
        $('ac-trail-bars').innerHTML = TRAILS.map(t => { const n = lessonsOf(t.id).length, k = doneCount(t.id); return `<div><div class="flex justify-between text-[11px]"><span class="text-slate-300">${t.title}</span><span class="font-mono text-slate-400">${k}/${n}</span></div><div class="h-1.5 bg-white/10 mt-1"><div class="h-full transition-all" style="width:${k / n * 100}%;background:${t.color}"></div></div></div>`; }).join('');
        const nx = nextLesson(), btn = $('ac-continue');
        btn.querySelector('span').textContent = d === 0 ? 'Começar a primeira lição' : nx ? `Continuar: ${nx.title}` : 'Revisar as lições';
        btn.onclick = () => { open((nx || LESSONS[0]).id); $('ac-player').scrollIntoView({ behavior: 'smooth' }); };
    }

    function renderTrails() {
        $('ac-trails').innerHTML = TRAILS.map((t, i) => {
            const ls = lessonsOf(t.id), k = doneCount(t.id), mins = ls.reduce((a, l) => a + l.min, 0), on = current && current.trail === t.id;
            return `<button type="button" data-trail="${t.id}" class="group text-left term-panel p-5 border-t-4 transition-all hover:-translate-y-0.5 ${on ? 'ring-2 ring-offset-2 ring-offset-[#F4F6F9] dark:ring-offset-lect-bgDark' : ''}" style="border-top-color:${t.color};${on ? '--tw-ring-color:' + t.color : ''}">
                <div class="flex items-start justify-between"><span class="w-11 h-11 grid place-items-center" style="background:${t.color}1A"><i class="ph-duotone ${t.icon} text-2xl" style="color:${t.color}"></i></span><span class="font-mono text-[10px] font-bold text-slate-400">TRILHA ${String(i + 1).padStart(2, '0')}</span></div>
                <strong class="block font-display text-lg mt-3">${t.title}</strong>
                <span class="block text-xs text-slate-500 mt-1 min-h-[32px]">${t.desc}</span>
                <div class="flex items-center gap-3 mt-4 font-mono text-[10px] text-slate-500"><span><i class="ph ph-book-open"></i> ${ls.length} lições</span><span><i class="ph ph-clock"></i> ${mins} min</span><span class="ml-auto font-bold" style="color:${t.color}">${k === ls.length ? '✓ CONCLUÍDA' : k + '/' + ls.length}</span></div>
                <div class="h-1 bg-slate-100 dark:bg-lect-bgDark mt-2"><div class="h-full transition-all" style="width:${k / ls.length * 100}%;background:${t.color}"></div></div></button>`;
        }).join('');
        document.querySelectorAll('[data-trail]').forEach(b => b.onclick = () => {
            const ls = lessonsOf(b.dataset.trail), first = ls.find(l => !state.done[l.id]) || ls[0];
            open(first.id); $('ac-player').scrollIntoView({ behavior: 'smooth' });
        });
    }

    function renderSide() {
        const t = trailOf(current.trail), ls = lessonsOf(t.id);
        $('ac-side-head').innerHTML = `<span class="term-label font-bold" style="color:${t.color}">TRILHA</span><strong class="block font-display text-lg">${t.title}</strong><span class="text-[11px] text-slate-500">${doneCount(t.id)} de ${ls.length} concluídas</span>`;
        $('ac-side').innerHTML = ls.map((l, i) => {
            const on = l.id === current.id, ok = state.done[l.id];
            return `<li><button type="button" data-lesson="${l.id}" class="w-full text-left flex items-center gap-3 px-4 py-3 border-l-4 transition-colors ${on ? 'bg-slate-50 dark:bg-lect-bgDark' : 'border-transparent hover:bg-slate-50 dark:hover:bg-lect-bgDark'}" style="${on ? 'border-left-color:' + t.color : ''}">
                <span class="w-7 h-7 shrink-0 grid place-items-center font-mono text-[11px] font-bold ${ok ? 'text-white' : 'border-2 border-slate-300 dark:border-lect-borderDark text-slate-500'}" style="${ok ? 'background:' + t.color : ''}">${ok ? '<i class="ph-bold ph-check"></i>' : i + 1}</span>
                <span class="min-w-0"><span class="block text-sm ${on ? 'font-bold' : ''} truncate">${l.title}</span><span class="text-[10px] font-mono text-slate-400">${l.min} min · ${WIDGETS[l.widget].title}</span></span></button></li>`;
        }).join('') + `<li class="p-3 bg-slate-50 dark:bg-lect-bgDark"><div class="flex gap-1">${TRAILS.filter(x => x.id !== t.id).map(x => `<button type="button" data-trail2="${x.id}" class="flex-1 px-2 py-1.5 text-[10px] font-mono font-bold border border-slate-200 dark:border-lect-borderDark hover:border-lect-teal truncate" title="${x.title}"><i class="ph-bold ${x.icon}" style="color:${x.color}"></i> ${x.title}</button>`).join('')}</div></li>`;
        document.querySelectorAll('[data-lesson]').forEach(b => b.onclick = () => open(b.dataset.lesson));
        document.querySelectorAll('[data-trail2]').forEach(b => b.onclick = () => { const ls2 = lessonsOf(b.dataset.trail2); open((ls2.find(l => !state.done[l.id]) || ls2[0]).id); });
    }

    function renderLesson() {
        const l = current, t = trailOf(l.trail), ls = lessonsOf(t.id), idx = ls.indexOf(l), w = WIDGETS[l.widget], ok = state.done[l.id];
        const gi = LESSONS.indexOf(l), prev = LESSONS[gi - 1], next = LESSONS[gi + 1];
        $('ac-lesson').innerHTML = `
            <div class="p-6 border-b border-slate-200 dark:border-lect-borderDark">
                <div class="flex flex-wrap items-center gap-2 font-mono text-[10px] font-bold"><span class="px-2 py-0.5 text-white" style="background:${t.color}">${t.title.toUpperCase()}</span><span class="text-slate-400">LIÇÃO ${idx + 1} DE ${ls.length} · ${l.min} MIN</span>${ok ? `<span class="text-emerald-600"><i class="ph-bold ph-check-circle"></i> CONCLUÍDA</span>` : ''}</div>
                <h2 class="font-display text-2xl sm:text-3xl font-bold mt-2">${l.title}</h2>
                <p class="text-slate-600 dark:text-slate-300 mt-2 leading-relaxed">${l.intro}</p>
            </div>
            <div class="p-6 space-y-6">
                <section><span class="term-label font-bold" style="color:${t.color}">O ESSENCIAL</span>
                    <ul class="mt-2 space-y-2.5">${l.points.map(p => `<li class="flex gap-3 text-sm leading-relaxed"><span class="mt-1.5 w-1.5 h-1.5 shrink-0" style="background:${t.color}"></span><span class="text-slate-700 dark:text-slate-300">${p}</span></li>`).join('')}</ul></section>
                <section class="bg-slate-50 dark:bg-lect-bgDark border border-slate-200 dark:border-lect-borderDark">
                    <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-200 dark:border-lect-borderDark"><span class="inline-flex items-center gap-2 font-mono text-[11px] font-bold"><i class="ph-fill ph-hand-pointing text-lect-orange"></i>EXPERIMENTE · ${w.title.toUpperCase()}</span><span class="lx-demo">INTERATIVO</span></div>
                    <div class="p-4">${w.html()}</div></section>
                <section class="flex gap-3 p-4 border-l-4 border-lect-orange bg-orange-50 dark:bg-lect-orange/10"><i class="ph-duotone ph-lightbulb text-2xl text-lect-orange shrink-0"></i><div><span class="term-label font-bold text-lect-orange">NA PRÁTICA</span><p class="text-sm text-slate-700 dark:text-slate-300 mt-1 leading-relaxed">${l.practice}</p>${l.link ? `<a href="${l.link[1]}" class="inline-flex items-center gap-1 mt-2 text-xs font-bold text-lect-teal hover:underline">${l.link[0]} <i class="ph-bold ph-arrow-right"></i></a>` : ''}</div></section>
                <section id="ac-quiz" class="border border-slate-200 dark:border-lect-borderDark">
                    <div class="px-4 py-2.5 bg-lect-navy text-white flex items-center gap-2 font-mono text-[11px] font-bold"><i class="ph-fill ph-question text-lect-orange"></i>TESTE RÁPIDO</div>
                    <div class="p-4"><p class="font-bold text-sm">${l.quiz.q}</p>
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-3">${l.quiz.opts.map((o, i) => `<button type="button" data-opt="${i}" class="text-left px-3 py-2.5 text-sm border-2 border-slate-200 dark:border-lect-borderDark hover:border-lect-teal transition-colors flex items-center gap-2"><span class="w-6 h-6 shrink-0 grid place-items-center font-mono text-[11px] font-bold bg-slate-100 dark:bg-lect-bgDark">${'ABCD'[i]}</span><span>${o}</span></button>`).join('')}</div>
                        <div id="ac-qfb" class="hidden mt-3 p-3 text-sm"></div></div>
                </section>
            </div>
            <div class="flex items-center justify-between gap-2 px-6 py-4 border-t border-slate-200 dark:border-lect-borderDark bg-slate-50 dark:bg-lect-bgDark">
                ${prev ? `<button type="button" data-go="${prev.id}" class="inline-flex items-center gap-1.5 text-xs font-bold text-slate-500 hover:text-lect-teal min-w-0"><i class="ph-bold ph-arrow-left"></i><span class="truncate">${prev.title}</span></button>` : '<span></span>'}
                ${next ? `<button type="button" data-go="${next.id}" class="inline-flex items-center gap-1.5 px-4 py-2 bg-lect-navy text-white text-xs font-bold hover:bg-lect-teal min-w-0"><span class="truncate">Próxima: ${next.title}</span><i class="ph-bold ph-arrow-right"></i></button>` : `<button type="button" onclick="document.getElementById('glossario').scrollIntoView({behavior:'smooth'})" class="inline-flex items-center gap-1.5 px-4 py-2 bg-lect-navy text-white text-xs font-bold hover:bg-lect-teal">Ir para o glossário <i class="ph-bold ph-arrow-down"></i></button>`}
            </div>`;
        try { w.bind(); } catch (e) { console.warn('widget', l.widget, e); }
        document.querySelectorAll('[data-go]').forEach(b => b.onclick = () => { open(b.dataset.go); $('ac-player').scrollIntoView({ behavior: 'smooth' }); });
        document.querySelectorAll('[data-opt]').forEach(b => b.onclick = () => answer(+b.dataset.opt));
    }

    function answer(i) {
        const l = current, right = i === l.quiz.a, fb = $('ac-qfb');
        document.querySelectorAll('[data-opt]').forEach(b => {
            const k = +b.dataset.opt; b.disabled = right;
            b.classList.remove('border-emerald-500', 'bg-emerald-50', 'border-rose-500', 'bg-rose-50');
            if (k === i) b.classList.add(right ? 'border-emerald-500' : 'border-rose-500', right ? 'bg-emerald-50' : 'bg-rose-50', 'dark:bg-transparent');
        });
        fb.classList.remove('hidden');
        fb.className = 'mt-3 p-3 text-sm border-l-4 ' + (right ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-500/10' : 'border-rose-500 bg-rose-50 dark:bg-rose-500/10');
        fb.innerHTML = right ? `<strong class="text-emerald-700 dark:text-emerald-400"><i class="ph-bold ph-check-circle"></i> Isso mesmo!</strong> ${l.quiz.why}` : `<strong class="text-rose-700 dark:text-rose-400">Ainda não.</strong> Releia “O essencial” e tente de novo.`;
        if (right && !state.done[l.id]) {
            state.done[l.id] = Date.now(); save(state);
            renderHero(); renderTrails(); renderSide();
            const t = trailOf(l.trail);
            if (doneCount(t.id) === lessonsOf(t.id).length) fb.innerHTML += `<div class="mt-2 font-bold" style="color:${t.color}"><i class="ph-fill ph-trophy"></i> Trilha “${t.title}” concluída!</div>`;
        }
    }

    function open(id) {
        const l = LESSONS.find(x => x.id === id) || LESSONS[0];
        current = l; state.last = l.id; save(state);
        renderTrails(); renderSide(); renderLesson();
        try { const u = new URL(location.href); u.searchParams.set('tab', 'academia'); u.searchParams.set('licao', l.id); history.replaceState(null, '', u); } catch (_) { }
    }

    /* ------------------------------------------------------------ GLOSSÁRIO */
    function renderGloss() {
        const q = (($('ac-gq') || {}).value || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
        const letter = renderGloss.letter || '';
        const items = GLOSS.slice().sort((a, b) => a[0].localeCompare(b[0], 'pt-BR'))
            .filter(([t, d]) => { const h = (t + ' ' + d).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, ''); return (!q || h.includes(q)) && (!letter || t[0].toUpperCase() === letter); });
        const letters = [...new Set(GLOSS.map(g => g[0][0].toUpperCase()))].sort();
        $('ac-gletters').innerHTML = ['', ...letters].map(L => `<button type="button" data-gl="${L}" class="w-8 h-8 font-bold ${L === letter ? 'bg-lect-navy text-white dark:bg-lect-teal' : 'bg-slate-100 dark:bg-lect-bgDark hover:text-lect-teal'}">${L || 'Tudo'}</button>`).join('').replace('w-8 h-8 font-bold', 'px-2 h-8 font-bold');
        $('ac-gl').innerHTML = items.length ? items.map(([t, d]) => `<div class="p-4 bg-slate-50 dark:bg-lect-bgDark border-l-4 border-lect-teal"><strong class="font-display">${t}</strong><p class="text-xs text-slate-600 dark:text-slate-300 mt-1 leading-relaxed">${d}</p></div>`).join('') : `<p class="text-sm text-slate-500 col-span-2">Nenhum termo encontrado.</p>`;
        document.querySelectorAll('[data-gl]').forEach(b => b.onclick = () => { renderGloss.letter = b.dataset.gl; renderGloss(); });
    }

    /* ------------------------------------------------------------ BOOT */
    function boot() {
        if (!$('ac-lesson')) return;
        const p = new URLSearchParams(location.search).get('licao');
        const start = (p && LESSONS.some(l => l.id === p.toUpperCase())) ? p.toUpperCase() : window.__acStart || state.last || LESSONS[0].id;
        renderHero(); open(start); renderGloss();
        $('ac-gq').addEventListener('input', () => { renderGloss.letter = ''; renderGloss(); });
        document.addEventListener('lx:macro', () => { if (current && (current.widget === 'cdi' || current.widget === 'mult')) renderLesson(); });
        if (p || window.__acStart) setTimeout(() => $('ac-player').scrollIntoView({ behavior: 'smooth' }), 300);
    }
    LX.academia = { lessons: LESSONS, open, glossary: GLOSS };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
