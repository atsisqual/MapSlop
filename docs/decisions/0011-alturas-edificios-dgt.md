# 0011 — Alturas MDS−MDT e ensaio Roofer

- Data: 2026-11-27 · Estado: proposta experimental (issue #7)

## Decisão

Medir percentis da diferença MDS−MDT nos footprints OSM, com máscara interior, indicadores de cobertura e heterogeneidade, e conservar fallback existente quando não houver suporte. Preservar alturas OSM explícitas. Alternativas: níveis estimados, máximo raster (sensível a árvores), classe 6 isolada ou reconstrução integral imediata. O percentil 90 é um candidato de altura total, não uma medida certificada de fachada. Ver [critérios e workflow](../buildings-dgt.md).

Reutilizar Roofer 1.0.0 como ferramenta offline separada para vinte footprints e quatro LAZ verificados. CityJSONSeq é o produto experimental; não incluir código copyleft no runtime. Comparar qualidade e resultados antes de converter telhados em meshes e colisões do jogo. CI sintético e execução real pendentes; nenhum dado publicado.
