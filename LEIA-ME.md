# Lectnex Terminal — estrutura do site

```
index.html          Mercado Hoje: indicadores oficiais, agenda, câmbio, Focus, Copom, notícias
futuros.html        NOVA — WIN, WDO e DI: vencimentos, risco por operação, IR, dólar justo
acoes.html          Ações B3: cotação (brapi), gráfico (TradingView), painéis didáticos de fluxo/opções
laboratorio.html    Enciclopédia + simuladores (regras de IR de 2026)
assets/
  lectnex-core.js   Núcleo: dados BCB/AwesomeAPI, calendário B3, vencimentos, cabeçalho/rodapé, busca
  lectnex.css       Estilos compartilhados
  tw-config.js      Cores e fontes da marca para o Tailwind
```

Mantenha a pasta `assets/` junto dos `.html` ao publicar.

## Configuração rápida

Em `assets/lectnex-core.js`, bloco `LX.config`:

- `brapiToken` — crie um token gratuito em brapi.dev. Sem ele, só PETR4, VALE3, ITUB4 e MGLU3 trazem cotação e faixa de 52 semanas.
- `fallback` — valores exibidos enquanto as APIs respondem (ou se falharem). Atualize após cada Copom/IPCA.

## Manutenção periódica

- `LX.copom2026`: preencha o resultado de cada reunião (ex.: `'13,50% (−0,25)'`) e acrescente o calendário de 2027 quando o BCB publicar.
- Agenda fixa em `index.html` (lista `fixed`): eventos do mês (IPCA, payroll etc.). Vencimentos e Focus são calculados sozinhos.
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
