# Estado do MapSlop — 28/11/2026

Ler [AGENTS.md](../AGENTS.md). Este ficheiro descreve estado atual; o histórico integral está em [STATUS-history-20261128.md](STATUS-history-20261128.md). Auditoria do Claude: [relatório](audit/2026-11-28-auditoria-tecnica.md), [CSV histórico](audit/ferramentas-estado.csv), [registo atualizado](../tools/registry.yaml). O CSV é uma fotografia da auditoria, não resultados atuais.

## Produção

- [MapSlop móvel](https://atsisqual.github.io/MapSlop/mobile.html?webgl&build=255673d8bc58), build 255673d8bc58; Pages run 46134591537 aprovado.
- TIN DGT aprovado SHA 36019dfc27584d667555c794350107c29981da4f4ee15bac2c03078aba0d895b; runtime combinado SHA f9f574945cfe74923076b3d430fefb2848e0cad5a1b0ce67bcbd787b7fe0f57c, draft geodata-dgt-orthophoto-46098427966-1.
- 179 registos de vias, 527 edifícios (371 alturas LiDAR/156 estimadas), 17 Roofer, 5702 árvores, 64 tiles ortofoto 25cm. Circulação direita, 104m drive aprovado, HUD tátil. Sem FPS medido em telemóvel físico.
- Motor Nairobi 64b8599ae7dd7ba56ffbe68f19cc1423a9e7f903; Three.js f17eb5d689094a3fbd4cd0d64d54729a48036ce0.
- Piloto bbox S,W,N,E 41.4105,-8.395,41.4195,-8.383; origem igreja 41.41501,-8.38809. Dados de origem DGT EPSG:3763; runtime local linearizado WGS84 X este/Y acima de base/Z sul (não confundir com PT-TM06).
- Originais e derivados em drafts; [inventário](../data/GEODATA-ARCHIVE.md). Nunca publicar release bruta. Mapillary: 0 resultados no piloto; controlo Famalicão 1177; cobertura nova via fotos próprias autorizadas.

## PRs em curso

| PR | Estado / gate seguinte |
|---|---|
| [#40](https://github.com/atsisqual/MapSlop/pull/40) Ortofoto | V1 rejeitada visualmente; V2 efeito baixo segundo auditoria, não fazer merge sem confirmação do dono. Preservar floresta e edifícios. |
| [#41](https://github.com/atsisqual/MapSlop/pull/41) Toolchain | 9/10 jobs run 46143556606; Open3D/PyMeshLab/OpenMVS etc. sintéticos; RenderDoc exit139. Jobs de captura e formatos de fornecedores retirados da cadeia ativa, preservar investigação histórica fora de produção. Não merge tal como está. |
| [#42](https://github.com/atsisqual/MapSlop/pull/42) Igreja | Run 46152915989 PASS fixture e 6 mapas CC0 reais em geometria sintética. Lockfile fixado; replay e run real pendentes. Porta inferida tem fallback, configuração explícita mantém gate. |
| [#43](https://github.com/atsisqual/MapSlop/pull/43) Infraestrutura | Run 46152945559 PASS 8/8; Triangle removido, cjio Earcut, SUMO 430 lanes e controlo de reprojeção OSM p95 0,00769 m; não prova precisão topográfica. Laboratório, não merge/integração. |
| [#44](https://github.com/atsisqual/MapSlop/pull/44) Auditoria | Proposta do Claude e reorganização do estado; revisão do dono. |
| [#45](https://github.com/atsisqual/MapSlop/pull/45) Iluminação | Candidato privado, sombras edifícios estáticos low/high e fog, fixture pendente à escrita, depois real. Sem mudança pública. |

## Prioridades aceites (ajustes à auditoria)

1. Desbloquear #42, confirmar #40 visualmente, resolver riscos #41/#43. Não remover histórico útil; manter ferramentas dormentes isoladas.
2. Criar controlos independentes aprovados pelo dono a partir da ortofoto e gate visual com câmaras fixas/relatório. A aprovação humana é obrigatória; não inventar controlos medidos.
3. Iluminação e ambiente (#45), depois fachadas dos 527 edifícios, muros/portões (PDAL + OSM + 3dfier como fallback), pormenor do solo, postes e mobiliário. Um PR visual de cada vez para publicação; novos testes privados podem correr em paralelo.
4. Otimização glTF-Transform/gltfpack/meshopt/KTX2 apenas aplicada a assets concretos. osm2streets para ruas quando houver comparação com o TIN/road graph. Não acumular laboratórios.
5. Expansão de território, rotunda #35, NPCs e fotogrametria própria em pausa até revisão do dono.

## Lançamentos manuais

Usar workflow registado em main e branch indicado:
```sh
gh workflow run pedome-terrain.yml --repo atsisqual/MapSlop --ref agent/local-photogrammetry -f mode=roofs
gh workflow run pedome-terrain.yml --repo atsisqual/MapSlop --ref agent/clean-orthophoto -f mode=orthophoto
gh workflow run pedome-terrain.yml --repo atsisqual/MapSlop --ref agent/lighting-preview -f mode=roofs
```
Confirmar CI antes de dispatch. Resultados reais em draft privado; merge/publicação só após revisão visual explícita. Testes sintéticos nunca são validação real. Ver [workflows](workflows.md) e [histórico](STATUS-history-20261128.md).

## Bloqueios

- Telemóvel físico sem medição de FPS/memória.
- Fachadas reais requerem fotos ou levantamento autorizado; geometria procedural é estimada.
- Materiais/style OSM2World e alinhamento de modelos precisam de revisão; não usar cena inteira duplicada. MRoadGen original não recebido.
- Não há autorização para dados Google/Apple; não usar nem publicar derivados. Não adquirir ferramentas/dados sem aplicação concreta.
