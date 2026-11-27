# 0004 — Copernicus GLO-30 como fallback

- Data: 2026-11-27 · Estado: aceite

## Contexto
A aquisição do MDT DGT ficou bloqueada inicialmente. O jogo ainda estava plano.

## Alternativas
- Terreno plano para debug.
- Copernicus GLO-30 como DSM aproximado.
- DGT MDT 0,5 m como fonte prioritária.

## Decisão
Preservar o plano como fixture/debug e usar GLO-30 apenas como fallback. Preferir MDT DGT quando o pipeline de terreno estiver implementado.

## Consequências
O build GLO-30 passou 67/67 testes (5670 amostras, 81,5–284,9 m no recorte com margem). Não confundir DSM com DTM, não declarar integração na demo. [Evidência](../research/evidence-20261127.md). Atribuição Copernicus obrigatória.
