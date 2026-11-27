# P1 — Pipeline MDT DGT (issue #6)

## Estado

O run manual 46053111254, commit `b95df198c277fdf9509f94f58f63592854766d7a`, verificou os quatro TIFF reais, CRS EPSG:3763, 4 040 084 pixels no envelope projetado e zero inválidos. 2 m passou o critério antigo, 5 m falhou apenas no máximo dos 100 pontos. [Evidência persistente](research/dgt-terrain-grid-evidence-20261127.json). Nova TIN e condução longa em revisão; não foram ainda validadas com DGT. A demo P0 e o fallback Copernicus mantêm-se. Não publicar produtos DGT sem resolver a licença e obter autorização.

## Conversão

Entradas: quatro TIFF MDT 0,5 m v02, nomes e SHA-256 no [inventário](research/release-assets-20261127.json), rascunho geodata-dgt-pedome-20261127. O script verifica bytes/hash, banda, CRS projetado métrico comum, pixel 0,5 m norte acima, alinhamento, cobertura e nodata. Não se presume datum vertical sem metadados suficientes.

Amostragem bilinear nos centros dos pixels do MDT original, no referencial métrico do motor (WGS84 Nairobi; origem igreja; x este, z sul). Alturas relativas à elevação na origem. Grelhas regulares de 2/5/10 m (1 m opcional) e TIN adaptativa. A TIN usa **pydelatin 0.4.0 (MIT, Kyle Barron, [v0.4.0](https://github.com/kylebarron/pydelatin/tree/e281368a62429a47686c1e21786678cc5213fcb1))**, wrapper do hmm; não implementamos triangulação. Reamostra o MDT original para uma grelha local de 0,5 m em blocos, margem de erro interna 0,25 m e limite 149 999 vértices. A margem não é garantia: valida a malha exportada nos pontos de avaliação. A transformação de orientação e os valores dos vértices são conferidos; faces com área nula, índices inválidos e área total incorreta são rejeitados. Se a TIN falhar na geração, conservar grelhas e registar a exceção. Não trocar por uma malha cuja precisão não tenha sido testada.

O motor usa os próprios vértices e índices da TIN no Three.js e na pesquisa baricêntrica de altura e normal. O adaptador separa polígonos do asfalto, passeios e muros pelas faces reais da TIN; não renderiza uma grelha independente. A grelha regular permanece inalterada. `--terrain-json` carrega o formato escolhido, sem filtro DSM. `--flat` e `--dem-json` continuam disponíveis. Os produtos sintéticos têm HUD explicitamente identificado.

## Métricas e aceitação

- 100 pontos interiores determinísticos fora dos nós, comparando as alturas absolutas com o MDT original por amostragem bilinear. Complemento: vias de superfície OSM, centro e dois corredores laterais de ±1,5 m, espaçamento máximo 0,5 m dentro do piloto; excluem-se viadutos, túneis e outros layers. Não são uma medição topográfica das bermas. Relatar contagem, máximo, MAE e RMSE, vértices/triângulos, bytes e SHA-256 para cada produto.
- TIN: menos de 150 000 vértices, erro máximo ≤0,5 m nos 100 pontos e nos corredores rodoviários amostrados, erro indicado pela biblioteca ≤0,5 m. Tem de passar a condução. Não equivale a limite certificado contínuo em todos os pontos; a amostragem pode omitir extremos.
- Se TIN não cumprir, fallback 2 m: máximo ≤1 m nos 100 pontos (critério anterior), condução aprovada, registar também erro nas estradas e custo de 252 506 vértices/503 004 triângulos observado. Nenhum produto de proximidade é selecionado sem teste.
- 5 e 10 m são candidatos a LOD distante, avaliados por RMSE (metas provisórias de 0,35 e 0,60 m, respetivamente), não bloqueiam a solução próxima. A seleção dinâmica de LOD/streaming ainda não existe.
- Teste Chromium curto continua a validar render, teclado e multitoque. Teste longo: escolhe via OSM nomeada de superfície com largura ≥5,5 m, percurso interior de 120 m, declive mínimo 2% num intervalo de 20 m e curva de pelo menos 20° no traçado. Testa até cinco candidatos por ordem determinística, regista tentativas; usa a rota aprovada na grelha 2 m para a TIN quando disponível. Segue os comandos analógicos e o controlador/colliders reais com passos fixos de 1/60 s, sem alterar posição durante a condução; só teleporta no início de cada tentativa. Isto é teste de física acelerada dentro do browser, não benchmark de FPS. Requer distância e progresso ≥100 m, mudança real de direção ≥15°, zero colisões reportadas, permanência no corredor, diferenças máximas ≤0,5 m com o terreno e a superfície de colisão amostradas a cada passo. Guarda amostras e agregados. Render antes e após o percurso.
- `validation.json` (schema 2) regista resultados e `recommended_default_file`; se houver candidato próximo aprovado, o workflow cria `terrain-default.json` byte-idêntico ao selecionado. Este é o produto próximo por omissão para builds experimentais autorizados, **não** para o Pages público. Sem aprovação, não existe alias. Usar `--terrain-json caminho/terrain-default.json`.

## Execução em cloud

Antes do merge, usar o workflow manual já registado **Pedome real terrain fallback**, branch agent/dgt-terrain-grid, mode=dgt. Este chama o workflow reutilizável DGT. Não há triggers automáticos.

```sh
gh workflow run pedome-terrain.yml --ref agent/dgt-terrain-grid -f mode=dgt
```

Uma execução gera e compara as grelhas e TIN, testa os candidatos próximos 2 m e TIN em Chromium e seleciona o melhor aprovado. Só nos branches autorizados e com acesso ao rascunho; sem segredos DGT nem Pages. Uma única release em rascunho por branch, clobber restrito aos assets de evidência; `validation.json`, manifesto, grelhas, logs e checksums. Guardar as métricas históricas no Git antes de substituir assets. Um rascunho pode conter resultados de falha, não é prova de validação. Não publicar sem autorização.

## Testes e próximos passos

CI read-only usa raster e malha sintéticos, testes de orientação e interpolação, regra de seleção e fallback, build/render/drape de TIN e teste longo. Não confundir CI com teste real DGT. Registar novo run, SHA-256, cobertura, métricas e motivo de seleção no STATUS e ADR 0010 antes de merge. Android real: 5 min, FPS mediana/percentil baixo, pico de memória/método e comparação com fallback; pendente. Não fechar #6 antes de critérios. Subtree não executado.
