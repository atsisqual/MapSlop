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

## Segunda etapa — edifícios realistas, após validar PR #26

1. **Geometria:** conservar o OSM ID e proveniência por edifício. Roofer LoD2.2 → CityJSONSeq → CityJSON por conjunto, depois exportação GLB com cjio (a documentação confirma exportação glTF binário: https://cityjson.github.io/cjio/includeme.html). Usar a versão arquivada e verificar hash, sintaxe CLI, transformações CityJSON (scale/translate), CRS, eixos e unidades com três pontos de controlo. Exportar apenas geometrias aprovadas; não copiar ferramentas GPL/AGPL para runtime. Se não houver geometria válida, preservar roof:shape OSM suportado; caso contrário telhado procedural 2 águas para footprints alongados, 4 águas para compactos, plano para tipologias industriais explicitamente identificadas. Não afirmar telhados procedurais como medidos.
2. **Implantação:** amostrar TIN ao longo de todos os lados do footprint e interior (máx. 0,5 m); guardar mínimo/máximo, desnível e base. Fundação/plinto desce até à cota mínima; paredes habitáveis começam numa plataforma coerente acima do terreno local, fundação exposta acompanha o declive. Preservar cotas absolutas de telhado Roofer; se a geometria implicar paredes enterradas ou altura impossível, sinalizar e usar fallback explícito. Testar casas em talude, nenhuma abertura visível debaixo da fundação, portas acessíveis quando possível.
3. **Fachadas:** materiais procedurais deterministicamente derivados do ID (reboco branco/creme, pedra em soco, telha cerâmica, caixilharias e portas; pisos 2,8–3 m). Instancing por material/LOD para janelas e portas, varandas simples apenas quando compatíveis com tipologia e espaço. Cores de telhado opcionais: amostrar mediana robusta da ortofoto de 25 cm dentro da cobertura, excluir sombra/vegetação, conservar licença/proveniência e usar paleta fallback. Não inferir detalhes de uma fachada real apenas por LiDAR.
4. **Completar footprints:** recortar o [Mapa de Construções LiDAR 2024](https://dados.gov.pt/pt/datasets/mapa-de-construcoes-lidar-2024), verificar licença e hash antes de arquivar. Classe 6 não é exclusivamente edifícios; área mínima 10 m² e possíveis polígonos unidos. Complementar somente quando não houver sobreposição material com OSM: rejeitar duplicados quando a interseção sobre o menor polígono for ≥50%; candidatos novos exigem ≥90% da área fora da união de OSM com buffer 0,5 m; casos intermédios e estruturas não habitáveis vão para revisão, não adicionar automaticamente. Registar IDs separados DGT, contagens e razões. Não alterar OSM original.
5. **Orçamento experimental do piloto:** ≤120 mil triângulos em cascas/telhados (todos os edifícios), ≤250 mil triângulos de edifícios visíveis incluindo instâncias no LOD próximo, ≤3 MB gzip para geometria e atributos derivados (incremental ao terreno), ≤1 MB no primeiro carregamento de LOD, ≤40 draw calls dedicados a edifícios, janelas instanciadas e fachadas simplificadas à distância. Colisões por caixas ou cascos convexos simples/união curta, separados de detalhe visual, sem malhas ornamentais. Medir contagens reais, tamanho, tempo de carregamento, FPS e memória; meta móvel ≥30 FPS mediana em 5 minutos de teste físico, não assumir antes da issue #19. Ajustar mediante evidência, não relaxar automaticamente.
6. **Aceitação:** inspeção de pelo menos 20 edifícios (incluindo igreja, habitações e pavilhões, mais casos de falha), cobertura e plausibilidade de alturas/roof/fundação, comparação ortofoto, teste de contacto e colisão de fachadas; publicar apenas em PR separado autorizado. Nenhum destes passos está executado até validar #26.
