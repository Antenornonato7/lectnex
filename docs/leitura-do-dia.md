# Leitura do Dia — manual da tarefa automática

A seção "Leitura do Dia" (topo do Mercado Hoje, `index.html#leitura`) lê o arquivo `data/leitura.json`.
Uma tarefa agendada no Claude roda todos os dias às 7h40 (Brasília) — edição completa em dia de pregão e edição sem pregão nos fins de semana e feriados, pesquisa o cenário, escreve esse arquivo e publica na `main`.
Se o arquivo faltar, estiver inválido ou tiver mais de 4 dias, a seção simplesmente não aparece.

## Passo a passo da tarefa

1. **Dia de pregão?** Use a data de hoje em Brasília (America/Sao_Paulo). Veja `LX.agendaFixed` em `assets/lectnex-core.js`
   e a regra de feriados nacionais em `LX.isBusinessDay`.
   - **Dia de pregão** → edição completa: `"tipo": "pregao"`, com `termometro`.
   - **Sábado, domingo ou feriado da B3** → **edição sem pregão**: `"tipo": "sem-pregao"`, **sem** `termometro`, com
     `proximo_pregao` (data e o que esperar). Foque nas notícias das últimas ~24 horas que podem mexer na abertura do
     próximo pregão e na agenda desse dia. Se realmente não houver nada relevante, publique mesmo assim com 3 notícias
     de contexto e diga isso no resumo — nunca invente fato para preencher.
2. **Pesquise** (busca na web, fontes públicas e recentes — sempre do dia ou da noite anterior):
   - Fechamento de ontem e futuros de agora: S&P 500, Nasdaq, Treasury 10 anos, DXY, petróleo Brent, minério de ferro.
   - Ibovespa e dólar no fechamento de ontem.
   - Agenda de hoje no Brasil e nos EUA, com horário de Brasília (Copom, IPCA, payroll, CPI, falas do Fed/BCB, leilões do Tesouro).
   - Notícias que mexem com o Brasil: fiscal, política monetária, commodities, China. Selecione as 5 mais relevantes para `noticias`.
   Também confira `LX.agendaFixed` e os vencimentos (WIN: quarta mais próxima do dia 15 dos meses pares; WDO: 1º dia útil do mês).
3. **Escreva `data/leitura.json`** no formato abaixo (UTF-8, JSON válido).
4. **Valide** a leitura: `python3 -c "import json;d=json.load(open('data/leitura.json'));assert d['data'] and d['tipo'] in ('pregao','sem-pregao') and 3<=len(d['resumo'])<=5 and len(d.get('noticias',[]))>=3"`.
5. **Atualize `data/calendario.json`** (formato na seção "Calendário" abaixo): eventos de hoje até os próximos 7 dias corridos que
   mexem com WIN, WDO ou DI. Preencha `resultado` dos eventos que já saíram (só com o número oficial). Remova eventos antigos.
6. **Publique**: commit `leitura: AAAA-MM-DD` com **apenas** `data/leitura.json` e `data/calendario.json`, na `main`, e push.

## Formato

```json
{
  "tipo": "pregao",
  "data": "2026-11-03",
  "gerado_em": "2026-11-03T07:45:00-03:00",
  "titulo": "Frase curta que resume o dia (até 70 caracteres)",
  "resumo": [
    "3 a 5 frases curtas, cada uma com um fato e o porquê dele importar para WIN/WDO/DI.",
    "..."
  ],
  "termometro": {
    "win": { "leitura": "bullish | neutro | bearish", "motivo": "Uma frase com o principal motivo." },
    "wdo": { "leitura": "bullish | neutro | bearish", "motivo": "Uma frase com o principal motivo." }
  },
  "destaques": [
    { "hora": "9h", "evento": "IPCA de outubro (IBGE)", "por_que": "Mexe nos vértices curtos do DI." }
  ],
  "exterior": [
    { "ativo": "S&P 500 fut.", "variacao": "+0,4%" },
    { "ativo": "DXY", "variacao": "−0,2%" }
  ],
  "noticias": [
    {
      "titulo": "Manchete reescrita de forma objetiva",
      "fonte": "Nome do veículo",
      "hora": "07h10",
      "url": "https://...",
      "por_que": "Uma frase: por que isso importa para quem opera WIN/WDO hoje.",
      "impacto": { "win": "alta | baixa | neutro", "wdo": "alta | baixa | neutro", "di": "alta | baixa | neutro" }
    }
  ],
  "proximo_pregao": { "data": "2026-11-03", "o_que_esperar": "Só na edição sem pregão: 1–2 frases sobre o que pode pesar na abertura." },
  "fontes": [
    { "titulo": "Nome do veículo — título da matéria", "url": "https://..." }
  ]
}
```

- `tipo`: `pregao` ou `sem-pregao`.
- `termometro.*.leitura` é o **viés do dia para o preço** do ativo: no WDO, `bullish` = dólar tende a subir. Não use na edição sem pregão.
- `proximo_pregao`: obrigatório na edição sem pregão; omita em dia de pregão.
- `destaques`: na edição sem pregão, use a agenda do próximo pregão (com o dia na `hora`, ex.: `ter 9h`).
- `exterior`: use `+` ou `−` no início da variação; até 6 itens. Pode ficar vazio se não houver dado confiável.
- `destaques`: até 4, em ordem de horário.
- `noticias`: as 5 notícias (máx. 6) das últimas ~18 horas que mais mexem com WIN, WDO e DI. Prefira fatos (decisões, dados, números) a opinião. `impacto` = direção provável do preço do ativo por causa daquela notícia; omita o ativo se não houver efeito claro. A `url` precisa ser o link real da matéria que você abriu.
- `fontes`: 2 a 6 links reais que você abriu.

## Fontes

- **Fechamento do último pregão (uma fonte só, sempre a mesma):** Ibovespa pelo número oficial da B3 (b3.com.br) ou, na falta,
  pelo InfoMoney/Valor citando a B3; dólar à vista pelo fechamento do InfoMoney ou Valor (e a PTAX pelo Banco Central). Se a
  edição anterior já trouxe o fechamento do mesmo pregão, **repita os mesmos números** em vez de buscar de outra fonte.
- **Dados oficiais:** IBGE, Banco Central (BCB), Tesouro Nacional, BLS, BEA, Federal Reserve, ISM. Prefira o comunicado oficial.
- **Notícias, nesta ordem de preferência:** Valor Econômico, InfoMoney, Reuters, Bloomberg Línea, Folha, Estadão, O Globo,
  CNN Brasil, CNBC, Agência Brasil, Broadcast; no exterior, Reuters, Bloomberg, CNBC, AP, Financial Times, WSJ.
- **Evite** veículos com linha política declarada (de qualquer lado) e sites de opinião ou agregadores sem apuração própria.
  Se um fato só aparecer neles, procure a confirmação em um veículo da lista; sem confirmação, deixe de fora.
- Fato relevante com fonte única ou anônima (ex.: "autoridades disseram"): atribua sempre ("segundo a Reuters, …") e não o coloque
  sozinho no título.

## Regras de conteúdo

- Português do Brasil, direto, para quem opera mini índice e mini dólar.
- **Educacional**: descreva cenário e riscos; nunca diga "compre", "venda", preço-alvo ou ponto de entrada.
- Só fatos verificados nas fontes do dia; se não encontrou um dado, deixe de fora em vez de estimar.
- Quando os sinais forem mistos, o termômetro é `neutro`.

## Calendário (`data/calendario.json`)

Usado pelo painel "Calendário que mexe no WIN e WDO" no Mercado Hoje. Só eventos relevantes para mini índice, mini dólar e DI
(Copom e ata, IPCA/IPCA-15, PIB, varejo, produção industrial, CAGED, fiscal/leilões do Tesouro relevantes; EUA: payroll, CPI, PCE,
FOMC e falas do Fed, ISM, PIB; China: PMIs e dados de atividade; Europa: BCE e inflação). Feriados da B3 e vencimentos também entram.

```json
{
  "atualizado_em": "2026-11-03T07:45:00-03:00",
  "eventos": [
    {
      "data": "2026-11-06",
      "hora": "10h30",
      "pais": "US",
      "evento": "Payroll — criação de vagas (out)",
      "importancia": 3,
      "anterior": "180 mil",
      "consenso": "150 mil",
      "resultado": null,
      "impacto": { "wdo": "volatil", "di": "volatil" },
      "nota": "Emprego forte tende a fortalecer o dólar global.",
      "tipo": "payroll",
      "surpresa": null
    }
  ]
}
```

- `hora` em horário de **Brasília** (atenção ao horário de verão americano). `pais`: BR, US, CN, EU, JP, UK.
- `importancia`: 1 (baixo) a 3 (alto). `impacto` por ativo (`win`, `wdo`, `di`): `alta`, `baixa`, `neutro` ou `volatil` (direção depende do resultado).
- `anterior`, `consenso` e `resultado`: só valores confirmados em fonte; se não souber, `null`. Nunca estime número.
- De 8 a 25 eventos no total; ordem cronológica.
- `surpresa` (só depois que o `resultado` sai): `{"direcao": "acima" | "abaixo", "reacao": "1 frase sobre a reação típica de WIN/WDO/DI"}`
  quando o resultado ficar claramente fora do consenso (ex.: IPCA ≥ 0,1 p.p., payroll ≥ 50 mil, PMI ≥ 1 ponto, decisão de juros diferente do esperado);
  senão `null`. Eventos do dia com surpresa aparecem num alerta no topo do Mercado Hoje. A `reacao` descreve o padrão típico, nunca recomenda operação.

## Rodadas de resultado (dias úteis)

Além da edição das 7h40, a tarefa "Resultados do calendário" roda às 12h40 e às 16h40 (Brasília) nos dias úteis.
Ela **só** mexe em `data/calendario.json`: preenche `resultado` e `surpresa` dos eventos de hoje que já saíram (número oficial
da fonte primária ou de veículo confiável) e publica com o commit `calendario: AAAA-MM-DD HHhMM`. Não altera mais nada.
- `tipo`: identificador fixo do indicador, igual em todas as edições (alimenta a "reação histórica"). Use estes quando couber:
  `payroll`, `desemprego-eua`, `salario-eua`, `cpi-eua`, `pce-eua`, `pib-eua`, `ism-industrial`, `ism-servicos`, `jolts`, `adp`,
  `seguro-desemprego`, `fomc`, `ipca`, `ipca-15`, `pib-brasil`, `copom`, `ata-copom`, `caged`, `varejo-brasil`, `producao-industrial`,
  `pmi-china`, `cpi-china`, `bce`, `inflacao-zona-euro`, `boe`. Para outros, crie um identificador curto em minúsculas com hífens e repita sempre o mesmo.
