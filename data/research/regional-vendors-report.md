# Relatório regional — depos e redes (Nova Odessa / Americana / Campinas)

Referência: CEP 13380-000. Gerado em 2026-09-17. Artefato só em `data/research/` (sem frontend).

## Como ler

- **Chains:** preços de `*-lowest-prices.json` (verificados no projeto).
- **Depos locais:** reputação de preço/comentários na web — quase sempre `reputation_only` (cotar antes de comprar).
- Score 0–100: preço (40) + sentimento (25) + cobertura vs 35 materiais (20) + logística até Nova Odessa (15).

## Ranking (resumo)

| #    | Local                                                                           | Tipo | Score | Por quê                                                                  |
| ---- | ------------------------------------------------------------------------------- | ---- | ----: | ------------------------------------------------------------------------ |
| 1    | Construeva (Americana)                                                          | depo |    86 | Mais comentários públicos citando preço baixo/bom + linha completa       |
| 2    | Sodimac                                                                         | rede |    84 | Mais wins de menor preço no catálogo do projeto (13) e 31/35 verificados |
| 3    | 333Obra                                                                         | rede |    78 | Cimento mais barato verificado (R$29); perto (Americana)                 |
| 4    | Depósito Ouro Verde (Campinas)                                                  | depo |    77 | Especialista em areia/pedra m³ (gap das redes)                           |
| 5    | Leroy Merlin                                                                    | rede |    74 | Melhores esquadrias/portas verificadas; RA marca ~6,9                    |
| 6    | Telhanorte                                                                      | rede |    72 | Bom meio-termo / promoções de básicos                                    |
| 7    | Depósito Brasil (Campinas)                                                      | depo |    70 | Reviews “preço acessível”; mais longe                                    |
| 8    | Feval (Americana)                                                               | depo |    68 | Marketing de preço + 2 lojas; poucas reviews                             |
| 9–15 | Casa dos Tijolos, Tayo, Alvorada, Ceron, Casa do Construtor, Pezão, Dep. Alemão | depo | 48–62 | Úteis para cotação/pickup; evidência web fraca                           |

## Baselines das redes (amostra verificada)

| Item            |         LM |    Sodimac | Telhanorte |   333Obra |
| --------------- | ---------: | ---------: | ---------: | --------: |
| Cimento 50kg    |      34,90 |      32,90 |      34,90 | **29,00** |
| Bianco ~18L     |     314,90 |     314,90 |     319,90 |         — |
| Porcelanato /m² |  **34,69** |      39,90 |      42,90 |         — |
| Tinta 18L       |     199,90 |  **99,90** |     149,90 |         — |
| Porta interna   | **307,30** |     634,00 |     365,42 |         — |
| Vaso            |     390,80 | **318,00** |     319,90 |    399,90 |

Cobertura verificada: Sodimac 31/35 · Telhanorte 30/35 · LM 23/35 · 333Obra 16/35.

## Gaps importantes

1. **Areia/pedrisco m³** — todas as redes `no_match` → cotar **Ouro Verde** (e similares).
2. **Cimento** — 333Obra lidera no verificado; depos locais podem ganhar no atacado (só com cotação).
3. **Esquadrias** — LM ainda é o baseline verificado.
4. **Depos dentro de Nova Odessa** — existem (Alvorada, Ceron, Casa do Construtor, Pezão) mas quase sem reviews/preços públicos; bons para retirada rápida, não como “mais barato comprovado”.

## Próximo passo operacional (para agentes)

1. Pacote de cotação WhatsApp: Construeva, Feval, Casa dos Tijolos, Ouro Verde (+ Alvorada/Ceron para top-ups).
2. Confrontar com winners Sodimac / 333Obra / LM / Telhanorte por `EXP_*`.
3. Só trocar o winner da rede se a cotação local for ≤ preço normalizado e especificação comparável.

Fonte estruturada completa: [`regional-vendors-report.json`](regional-vendors-report.json).
