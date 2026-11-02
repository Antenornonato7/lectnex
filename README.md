# lectnex

Site estático do Lectnex Terminal (GitHub Pages). Estrutura e operação: [LEIA-ME.md](LEIA-ME.md).

## Plantão / FLASH (`data/plantao.json`)

O bloco **Plantão Lectnex** no Mercado Hoje (`index.html#plantao`, acima do feed TradingView) lê este arquivo. Para o próximo FLASH, edite só o JSON e publique. O HTML não muda.

```json
{
  "atualizado_em": "2026-11-02T09:37:00-06:00",
  "fuso": "America/Chicago",
  "aviso": "Plantão educacional. Não é recomendação de investimento.",
  "itens": [
    {
      "titulo": "Manchete em tom educacional, sem call de compra ou venda",
      "contexto": "Nota curta opcional. Ativos citados como contexto, não como ordem.",
      "fonte": "Nome da fonte",
      "url": "https://link-da-materia",
      "publicado_em": "2026-11-02T09:37:00-06:00"
    }
  ]
}
```

- `publicado_em` e `atualizado_em` são ISO-8601 com fuso. A página mostra esse horário em America/Chicago, com o rótulo CT.
- Cada card exige `titulo` e `url` http(s). `fonte` e `contexto` aparecem quando preenchidos. Sem itens válidos, o bloco fica oculto.
- A ordem do array é a ordem na tela (até 9 cards). O relógio do bloco é o do arquivo, não um “ao vivo”.
