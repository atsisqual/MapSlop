# Estado do projeto

> Atualizado em 2026-11-27. Fonte de verdade para retomar o projeto; ler primeiro [AGENTS](../AGENTS.md). O histórico de investigação não substitui este estado.

## Fase atual: P0 — condução livre em Pedome

- Motor: Slop Nairobi `64b8599ae7dd7ba56ffbe68f19cc1423a9e7f903`, Three.js `f17eb5d689094a3fbd4cd0d64d54729a48036ce0`. Adaptador `tools/prepare-pedome.py`, sem código/dados de PortoSlop. Londres/Taipei são referências; ver [investigação](research/reuse-audit.md).
- Piloto WGS84 S,W,N,E `41.4105,-8.395,41.4195,-8.383`, origem na igreja `41.41501,-8.38809` (OSM way 149406360). 1 208 elementos OSM, 179 registos de vias, 527 edifícios (511 alturas estimadas), 113 nós, 134 links. Área alargada W,S,E,N `-8.405,41.405,-8.375,41.435` (~8,4 km²), não confundir com piloto.
- Demo: https://atsisqual.github.io/MapSlop/ e `mobile.html?webgl`. HUD tátil, minimapa norte acima, igreja, rua mais próxima e reposição. Testes Chromium desktop e multitoque emulado passaram; não há teste num telemóvel físico registado. Utilizador reportou que versão inicial não mostrava botões; entrada versionada e verificação pública introduzidas. Relevo publicado plano.
- Arquivo: originais em Releases em rascunho, acessíveis com token/permissão de escrita. **Não publicar sem autorização.** [Inventário por ficheiro com SHA-256](research/release-assets-20261127.json) e [evidência dos testes](research/evidence-20261127.md).
- Copernicus GLO-30: build alternativo concluído (5 670 amostras, 81,5–284,9 m no recorte com margem); DSM aproximado, não DTM de 0,5 m. Artefacto temporário, não integrado na demo nem preservado como original permanente. Pode ser reobtido pelo workflow.
- DGT `geodata-dgt-pedome-20261127`: 15 ficheiros, 222723518 bytes MDT 0,5 m; 15 ficheiros, 230314564 bytes MDS 0,5 m; 15 ficheiros, 15237327 bytes MDT 2 m; 15 ficheiros, 15443335 bytes MDS 2 m; 15 ficheiros, 1902990934 bytes LAZ; 2 ficheiros, 1102550931 bytes ortofotos atuais 25 cm. LAZ anteriormente falhou por allowlist de redirecionamento; recuperado. `geodata-dgt-history-20261127`: 16 ficheiros, 3588836327 bytes (1995–2021, duas folhas por cobertura).
- OSM nacional 429 648 916 bytes e extrato alargado guardados; vetores OGC: 8 freguesias, 239 COS2025, 86 CRUS, 2 municípios, **0** objetos cadastro (não é cobertura cadastral). CAOP/COS do piloto no Git.
- Toolchain `reconstruction-toolchain-20261127`: sete ZIPs byte-idênticos e binário Roofer v1.0.0, 0 ficheiros, 0 bytes. `roofer --help` executado com sucesso em Linux; não reconstruímos ainda edifícios reais. Outras ferramentas não executadas.
- README, MIT/avisos upstream, .gitignore e CLAUDE.md (symlink) integrados no PR #2. PR #1 integrou governação; ver [proposta](PROPOSTA-PROCESSO.md).

## Histórico e problemas encontrados

- PortoSlop: HAR e resposta /api/map foram analisados para compreender formato, física, streaming e funcionalidades; apenas notas e contagens, nenhum bundle/asset redistribuído. O servidor original não foi inspecionado. [Auditoria](research/portoslop-client-audit.md) e [formato](research/portoslop-map-format.md).
- Overpass indisponível/limitado, exportação XML manual utilizada; removidos UID, nomes de utilizador, changesets e timestamps individuais no extrato. Build fixture não prova geografia real. Testes upstream London 66/111, Taipei 9/9, Nairobi 67/67. Browser local bloqueado por política de acesso; validação via Actions. Primeiro runner incompatível com Playwright; Ubuntu 24.04 resolveu. GL_INVALID_OPERATION devido a MRT de material no render direto; removido MRT nesse percurso; teste passou após esperar deslocação efetiva.
- Inicialmente CDN e teste em PC/teclado; publicados módulos Three fixados e HUD tátil. Teste real em hardware móvel continua em falta.
- Índices DGT enviados eram GeoPackages, não os rasters. Pesquisa GET bbox devolvia nacional; POST /search por coleção e bbox resolveu. Orto direta HTTP 403 sem sessão. Primeiro cliente rejeitava redirecionamentos válidos: stor-002.a.acnca.pt para MDT/MDS, stor-001.a.acnca.pt para LAZ. Login normal por credenciais em Actions secrets DGT_USERNAME/DGT_PASSWORD (nunca no Git), validado pelo download de TIFF/LAZ. Browser externo não foi usado após falha de saldo. Guardar apenas domínios e metadados, nunca cookies/URLs assinados.
- Recolha DGT inicial parcial: 62 rasters arquivados, 15 LAZ falharam, retry LAZ posteriormente sucesso. Orto histórico e reconstrução concluídos. Todos os digests publicados pela API de releases foram capturados no Git. Acesso sem token continua bloqueado.
- Prioridade expressa: cloud/GitHub, sem depender de computador do utilizador; reconstrução geográfica antes de missões; reutilizar ferramentas existentes, guardar originais e detalhes.
- Candidatos de reconstrução: Roofer, City4CFD, 3dfier, BlenderGIS, OSM2World, cjio e City3D. GPL/AGPL offline separado, exportação de geometria sujeita à licença dos dados; inventariar dependências e não copiar código para runtime.

## Em aberto / conhecido como incompleto

- Faixas/pintura ainda orientadas à esquerda, relevo DGT ainda não integrado, alturas e telhados não reconstruídos, vegetação/ortofotos não integradas.
- Inventário completo de assets upstream por concluir; licenças por coleção DGT inconsistentes (MDT STAC proprietary, MDS CC BY 4.0, ortofoto public; documentação institucional aberta). Confirmar direitos específicos antes de publicar; autorização do utilizador obrigatória.
- Cadastro OGC zero resultados; Mapa de Construções LiDAR identificado, não descarregado; não prometer cobertura.
- Não foram executados Roofer com Pedome, City4CFD nem pipeline de reconstrução. Não afirmar desempenho móvel nem qualidade geométrica.
- Workflows antigos duplicados e acionados por push, ambiente incompleto e issues por criar. Subtree ainda só proposta futura; não executar nesta reorganização.

## Próximos passos (por prioridade)

1. Integrar MDT DGT 0,5 m → terreno do jogo (substituir GLO-30).
2. Alturas de edifícios via MDS−MDT por footprint OSM.
3. Circulação pela direita: faixas, pintura, rotundas.
4. Árvores/vegetação a partir de LAZ (classes 3–5) e COS2025.
5. Ortofoto como textura de solo (tiles com LOD).

## Bloqueios

- Distribuição pública de originais: releases rascunho, autorização ainda não dada; discrepâncias de licenças requerem esclarecimento. Agentes sem permissões de escrita não conseguem descarregar; pedir ao mantenedor acesso autorizado, nunca pedir credenciais em chat.
- Não há pipeline DGT→runtime implementado. Copernicus é fallback, não resolução final. Teste em dispositivo físico pendente.
- Não depender de logs/artefactos temporários como única prova. Evidência neste Git é metadado e excertos de resultados, não cópia integral dos logs.

## Ficheiros recebidos fora do repo

Tamanhos e SHA-256 calculados sobre ficheiros montados em 2026-11-27 (Python hashlib.file_digest); ZIPs GitHub identificados pelo comentário. Ficheiros de terceiros não redistribuídos; não guardar HAR nem dados privados. Alguns ficheiros são outputs gerados, incluídos para preservar contexto.

| Ficheiro | Bytes | SHA-256 | Onde está arquivado |
|---|---:|---|---|
| portugal-261126.osm.pbf | 429648916 | `983c1ffcc59535d53b674ae0caeac3e4d25f28d93a7a635f2a9a531c4445bc91` | Release geodata-portugal-20261126; original |
| map.osm (1).xml | 6826513 | `abe3857180b64cfff833033dafebf313350aa51d853be6650f0bb9ee1cef3225` | Original não arquivado (metadados pessoais OSM); extrato filtrado data/pedome/pedome-osm.json |
| porto.tremocogames.com.har | 7933543 | `1854559c47ebc5b63076213bd9d8c08ad5e75b426db7fdd1ece6b663c5aeb7c6` | Não arquivar: terceiros, HAR pode conter informação de sessão; apenas análise |
| Texto colado.txt | 11021802 | `f97f6cf66f306aa9ed9f65b1c6b5e353db496d01e74d051bb9ddb31bab43427f` | Resposta /api/map PortoSlop; não arquivar: terceiros |
| MapSlop-Pedome-P0.zip | 525539 | `8b8cc4963694404669965f83ea2eb6c4b9874e01226ebfd44b19ecd2fccb7cf2` | Gerado experimentalmente; não arquivado, reconstruível com diferenças de empacotamento |
| MapSlop-Pedome-P0-teste.zip | 4267055 | `55ebf0e7790d785ea893201d583907f480ee6753a7db3975ff0fe01954687a47` | Gerado com fixture; não arquivado |
| slop-nairobi-main.zip | 3899528 | `dd9994979b7fc3370b61815535929f415926511a046911da4b2e380ae214c491` | Não arquivado ZIP; commit 64b8599ae7dd7ba56ffbe68f19cc1423a9e7f903 |
| london-loop-main.zip | 9256430 | `b23c416d1e2e83cc93222fe6f9d780711aaac9aef618312e5a47fe8d45c369e3` | Não arquivado ZIP; commit 3c7525e03804322f9c957984c88020a00e447a51 |
| slop-taipei-main.zip | 3757380 | `b921fda100e04a7a55ab474be47a7936bf08c0f2b67e2fa8919745ccae419d5d` | Não arquivado ZIP; commit 1d70708fc92a088b779c8c0e22677adb64966a1b |
| LiDAR2024_2025_Seccionamento.rar (11) | 3087054 | `bd1fa015eb493debbc7001b964511729b7d0f1e6dd9551cdb2a0addeb11c2404` | Índice vetorial; não arquivado; data/pedome/dgt-index-inventory.md |
| dgt_cdd_downloader-0.3.1 (1).zip | 51366 | `4de8b916d68658f3f9f485287bc8c8097c607aac4793495be4a1b2f99d7256c7` | Plugin QGIS; não arquivado; https://github.com/qgispt/dgtcd_downer |
| ortos1995.zip | 98677 | `52dd0a80d7c4b22a528a636fc760707e06f10346d1758717717f7120f5c5a6f0` | Índice vetorial; não arquivado |
| ortos2004_2006.zip | 183905 | `c40a4ab5fe123d0f24415542a85ea6f20db7c92b1070630844cc0e1e0b5d43cf` | Índice vetorial; não arquivado |
| ortos2007.zip | 100980 | `72a228fd51fe92a8190b531067fbc166fed22226caabae1ae50c607bba2754f3` | Índice vetorial; não arquivado |
| ortos2010.zip | 100028 | `d924d5a9c6cb09010605d03729ee8137080143605031c4e562f345646ebcc733` | Índice vetorial; não arquivado |
| ortos2012.zip | 99586 | `b42ec9a311839b25f25f2608db525d820ed4e1da10868bd1bf7824141809aed2` | Índice vetorial; não arquivado |
| ortos2015.zip | 99790 | `7ba15082485895b03ea786a027a0187cacb89eba02d46cb96863d8a9607404c0` | Índice vetorial; não arquivado |
| ortos2018.zip | 100293 | `1de3d0a11ebf9f9a5f2eee88d4fabe814f590feb64ed2047f8b4083204304974` | Índice vetorial; não arquivado |
| ortos2021.zip | 53147 | `0bc493ccb83cda5a1b7b34d8302d92257a6f6436e5543f1bac8180594bc8bc8d` | Índice vetorial; não arquivado |
| ortos2025 (1).zip | 103760 | `c7acd5eb9f8758e1604bd66d0ac1776a890a74452ee9f5c72adcfd301bec2f6a` | Índice vetorial; não arquivado |
| roofer-main.zip | 3434109 | `0a64fcd19410be4e92ca211b347e9e0b2b3b43753f55b44a01a77d3f04503e56` | Release reconstruction-toolchain-20261127; byte-idêntico; 4c7e18312c4eb90ad31be1b8e523726ba646b333 |
| City4CFD-main.zip | 131761175 | `36e496106b6590338e04e6594c25eacf1806fa1717359052e6f0c8fdbb67d469` | Release reconstruction-toolchain-20261127; byte-idêntico; b0763985b03b90d3e58665a9632ae543f725e17d |
| City3D-main.zip | 69497555 | `9bf4b4c89fa2ac4cc49ae3ca2af9b0bf241b2557fbd2f97587ae45f0d0aa3f04` | Release reconstruction-toolchain-20261127; byte-idêntico; 4e91afb85b7678ea34d6c1346e42f91264b42ba0 |
| OSM2World-master.zip | 3915929 | `e0ac980281a27a40e38eca176202ae6685e16371a0ffed350ae82167b45b49e0` | Release reconstruction-toolchain-20261127; byte-idêntico; 8a1c17e6a25f5238ca532c9460f69401151b4fd7 |
| 3dfier-master.zip | 36402288 | `2515cdce3572b0d2b3649555c4a1d7504f47602370ef3eb98cc11e2511fad3d6` | Release reconstruction-toolchain-20261127; byte-idêntico; 9f7fece6bb2624095dc7e7059defa1a9dbd4276e |
| cjio-master.zip | 8001075 | `9e02df04a4c7d37403eeaf7bee27fb0ad9a4947bfae8661d1d1755bbd316700e` | Release reconstruction-toolchain-20261127; byte-idêntico; 35728539127f71b1d5ae458169ff84050e5e20ad |
| BlenderGIS-master.zip | 422742 | `62fe4c73c1fee2d825580500b77b9adc85b5b9b891ec829831cced0f7ae6316b` | Release reconstruction-toolchain-20261127; byte-idêntico; 2add45ffec547f419cc77563a7fe976fd6c8f0c4 |
| roofer-linux-x86_64-v1.0.0.tar.gz | 20291139 | `85834b289467b0e583e2b9c59a725c97ef39dc03c0c0a12417a8a0666e1aa0a1` | Release reconstruction-toolchain-20261127; byte-idêntico; v1.0.0 |

## Passagem de turno — processo

- PR #1: links relativos e fences de seis documentos verificados; integrado.
- PR #2: README/licença/gitignore/CLAUDE.md; links relativos, fences e modo symlink 120000 verificados; integrado.
- Tarefa 2: STATUS e evidências corrigidos a partir de logs dos sete runs, metadados das releases e hashes de ficheiros montados; links relativos, fences, JSON e formato dos digests verificados. Não executa novo build do jogo.
