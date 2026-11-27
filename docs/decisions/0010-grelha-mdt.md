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


## Revisão 3 — substituir a regra de fallback e o formato de transporte

O run 46055620274 mostrou que o fallback tinha uma exceção indevida: 2 m máximo nas estradas 1,412378 m, TIN 0,586453 m. Ambos excedem 0,5 m; nenhum é aprovado pela regra atual. TIN: 90 284 vértices, 180 007 faces, 4 950 736 bytes JSON; grelha 2 m: 252 506 vértices, 503 004 faces, 1 812 236 bytes. Ambos passaram 104 m e contacto 0,03 m na Rua das Bouças. [Evidência](../research/dgt-terrain-tin-evidence-20261127.json).

Decisão: aplicar os mesmos limites de precisão (máximo ≤0,5 m nos 100 pontos e nas estradas) e condução aos candidatos próximos, sem exceção para fallback. TIN mantém orçamento <150k e avaliação nos nós locais ≤0,5 m. Se nenhum passar, falhar workflow e não emitir default. LOD distante continua por RMSE. Manter 2 m só se realmente passar, com custo já registado.

Alternativas de transporte: JSON, glTF/meshopt, binário Float32 ou quantização Uint16. Escolher MSLTERR1: cabeçalho JSON pequeno embutido, Float32 LE para XYZ/alturas e Uint32 LE para índices explícitos da TIN; grelha tem índices implícitos. Evita introduzir erro relevante de quantização e permite leitura direta no browser. Medir bruto/gzip nível 9 mtime=0 e equivalentes JSON, com SHA-256; não afirmar gzip servido por HTTP. Testar round-trip, corrupção e render/drive sobre o binário. Quantização/meshopt fica alternativa posterior se tamanho ou memória ainda excessivos.

Alternativas de refinamento: Delatin global mais fino (custo), linhas de quebra constrained (complexidade), seleção de vértices fina junto a eixos OSM. Escolher base 0,25 m + pool 0,15 m, seleção em raio 6 m dos eixos amostrados, retriangulação SciPy 1.15.3 Delaunay/Qhull (BSD, commit e29dcb65a2040f04819b426a04b60d44a8f69c04). Acrescentar pontos MDT reais em resíduos, até cinco rondas e 149 999 vértices. Não é mesh com breaklines obrigatórias; medir resultado final em todos os nós de 0,5 m locais e corredores OSM, além dos 100 pontos, porque a retriangulação pode alterar faces. A metadata library_error_m descreve apenas Delatin base; raster_max_abs_m descreve a malha refinada. Reportar 10 maiores erros rodoviários com way e coordenadas. Não densificar indefinidamente para compensar taludes/muros/pontes; avaliar perfis próprios de estrada numa tarefa futura, com evidência.

Resultado real da revisão ainda pendente. Sem autorização para publicar, sem subtree. O teste Android físico continua necessário; o tamanho do ficheiro não prova memória/FPS.

## Resultado aprovado (run 46056885609)

TIN selecionada: 100800 vértices, 201015 faces, 3622880 bytes bruto, 1966866 gzip; máximo 0,201276 m/100 pontos, 0,350236 m/70627 probes rodoviários, 0,429646 m/4020009 nós locais. Condução 104,219550 m, contacto 0,03 m, zero colisões, CI sintético success. Grelha 2 m rejeitada por máximo rodoviário 1,412379 m. [Evidência permanente](../research/dgt-terrain-final-evidence-20261127.json). PR #15 integrado, #6 concluída; formato/compressão, monotonicidade, primary_pass e hardware físico são seguimentos #16–19. Usar terrain-tin.bin do rascunho; alias terrain-default.json observado contém binário idêntico. Não publicar.
