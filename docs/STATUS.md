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
- Toolchain `reconstruction-toolchain-20261127`: sete ZIPs byte-idênticos e binário Roofer v1.0.0, 8 ficheiro(s), 273726012 bytes. `roofer --help` executado com sucesso em Linux; não reconstruímos ainda edifícios reais. Outras ferramentas não executadas.
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
- Workflows de dados exclusivamente manuais, DGT consolidado; CI para PRs e Pages apenas main. Backlog em issues, ambiente P0 com versões fixadas. Subtree documentado no [ADR 0009 (proposta)](decisions/0009-motor-subtree-proposta.md); não executado, depende de aprovação e auditoria upstream.

## Próximos passos (por prioridade)

1. [#6 — Integrar MDT DGT de 0,5 m no terreno](https://github.com/atsisqual/MapSlop/issues/6)
2. [#7 — Calcular alturas e reconstruir edifícios com MDS−MDT e LAZ](https://github.com/atsisqual/MapSlop/issues/7)
3. [#8 — Corrigir circulação pela direita](https://github.com/atsisqual/MapSlop/issues/8)
4. [#9 — Gerar vegetação a partir de LAZ e COS2025](https://github.com/atsisqual/MapSlop/issues/9)
5. [#10 — Aplicar ortofoto de 25 cm ao solo com tiles LOD](https://github.com/atsisqual/MapSlop/issues/10)

As issues são o backlog executável; ROADMAP inclui critérios e tarefas de aceitação adicionais. Não fechar sem evidência.

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

- Tarefa 3: ADRs 0003–0008 registam decisões já tomadas (piloto, fallback, DGT, ferramentas/licenças, Pages/HUD e não reutilização PortoSlop). Verificação de links relativos e fences executada; sem alteração do jogo. Subtree fica para ADR de proposta separado.

- Tarefa 4: ROADMAP P0–P3 com critérios por testar e catálogo de dados, ligando hashes de todos os assets. SHA-256 dos 4 pequenos blobs calculado do conteúdo UTF-8 (autoteste abc, tamanho e comparação com sha256sum local do piloto). Corrigida contagem da toolchain. Links/fences verificados. Sem publicar releases.

- Tarefa 5: três templates Markdown com frontmatter YAML simples e cinco issues correspondentes ao backlog; links e formatação verificados. Issues #6–#10 confirmadas abertas pela API; nenhuma encerrada.

- Tarefa 6: ambiente P0 (Makefile, requirements.txt, package.json/lock, setup upstream e devcontainer). Run inicial 46044106964, job 140658925821, commit d151668a314f2c23900584030060bb5d23fb9515: Python 3.12.10, Node 22.16.0/npm 10.9.2; make setup, pip check sem dependências quebradas, make build e make test (67/67 em cada execução), HTTP make serve OK, relatório real/plano 179 vias, 527 edifícios, 113 nós, 134 ligações. Docker build e python/node/npm/git/make dentro do container OK. Lockfile gerado pelo npm nesse run; make setup passa a exigir npm ci. Segundo run 46044314224 (job 140659613926, commit d990fa790616c9b073f14085dea2fead79ced2e9) concluído success com npm ci: pip check, make build/test (67/67 em cada), make serve HTTP, Docker build e versões verificadas. [Evidência persistente](research/environment-evidence-20261127.md). GDAL/PDAL ficam para P1.

- Tarefa 7: cinco workflows DGT substituídos por dgt.yml parametrizado; dados workflow_dispatch apenas, CI read-only em PRs, smoke browser partilhado com Pages. Ver [workflows](workflows.md). CI run 46044980735/job 140661859061 no head 6bd7d1ca6ca89c7ab9dd0f9a3dace8fd8bfcffa0 concluído success: 6/6 testes DGT offline; 61 links, 9 workflows, 116 digests e 4 hashes; 67/67 em três execuções npm test; browser desktop e multitouch OK (2,1776 m). [Evidência persistente](research/ci-evidence-20261127.md). Nenhuma aquisição live nem publicação de releases.

- Tarefa 8: ADR 0009 com estado proposta, alternativas, plano, riscos de licenciamento e critérios verificáveis. Nenhuma migração executada; motor, build e workflows inalterados nesta tarefa. CI run 46045393176/job 140663257164, head eeb5b60c731a456b14289a33a6c0541f4ae4750d: success; 67 links internos, 9 workflows, 116 digests, 4 hashes; DGT offline 6/6; três execuções de 67/67 testes; build real/plano 179 vias, 527 edifícios, 113 nós, 134 ligações; Chromium distância 2,0356617684523037 m, touchSpeed 1,3689840365607093, multiTouch=true, touchRelease=true, success=true. Formatação e 23 links nas três páginas modificadas verificados antes do PR. Cinco releases mantidas em rascunho; 116 nomes/tamanhos/digests da API iguais ao inventário (7 803 124 586 bytes). Não houve redownload independente dos originais nem teste em dispositivo físico.

## Continuação P1 — issue #6

- Preparado pipeline offline de MDT 0,5 m → grelhas estáticas (2/5/10 m, 1 m opcional), validação de SHA-256/CRS/nodata/cobertura e 100 pontos, integração opt-in no adaptador, testes sintéticos e workflow exclusivamente manual de validação real. Ver [pipeline](terrain-dgt.md) e [ADR 0010](decisions/0010-grelha-mdt.md).
- Nesta alteração ainda não foi executada a recolha/conversão real nem o teste Chromium com DGT. PR CI solicitado; resultados a registar depois. Não fechar #6, não publicar derivados/release nem executar subtree. A demo plana continua inalterada.

### Revisão pré-merge PR #15

- CI inicial no commit `b96f9c9d8bdc5da011164e246a755536fe3f3544`, run 46051557178/job 140683868394: success. `make setup`, unittest 11/11, check-repo 73 links/10 workflows/116 digests/4 hashes; quatro execuções npm test 67/67; Chromium plano 2,177635 m, sintético 5 m 2,195771 m, contacto início/fim 0,03 m, multitoque e release true. Valores sintéticos, não DGT.
- Revisão: dispatch permite branch agent/dgt-terrain-grid e main; uma execução compara 2/5 m; um rascunho por branch, substituição segura dos assets, MAE/máximo/RMSE, contagem/tamanho/hash e contacto por frame limitado a 0,5 m. Cinco releases existentes são originais/toolchain; nenhum rascunho experimental existia, nada eliminado.
- Bloqueio: conector não disponibiliza workflow_dispatch e o workflow novo ainda não está registado em main. Contorno legítimo sem merge: workflow manual já registado pedome-terrain.yml no branch do PR, mode=dgt, chama o novo workflow via workflow_call. Conector não tem ação para iniciar a execução. Comando: gh workflow run pedome-terrain.yml --ref agent/dgt-terrain-grid -f mode=dgt. PR #15 ficou aberto aguardando os resultados; regra histórica de ambas as resoluções foi substituída na revisão TIN abaixo.
- Tarefa adicional: teste manual num Android físico, 5 minutos com aceleração, viragem, travagem e reset. Registar modelo/OS/browser/resolução, mediana e percentil baixo FPS, pico de memória e método (ou indisponibilidade), falhas e comparação 2/5 m. Não executado. Não publicar derivados DGT para testar sem autorização.


### Resultados reais — run 46053111254 (27-11-2026)

O run manual em `b95df198c277fdf9509f94f58f63592854766d7a` terminou failure pela regra antiga, não por falha de condução. Quatro TIFF originais conferidos pelo pipeline (bytes e SHA-256), EPSG:3763, 4 040 084 pixels do envelope, 0 inválidos. Rascunho `geodata-dgt-terrain-agent-dgt-terrain-grid`. [Evidência preservada](research/dgt-terrain-grid-evidence-20261127.json): JSON emitido nos logs e metadados dos assets (tamanhos/digests); conector não permite descarregar bytes de asset de release, não alegar rehash do validation.json.

| Produto | Vértices | Triângulos | JSON bytes | Máx. 100 pts (m) | MAE (m) | RMSE (m) | Condução (m) | Contacto máximo (m) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Grelha 2 m | 252 506 | 503 004 | 1 812 236 | 0,430891 | 0,041068 | 0,085677 | 2,025589 | 0,03 |
| Grelha 5 m | 41 006 | 81 204 | 294 403 | 1,192319 | 0,109483 | 0,220535 | 2,101722 | 0,03 |
| Grelha 10 m | 10 404 | 20 402 | 74 841 | 1,820113 | 0,226085 | 0,385827 | não testada | não testado |

2/5 m: 35 amostras em cada, diferença máxima superfície de colisão 0 m, browser/multitoque/release true. Hash completo de cada saída e de validation.json no JSON histórico (a release experimental será atualizada, mas esta evidência não será substituída).

### PR #15 — revisão TIN e condução longa

- TIN offline pydelatin 0.4.0, MIT, código upstream tag v0.4.0 commit e281368a62429a47686c1e21786678cc5213fcb1; dependência fixada, não implementar algoritmo. Reamostragem do MDT original para coordenadas locais a 0,5 m, erro interno 0,25 m, cap 149 999; validação por 100 pontos e vias OSM amostradas de 0,5 m em 0,5 m, centro e ±1,5 m. TIN usa as próprias faces no terreno, altura/colli­sões e corte de estradas/passeios. Critério TIN máximo ≤0,5 m em ambos os conjuntos e <150k vértices. Se falhar, manter 2 m com custo e erros registados no ADR; 5/10 m como LOD distante por RMSE, sem gate global.
- Teste longo: percurso ≥100 m com curva e declive numa via OSM, comandos analógicos e física/colli­sões reais em Chromium (passos fixos 1/60 s, sem teleport durante o percurso, não benchmark FPS). Contacto por passo ≤0,5 m, curva medida ≥15°, declive ≥2%/20 m, zero colisões reportadas. O workflow testa 2 m e TIN e emite validation.json schema 2 e alias terrain-default.json só se um candidato próximo passar. Mantém um rascunho de evidência por branch; os dados originais e o Pages público não são alterados.
- [Pipeline](terrain-dgt.md) e [ADR 0010](decisions/0010-grelha-mdt.md) atualizados. CI sintético e teste real da nova revisão pendentes neste registo. Voltar a lançar pedome-terrain.yml no branch agent/dgt-terrain-grid com mode=dgt após CI. Não fazer merge até análise dos novos resultados e registo persistente. Teste Android real/FPS/memória permanece aberto.


### Resultado real TIN — run 46055620274 (27-11-2026)

Commit `bec31303336100bd4a0ee89fed345ce9f5c2943d`, workflow success pela regra anterior inconsistente; **não aceitar nenhum candidato de proximidade segundo o critério uniforme atual**. Quatro TIFF verificados, CRS EPSG:3763, 4 040 084 pixels de cobertura, zero inválidos. 70 627 amostras rodoviárias, 121 vias. [Evidência persistente](research/dgt-terrain-tin-evidence-20261127.json) guarda JSON dos logs e metadados de 16 assets do rascunho `geodata-dgt-terrain-agent-dgt-terrain-grid`, incluindo hashes completos. Não foi possível descarregar bytes de validation.json pelo conector; JSON emitido nos logs é a fonte do conteúdo.

| Produto | Vértices | Triângulos | JSON bytes | Máx. 100 pts (m) | MAE (m) | RMSE (m) | Máx. estrada (m) | RMSE estrada (m) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 m | 252506 | 503004 | 1812236 | 0,430891 | 0,041068 | 0,085677 | 1,412378 | 0,078945 |
| 5 m | 41006 | 81204 | 294403 | 1,192319 | 0,109483 | 0,220535 | 2,455828 | 0,178954 |
| 10 m | 10404 | 20402 | 74841 | 1,820113 | 0,226085 | 0,385827 | 3,011910 | 0,341721 |
| TIN 0,25 m | 90284 | 180007 | 4950736 | 0,212807 | 0,062106 | 0,078314 | 0,586453 | 0,067989 |

Condução longa em Rua das Bouças (OSM way 149303998): grelha 2 m 104,157436 m, 1183 amostras, declive 5,528%/20 m, curva real 46,536°, desvio lateral 0,395 m; TIN 104,213960 m, 1185 amostras, declive 6,063%/20 m, curva 46,543°, desvio lateral 0,394 m. Ambos contacto máximo 0,03 m, superfície de colisão 0 m, zero colisões reportadas, browser e multitoque passaram. Este teste é física fixed-step, não FPS real. A escolha histórica terrain-default.json (2 m) fica explicitamente invalidada pela revisão seguinte. 5/10 m passaram metas RMSE de LOD distante, sem condução avaliada.

### Revisão 3 — precisão uniforme, binário e refinamento junto a vias

- Todos os candidatos próximos, inclusive grelha 2 m de recurso, têm de satisfazer máximo ≤0,5 m nos 100 pontos e nas estradas, mais teste de condução. TIN adicionalmente <150 000 vértices e máximo ≤0,5 m nos nós da grelha local reamostrada. Se nenhum passar, validation.json pass=false e sem alias; o workflow falha, não há fallback aprovado. Teste unitário de regressão com 1,41 m em estrada e 0,50001 m nos 100 pontos.
- Novo formato MSLTERR1 .bin com cabeçalho JSON embutido, alturas regulares Float32 LE (índices implícitos), TIN XYZ Float32 LE e faces Uint32 LE. O build e o Chromium leem o binário; não reexpande em JSON no geodata.js. Medir bytes brutos, gzip determinístico nível 9 (mtime=0), hash e tamanho equivalente JSON/gzip. Erros calculados sobre produto descodificado; nenhum ganho real de tamanho ou memória declarado antes do run. O browser lê .bin bruto; gzip é medição comparativa, não compressão HTTP já ativa.
- Refinamento: Delatin base 0,25 m, pool 0,15 m e retenção de novos vértices até 6 m dos eixos OSM, com SciPy 1.15.3 (BSD-3-Clause, [fonte fixada](https://github.com/scipy/scipy/tree/e29dcb65a2040f04819b426a04b60d44a8f69c04)) Delaunay/Qhull; não é triangulação constrained. Até cinco rondas de avaliação/refinamento, cap 149999; acrescentar pontos reais do MDT em resíduos de estrada >0,38 m e nós de raster >0,43 m, avaliar todos os nós locais e corredores rodoviários. Relatar contagens, máximos e iterações, não alegar garantia contínua. validation.json schema 3 contém os 10 piores pontos por produto, way/nome/tipo/offset, x/z, lon/lat, altitude MDT/mesh e erro assinado/absoluto. Não atribuir causa sem inspeção; perfis próprios de estrada serão tarefa posterior.
- CI offline pendente nesta revisão; rerun manual pedome-terrain.yml branch agent/dgt-terrain-grid mode=dgt. Novo workflow preserva único rascunho por branch e remove aliases/JSON antigos apenas quando substitui a evidência experimental; não toca nos originais. Sem merge até validar nova regra, sem publicar releases, sem subtree. Android físico/FPS/memória pendente.
