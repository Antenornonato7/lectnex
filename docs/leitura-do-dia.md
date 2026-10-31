# Leitura do Dia — manual da tarefa automática

A seção "Leitura do Dia" (topo do Mercado Hoje, `index.html#leitura`) lê o arquivo `data/leitura.json`.
Uma tarefa agendada no Claude roda nos dias úteis antes do pregão, pesquisa o cenário, escreve esse arquivo e publica na `main`.
Se o arquivo faltar, estiver inválido ou tiver mais de 4 dias, a seção simplesmente não aparece.

## Passo a passo da tarefa

1. **Dia de pregão?** Use a data de hoje em Brasília (America/Sao_Paulo). Se for sábado, domingo ou feriado da B3
   (veja `LX.agendaFixed` em `assets/lectnex-core.js` e a regra de feriados nacionais em `LX.isBusinessDay`), não publique nada.
2. **Pesquise** (busca na web, fontes públicas e recentes — sempre do dia ou da noite anterior):
   - Fechamento de ontem e futuros de agora: S&P 500, Nasdaq, Treasury 10 anos, DXY, petróleo Brent, minério de ferro.
   - Ibovespa e dólar no fechamento de ontem.
   - Agenda de hoje no Brasil e nos EUA, com horário de Brasília (Copom, IPCA, payroll, CPI, falas do Fed/BCB, leilões do Tesouro).
   - Notícias que mexem com o Brasil: fiscal, política monetária, commodities, China.
   Também confira `LX.agendaFixed` e os vencimentos (WIN: quarta mais próxima do dia 15 dos meses pares; WDO: 1º dia útil do mês).
3. **Escreva `data/leitura.json`** no formato abaixo (UTF-8, JSON válido).
4. **Valide**: `python3 -c "import json;d=json.load(open('data/leitura.json'));assert d['data'] and 3<=len(d['resumo'])<=5"`.
5. **Publique**: commit `leitura: AAAA-MM-DD` na `main` e push. Não altere nenhum outro arquivo.

## Formato

```json
{
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
  "fontes": [
    { "titulo": "Nome do veículo — título da matéria", "url": "https://..." }
  ]
}
```

- `termometro.*.leitura` é o **viés do dia para o preço** do ativo: no WDO, `bullish` = dólar tende a subir.
- `exterior`: use `+` ou `−` no início da variação; até 6 itens. Pode ficar vazio se não houver dado confiável.
- `destaques`: até 4, em ordem de horário.
- `fontes`: 2 a 6 links reais que você abriu.

## Regras de conteúdo

- Português do Brasil, direto, para quem opera mini índice e mini dólar.
- **Educacional**: descreva cenário e riscos; nunca diga "compre", "venda", preço-alvo ou ponto de entrada.
- Só fatos verificados nas fontes do dia; se não encontrou um dado, deixe de fora em vez de estimar.
- Quando os sinais forem mistos, o termômetro é `neutro`.
