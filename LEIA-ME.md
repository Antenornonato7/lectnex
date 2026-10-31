# Lectnex Terminal — estrutura do site

```
index.html          Mercado Hoje: faixa B3, Leitura do Dia (IA), mapa de calor, indicadores, agenda, câmbio, mercados globais, notícias
macro.html          Macro & Juros: Copom, Focus, curva DI, regimes de risco, mapa "E se…?"
futuros.html        WIN, WDO e DI: Placar de vencimento (contagem até o último pregão), Plano do Dia (checklist, limite de perda, placar), Diário de Trades (curva, calendário, DARF automático), vencimentos, risco, Kelly, IR, dólar justo
acoes.html          Ações B3: cotação (brapi), gráfico (TradingView), painéis didáticos de fluxo/opções
sobre.html          Sobre o Lectnex: proposta, o que tem no terminal, princípios, newsletter e contato
laboratorio.html    Academia (trilhas, lições interativas, glossário) + simuladores
assets/
  lectnex-core.js   Núcleo: dados BCB/AwesomeAPI, calendário B3, vencimentos, cabeçalho/rodapé, busca
  lectnex.css       Estilos compartilhados
  lectnex-academia.js Lições, quizzes e glossário da Academia (edite o array LESSONS)
  tailwind.css      CSS compilado do Tailwind (gerado — não editar à mão)
  tailwind.src.css  Fonte do CSS do Tailwind
tailwind.config.js  Cores e fontes da marca; o workflow "Compilar CSS" recompila sozinho a cada push
```

Mantenha a pasta `assets/` junto dos `.html` ao publicar.

## CSS (Tailwind compilado)

O site não usa mais o Tailwind de testes (Play CDN). O estilo fica em `assets/tailwind.css`, gerado a partir das classes usadas nas páginas.
Ao mudar classes, recompile localmente com o Tailwind CLI 3.4.16:
`./tailwindcss -c tailwind.config.js -i assets/tailwind.src.css -o assets/tailwind.css --minify`
— ou apenas faça o push: o workflow **Compilar CSS** faz isso sozinho.

## Desempenho

- Widgets do TradingView carregam só quando chegam perto da tela.
- Últimos dados (Selic, CDI, IPCA, PTAX, câmbio) ficam guardados no navegador: a página abre preenchida e atualiza em seguida.
- Modo escuro é o padrão; o claro fica salvo para quem escolher.

## Configuração rápida

Em `assets/lectnex-core.js`, bloco `LX.config`:

- `brapiToken` — crie um token gratuito em brapi.dev. Sem ele, só PETR4, VALE3, ITUB4 e MGLU3 trazem cotação e faixa de 52 semanas.
- `fallback` — valores exibidos enquanto as APIs respondem (ou se falharem). Atualize após cada Copom/IPCA.

## Manutenção periódica

- `LX.copom2026`: preencha o resultado de cada reunião (ex.: `'13,50% (−0,25)'`) e acrescente o calendário de 2027 quando o BCB publicar.
- Agenda fixa em `assets/lectnex-core.js` (`LX.agendaFixed`, usada no Mercado Hoje e no Plano do Dia): eventos do mês (IPCA, payroll etc.). Vencimentos e Focus são calculados sozinhos.
- Feriados nacionais são calculados por regra (inclui Páscoa e 20/11). Feriados extraordinários precisam ser adicionados em `LX.b3Holidays`.

## Fontes de dados

| Dado | Fonte | Observação |
|---|---|---|
| Selic, CDI, IPCA | BCB SGS (séries 432, 4389, 13522, 433) | oficial |
| PTAX | BCB Olinda | oficial |
| Boletim Focus | BCB Olinda (ExpectativasMercadoAnuais) | oficial, semanal |
| Câmbio e cripto | AwesomeAPI | atualiza a cada 30 s |
| Ações | brapi.dev | atraso de até 15 min |
| Fundos donos e captação | CVM dados abertos (via coletor) | mensal / diário, licença ODbL |
| Estrangeiro em ações | BCB SGS 22927 | mensal |
| Gráficos, notícias, calendário global | Widgets TradingView | alguns símbolos B3 podem exigir licença no widget |

Taxas DI em tempo real, posições em aberto e fluxo por corretora são dados da B3 cuja republicação exige autorização — por isso o site usa dados abertos da CVM e do Banco Central no lugar (sem curva DI montada pelo usuário nem treinador de tape).

## Dados da CVM (fundos donos de cada ação e captação dos fundos de ações)

Os painéis "Quem é dono da ação" e "Captação líquida dos fundos de ações" leem arquivos gerados pelo coletor
`coletor/coletor_cvm.py`, a partir dos dados abertos da CVM (licença ODbL, que permite republicar citando a fonte).

Para ativar (uma vez só):

1. Crie um repositório no GitHub e envie todo o conteúdo desta pasta, incluindo `.github/` e `coletor/`.
2. Em **Settings → Pages**, publique a partir da branch `main` (pasta raiz). O site fica em `https://SEU-USUARIO.github.io/NOME-DO-REPO/`.
3. Em **Actions**, abra "Coletor CVM" e clique em **Run workflow** para gerar os dados pela primeira vez (leva alguns minutos).
4. Depois disso ele roda sozinho de terça a sábado às 07h17 (Brasília) e atualiza `data/*.json`.

Teste local: `python coletor/coletor_cvm.py --saida data` (precisa de internet; só biblioteca padrão do Python).

Fluxo estrangeiro em ações vem direto do Banco Central (série SGS 22927), sem coletor.

## Automação de dados

| Workflow | Quando | O que faz |
|---|---|---|
| Cotações B3 | a cada 30 min no pregão | `coletor/cotacoes.py` → `data/cotacoes.json` (faixa B3 + mapa de calor de hora em hora) |
| Coletor CVM | ter–sáb 07h17 | fundos donos e captação (`data/*.json`) |
| Compilar CSS | a cada push | Tailwind + recorte de ícones |
| Lighthouse | a cada push de código e às segundas | notas de velocidade, acessibilidade e SEO |
| Leitura do Dia | tarefa agendada no Claude, todo dia 07h40 | `data/leitura.json` (ver `docs/leitura-do-dia.md`) |

## Newsletter (Buttondown)

- Usuário: `lectnex` (em `LX.config.newsletter`, em `assets/lectnex-core.js`). Formulários: `<div data-lx-news="completo|compacto|chamada">`.
- Envio automático: workflow **Newsletter** (`coletor/newsletter.py`) quando a Leitura de um novo dia é publicada. Segredo `BUTTONDOWN_API_KEY` (ou `SITE_LECTNEX`). Se o Buttondown recusar o envio, cria rascunho para envio manual.
