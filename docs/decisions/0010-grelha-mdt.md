# 0010 — Grelha MDT no referencial do motor

- Data: 2026-11-27 · Estado: aceite para implementação experimental

## Contexto
O MDT DGT já está arquivado, mas o motor Nairobi tem um filtro DSM e grelha fixa de 25 m. Aplicá-lo ao MDT perde detalhe e pode alterar terreno já classificado como solo.

## Alternativas
- Reusar o filtro GLO-30 no MDT.
- Converter diretamente o MDT para a grelha do motor.
- Migrar para terrain streaming/3D Tiles ou subtree desde já.

## Decisão
Conversão offline com rasterio, amostragem bilinear no CRS de origem e grelhas estáticas 2/5/10 m (1 m opcional). Preservar eixo/origem do motor, base na igreja, interpolação triangular. Carregar JSON no adaptador sem filtro DSM. Comparar 100 pontos interiores com fonte, tolerância de 1 m no produto primário. Manter fallback anterior. Não executar subtree nem streaming nesta tarefa.

## Consequências
LOD estático não é seleção dinâmica; malha fina aumenta vértices, memória e custo de render. Verificar limites em dispositivo real. Produtos DGT só em rascunho enquanto licenças e autorização estiverem pendentes. Testes de raster sintético são apenas testes do código; dados reais carecem de workflow manual e evidências. Ver [pipeline](../terrain-dgt.md).

## Revisão pré-merge

Comparar 2 m e 5 m com os mesmos quatro TIFF, 100 pontos e tolerância de 1 m. Registar MAE, RMSE, máximo, vértices, bytes/hash, distância e contacto. Limite de contacto 0,5 m, amostrado por frame contra MDT e superfície de colisão. Se 2 m ultrapassar 150 000 vértices, usar 5 m como padrão desde que ambos passem; 2 m mantém-se opção. Um rascunho de derivados por branch. Teste Android físico com FPS e memória pendente. Sem merge até dados reais passarem.


## Revisão 2 — TIN adaptativa (decisão substitui a seleção 2/5 m anterior)

O run 46053111254 demonstrou 2 m: 252 506 vértices, 503 004 triângulos, 1 812 236 bytes, máximo 0,430891 m, MAE 0,041068 m, RMSE 0,085677 m; 5 m: 41 006 vértices, 294 403 bytes, máximo 1,192319 m, MAE 0,109483 m, RMSE 0,220535 m; 10 m: 10 404 vértices, 74 841 bytes, máximo 1,820113 m, MAE 0,226085 m, RMSE 0,385827 m. Condução curta 2/5 m: 2,025589/2,101722 m, contacto 0,03 m, 35 amostras em cada, contacto com superfície de colisão 0. A regra anterior rejeitou 5 m e o run falhou. [Evidência imutável](../research/dgt-terrain-grid-evidence-20261127.json).

Alternativas: grelha 2 m (custo já conhecido), simplificar para 5 m (perde detalhe local), Martini ou Delatin. Escolher pydelatin 0.4.0 (MIT, fonte [tag v0.4.0](https://github.com/kylebarron/pydelatin/tree/e281368a62429a47686c1e21786678cc5213fcb1)); execução offline, sem nova dependência de triangulação no browser. Reamostra MDT 0,5 m em grelha local; erro interno 0,25 m (margem para interpolação fora dos nós) e cap 149 999 vértices. Aprovar TIN só se erro máximo ≤0,5 m nos 100 pontos e nos corredores OSM, biblioteca ≤0,5 m e <150k vértices, com condução longa aprovada. Se falhar, manter grelha 2 m como fallback, com custo acima (cerca de 2,5× o orçamento de 100k; 1,68× 150k) e erro rodoviário medido; continua sujeita a teste longo e critério anterior ≤1 m nos 100 pontos. Distant LOD 5/10 m avaliados por RMSE (metas provisórias 0,35/0,60 m, sem bloquear produto próximo); não há ainda seleção dinâmica. O runtime renderiza e interpola as mesmas faces e corta as superfícies rodoviárias sobre elas. Condução ≥100 m com declive ≥2% ao longo de 20 m, curva real ≥15°, contacto ≤0,5 m em cada passo, sem colisão reportada. Passo fixo 1/60 dentro de Chromium; não prova FPS em hardware.

Resultado de TIN e novo teste real pendentes; sem escolha final ou merge. Se passar, alias terrain-default.json escolhido por workflow. Android físico e licenças continuam pendentes.
