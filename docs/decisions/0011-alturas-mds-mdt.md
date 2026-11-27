# 0011 — Alturas dos edifícios por MDS−MDT

- Data: 2026-11-27 · Estado: aceite para implementação experimental
- Issue #7, primeira fase (alturas; não reconstrução LoD2)

## Contexto e alternativas

A TIN do MDT 0,5 m foi aprovada em privado no run 46056885609. O motor usa sobretudo alturas estimadas ou pisos OSM. Alternativas: manter estimativas, medir MDS−MDT nos footprints, reconstruir telhados com Roofer/LAZ. Escolher estatísticas raster como primeira fase; Roofer fica para a segunda.

## Decisão

Usar os footprints efetivamente renderizados, com buracos, e SHA-256 de tipo/ID OSM, ring e holes. Conferir os oito TIFF por tamanho/hash, CRS EPSG:3763, pixel 0,5 m, banda e alinhamento de pares/mosaicos. Shapely 2.1.1 (BSD-3-Clause, [commit](https://github.com/shapely/shapely/tree/b49155ea7eaec698a0357fb9bc1147533b566916)), rasterio e NumPy offline.

Amostrar centros de pixels num inset de 0,5 m, excluindo nodata de ambos os rasters e pátios. Guardar P10/P50/P75/P90 de MDS−MDT, P75 absoluto MDS, mediana MDT, contagem e cobertura. Limiares heurísticos: ≥8 amostras válidas, ≥80% cobertura, ≥80% deltas ≥1 m, P75 delta entre 1,5 e 60 m, P90−P10 ≤max(3 m,0,8×P75). Partes/pódios/elevados, footprints inválidos/fora da TIN, inset vazio, amostras insuficientes, cotas implausíveis e conflitos fortes com informação OSM mantêm altura anterior com motivo.

Altura nominal = P75 delta. Cota plana de telhado = P75 MDS absoluto menos base da TIN; altura de render = essa cota menos footing real do motor (mínimo nos vértices do anel), entre 1,5 e 80 m. Preservar altura OSM não estimada se divergir mais de max(3 m,35%). Usar a mesma altura em geometria/colisões e suprimir parapeitos e casotas artificiais nos edifícios medidos.

## Consequências

Estimativa observacional LoD1, não levantamento de paredes nem geometria real de telhados. Rever limiares após dados reais e inspeção de 20 casos. Provar coerência geométrica e colisões no browser; amostra automática não substitui inspeção visual. Roofer/LAZ fica fase seguinte. Dados e resultados reais só em rascunho enquanto licença e autorização pendentes. Ver [pipeline](../building-heights.md).
