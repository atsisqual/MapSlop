# P1 — Alturas e reconstrução de edifícios (#7)

## Objetivo e fontes

Piloto de 527 footprints OSM. Os quatro pares de MDT/MDS de 0,5 m e quatro LAZ da mesma cobertura estão no rascunho geodata-dgt-pedome-20261127. Ver [inventário](research/release-assets-20261127.json). DGT documenta EPSG:3763/PT-TM06, datum altimétrico de Cascais, classes 2 (solo) e 6 (construção) e cobertura LiDAR 2024–2025: https://www.dgterritorio.gov.pt/atividades/cartografia/cartografia-topografica/modelos-digitais. Licença catalogada CC BY 4.0: https://dados.gov.pt/pt/datasets/dados-lidar-de-portugal-continental/. Não publicar derivados nesta tarefa.

## Decisão experimental

Alternativas: altura de pisos OSM (fallback), máximos MDS−MDT (sensíveis a árvores), percentis dentro de footprint, classificação LAZ e reconstrução integral. Começar pela diferença raster com p90; guardar p10/25/50/75/90/95, cobertura e fração de pixels plausíveis, altitude do terreno e teto absoluto. Preferir máscara interior afastada da borda de 0,5 m quando existem pelo menos 12 pixels, exigir 80% cobertura e 80% de diferenças plausíveis 0,5–80 m; intervalo p90−p10 acima do máximo de 3 m ou 60% da mediana sinaliza superfície heterogénea. Estes são limiares heurísticos sujeitos à primeira execução real, não tolerâncias de precisão certificadas. P90 estima altura total; cobertura vegetal e desencontro temporal OSM/LiDAR podem afetar a estimativa. Manter alturas explícitas OSM na prévia; restantes candidatos alteram apenas cópia OSM privada, com ID e proveniência. Não alterar fontes.

Roofer v1.0.0, ferramenta externa arquivada e verificada, não faz parte do runtime MIT. Reutilizar executável existente (ver https://innovation.3dbag.nl/roofer/cli_application.html). Escolher 20 footprints por quantis de altura, verificar quatro LAZ e CRS, agrupar numa fonte (diretório), classe 6 e 2; não fornecer altura de teto como fallback Roofer para não confundir extrusão com reconstrução. GeoPackage projetado criado por ogr2ogr, CityJSONSeq exportado sem código copyleft. Relatar ausência de features, geometrias LoD2.2, indicadores de sucesso/RMSE e val3dity disponíveis; geometria não equivale a sucesso topológico. A distribuição de LoD2.2 e revisão visual ainda não estão validadas.

## Workflow e aceitação

Executar manualmente:

```sh
gh workflow run pedome-terrain.yml --ref agent/dgt-building-heights -f mode=buildings
```

Verificar:
- 527 registos, razões de fallback, distribuição e 20 candidatos para inspeção.
- Igualdade do CRS, alinhamento, SHA-256 e cobertura por footprint.
- Build privado com alturas exportadas por OSM ID, TIN aprovada e browser/100 m de condução. Esta condução não prova colisões específicas de telhados.
- Roofer executado com inputs reais; analisar 20 resultados, contagem, falhas, RMSE e geometrias. Exportar e validar mesh/colli­sões no runtime numa etapa seguinte, mantendo fallback de extrusão. Inspecionar visualmente amostra com ortofoto.
- Não fechar #7 até testes, evidência e inspeção; não publicar dados ou releases. CI read-only usa apenas testes sintéticos; resultados reais ainda pendentes.

Decisões sobre estimador e integração são experimentais, não promessa de qualidade topográfica.
