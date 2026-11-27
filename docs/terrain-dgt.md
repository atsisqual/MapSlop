# P1 — Pipeline MDT DGT (issue #6)

## Estado

Implementação inicial em revisão. Nenhum MDT original foi lido nesta sessão; os testes sintéticos não demonstram cobertura, CRS real, precisão ou qualidade visual do DGT. Não publicar produtos DGT: a licença da coleção MDT continua por reconciliar. A demo P0 e o fallback Copernicus mantêm-se.

## Conversão

Entradas: quatro TIFF originais MDT 0,5 m v02, nomes e SHA-256 exatos no [inventário](research/release-assets-20261127.json), rascunho geodata-dgt-pedome-20261127. O script verifica bytes/hash, banda, CRS métrico comum, pixel 0,5 m norte acima, alinhamento e nodata. O envelope projetado do piloto tem de estar integralmente coberto sem pixels inválidos. Não se presume datum vertical sem metadados suficientes.

A grelha amostra o MDT por interpolação bilinear nos centros dos pixels, no referencial métrico do motor (mesmas constantes WGS84 do Nairobi; origem igreja). Alturas relativas à elevação na origem. Produtos estáticos 2, 5 e 10 m (1 m opcional); não há streaming/LOD dinâmico. O motor interpola os mesmos triângulos usados na malha, não a superfície bilinear original. O comparador verifica 100 pontos interiores determinísticos fora dos nós da grelha contra amostras bilineares do original. Aceitação do produto primário: erro máximo nesses pontos ≤1 m (não certifica todos os pontos nem a precisão de levantamento). Se falhar a 2 m, experimentar 1 m manualmente e registar resultado, não relaxar tolerância. O manifesto identifica resolução, CRS, cobertura, hashes, parâmetros, 100 erros por produto e dependências.

O adaptador aceita `--terrain-json`, substitui a grelha gerada pelo Nairobi sem aplicar o filtro DSM do Copernicus. Render, ruas e colisões reutilizam o módulo terrain.js. `--flat` e `--dem-json` continuam como antes. O produto de teste sintético é explicitamente identificado no HUD.

## Execução em cloud

Depois de integrar o PR: Actions → **Pedome DGT terrain private validation** → Run workflow (main). Ou:
```sh
gh workflow run pedome-dgt-terrain.yml --ref main -f primary_cell=2 -f archive=true
```
Só execução manual em main com acesso autorizado ao rascunho. Não utiliza segredos DGT nem publica Pages; não envia imagens ou grelhas para artefactos públicos. Se archive=true, guarda grelhas, manifesto e relatório de browser (quando disponíveis) numa **nova release em rascunho** com checksums; o rascunho pode conter resultados de falha, não é prova de validação. Não publicar sem autorização.

## Testes

CI de PR, sem dados DGT nem segredos: cinco testes unitários em raster sintético EPSG:3763, verificação dos hashes de entrada, resolução, nodata, grelha e interpolação; build não plano sintético e Chromium conduzindo e verificando proximidade do veículo ao terreno, além do P0 existente. Testes reais a executar via workflow manual. O teste de contacto aceita diferença até 1,5 m entre posição do veículo e a superfície amostrada (sanity check, não prova ausência de todos os problemas de colisão/ruas).

## Próximos passos

Registar no STATUS e evidência permanente o run real, CRS observado, cobertura, 100 erros agregados, grelhas/hashes, resultado de condução e limite de desempenho. Verificar visualmente os declives, pontes e edifícios; P1 prossegue com MDS−MDT. Não fechar #6 antes de completar os critérios.
