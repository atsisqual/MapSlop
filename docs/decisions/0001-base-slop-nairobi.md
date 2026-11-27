# 0001 — Slop Nairobi como base do motor

- Data: 2026-11-27 · Estado: aceite

## Contexto
Prioridade P0: condução livre em 3.ª pessoa nas ruas reais de Pedome, sem reescrever física/renderização.

## Alternativas
| Base | Testes | Notas |
|---|---|---|
| Slop Nairobi | 67/67 | Ruas arbitrárias, terreno, testes de condução/câmara/declives; mão esquerda |
| London Loop | 66/111 | Mais mecânicas (táxi, autocarro, tráfego); suite dessincronizada; mão esquerda |
| Slop Taipei | 9/9 | Mão direita; cobertura de testes pequena |

## Decisão
Nairobi para P0. London Loop/Wuhan como referência para missões e tráfego (P2). Nunca misturar dois runtimes nem duas versões de Three.js.

## Consequências
- Adaptar faixas/sinalização à circulação pela direita.
- Detalhe: `docs/research/upstream-test-results.md`, `docs/research/pedome-p0-validation.md`.
