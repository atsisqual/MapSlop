# 0003 — Mapa piloto e referencial Pedome

- Data: 2026-11-27 · Estado: aceite

## Contexto
A prioridade é conduzir numa área real antes de alargar a cobertura. O PBF nacional e extratos alargados não correspondem ao mapa publicado.

## Alternativas
- Importar toda a freguesia de uma vez.
- Usar área retangular pequena para testar geometria e desempenho; manter dados alargados arquivados.

## Decisão
Piloto S,W,N,E 41.4105,-8.395,41.4195,-8.383; origem igreja (41.41501,-8.38809, OSM way 149406360). x este, z sul, y cima, unidade metro. Mapa alargado W,S,E,N -8.405,41.405,-8.375,41.435 (~8,4 km²).

## Consequências
O piloto não representa a fronteira CAOP. Guardar BBOX e CRS em manifestos; preservar origem e orientação nos produtos futuros. Testar a posição real, não inventar coordenadas. [Estado](../STATUS.md).
