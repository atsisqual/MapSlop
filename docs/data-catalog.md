# Catálogo de dados e ferramentas

Atualizado em 2026-11-27. Todas as releases abaixo continuam **rascunho**. Exigem acesso de escrita autorizado; sem esse acesso pedir ao mantenedor. Não publicar sem autorização. [Inventário por asset](research/release-assets-20261127.json) contém nomes, bytes e SHA-256 completos, incluindo manifestos; [evidências](research/evidence-20261127.md) contém contagens/comandos/resultados. Não confundir Git blob SHA-1, commit e SHA-256 do conteúdo.

## Extratos pequenos versionados

| Dataset | Fonte e data | Licença | Geração |
|---|---|---|---|
| pedome-osm.json | OSM export XML, 2026-11-27; piloto S,W,N,E 41.4105,-8.395,41.4195,-8.383 | ODbL 1.0, © OSM contributors | [osm-xml-to-json.py](../tools/osm-xml-to-json.py) |
| CAOP 2025 Pedome | DGT OGC API freguesias, dtmnfr 031230, 2026-11-27 | DGT CC BY 4.0 | consulta OGC; [collect-ogc-pedome.py](../tools/collect-ogc-pedome.py) recolhe área alargada |
| COS2025 piloto | DGT OGC API cos2025v1, 2026-11-27; 35 objetos | DGT CC BY 4.0 | consulta OGC bbox piloto, [arquivo](../data/GEODATA-ARCHIVE.md) |
| dgt-items.json | IDs STAC de 4 tiles MDT/MDS e 2 ortos, 2026-11-27 | metadados factuais; não licença dos rasters | consulta API STAC /collections/{collection}/items/{id}; [download-dgt-pedome.py](../tools/download-dgt-pedome.py) |

SHA-256 calculado do conteúdo UTF-8 dos Git blobs da árvore anterior a este PR; comprimento conferido, autoteste abc e cross-check do OSM piloto com sha256sum local:

| Ficheiro | Bytes | SHA-256 |
|---|---:|---|
| [data/pedome/pedome-osm.json](../data/pedome/pedome-osm.json) | 601191 | `948fa4269ba8eaa9d995711005d2c8a5413ac4ea16f69838ef031e870b032037` |
| [data/pedome/caop2025-pedome.geojson](../data/pedome/caop2025-pedome.geojson) | 16021 | `9ff818d5629e9fbf1c44d314e9a9957d767e90375dc4dee6d9e1930c1d082bcb` |
| [data/pedome/cos2025-pilot.geojson](../data/pedome/cos2025-pilot.geojson) | 258415 | `3e0e5b01691969b837d7274ea78492d51877bcf665ba423e5aea867d41f13dde` |
| [data/pedome/dgt-items.json](../data/pedome/dgt-items.json) | 765 | `3c74e4f8e74cb4dc0683311fb0ccee98dcae690924bd8b651f01bbcd88f50de6` |

## Arquivo bruto e extratos alargados

Área W,S,E,N -8.405,41.405,-8.375,41.435 (~8,4 km²), exceto PBF Portugal. Tiles originais intersectantes, não recortados à bbox. Aquisição 2026-11-27; data de observação e versão na designação do asset.

| Dataset | Fonte, data, resolução | Licença/atribuição | Release | Inventário / script |
|---|---|---|---|---|
| PBF Portugal | Geofabrik snapshot 2026-11-26 | ODbL 1.0 © OSM | geodata-portugal-20261126 | 429648916 bytes, `983c1ffcc59535d53b674ae0caeac3e4d25f28d93a7a635f2a9a531c4445bc91`; archive-portugal.yml |
| OSM alargado | recorte do PBF anterior | ODbL 1.0 © OSM | geodata-pedome-vectors-20261127 | 1 ficheiro(s), 2150454 bytes; osmium + osm-xml-to-json.py |
| Freguesias e municípios | DGT CAOP 2025, OGC | DGT CC BY 4.0 | geodata-pedome-vectors-20261127 | 8 freguesias, 2 municípios; collect-ogc-pedome.py |
| COS2025v1 | DGT OGC, 2025 | DGT CC BY 4.0 | geodata-pedome-vectors-20261127 | 239 features; collect-ogc-pedome.py |
| CRUS | DGT OGC, snapshot 2026-11-27 | política DGT aberta; verificar termos camada | geodata-pedome-vectors-20261127 | 86 features, só geometria; collect-ogc-pedome.py |
| Cadastro | DGT OGC, snapshot 2026-11-27 | verificar termos camada; sem informação pessoal | geodata-pedome-vectors-20261127 | **0 features**, cobertura vazia; collect-ogc-pedome.py |
| MDT 0,5 m | DGT STAC julho 2025 v02 | STAC proprietary vs política aberta; não publicar | geodata-dgt-pedome-20261127 | 15 ficheiro(s), 222723518 bytes; collect-dgt-pedome.py |
| MDS 0,5 m | DGT STAC julho 2025 v02 | CC BY 4.0 indicado no STAC, DGT | geodata-dgt-pedome-20261127 | 15 ficheiro(s), 230314564 bytes; collect-dgt-pedome.py |
| MDT 2 m | DGT STAC julho 2025 | licença por coleção a reconciliar, DGT | geodata-dgt-pedome-20261127 | 15 ficheiro(s), 15237327 bytes; collect-dgt-pedome.py |
| MDS 2 m | DGT STAC julho 2025 | licença por coleção a reconciliar, DGT | geodata-dgt-pedome-20261127 | 15 ficheiro(s), 15443335 bytes; collect-dgt-pedome.py |
| LAZ | DGT LiDAR 2024–2025, julho 2025 v05 | política LiDAR aberta; confirmar coleção | geodata-dgt-pedome-20261127 | 15 ficheiro(s), 1902990934 bytes; collect-dgt-pedome.py |
| Ortofoto atual | DGT 2025 25 cm, 084-2/084-4 | CC BY 4.0 segundo catálogo oficial, DGT | geodata-dgt-pedome-20261127 | 2 ficheiro(s), 1102550931 bytes; collect-dgt-pedome.py |
| Ortofoto histórica | DGT 1995 1 m; 2004/07/10/12/15 50 cm; 2018/21 25 cm | CC BY 4.0 segundo catálogo oficial, DGT | geodata-dgt-history-20261127 | 16 ficheiro(s), 3588836327 bytes; collect-dgt-pedome.py --historical-orthos |
| Copernicus GLO-30 | DSM COG N41_00_W009_00, 2026-11-27, ~30 m | termos Copernicus; crédito DLR/Airbus, UE/ESA | não arquivado permanentemente | 5670 amostras, hash não preservado; prepare-pedome.py sem --flat usa fetch-terrain.mjs upstream |
| Mapa Construções LiDAR 2024 | DGT dados.gov.pt, class 6 | consultar licença específica | não obtido | hash inexistente; candidato, não dataset disponível |

Cada hash completo dos assets em releases está no [JSON de evidência](research/release-assets-20261127.json). Manifestos e índices OGC também estão nesse JSON. Fontes: https://cdd.dgterritorio.gov.pt/ (STAC), https://ogcapi.dgterritorio.gov.pt/ (OGC), https://www.dgterritorio.gov.pt/dados-abertos (política), https://www.dgterritorio.gov.pt/novo-catalogo-de-ortofotos-de-portugal-continental-no-centro-de-dados-da-dgt (ortofotos), https://www.openstreetmap.org/copyright (OSM).

## Ferramentas e produtos derivados

- [reconstruction-sources.json](../data/reconstruction-sources.json): repositório, licença, commit, nome, bytes, SHA-256 de sete ZIPs e binário Roofer v1.0.0; release reconstruction-toolchain-20261127. Workflow reconstruction-archive.yml. `roofer --help` passou; não há reconstrução Pedome.
- Motor Nairobi e Three.js fixados em [STATUS](STATUS.md); não são dados geográficos. Produtos `pedome/` gerados por prepare-pedome.py; não se arquivam como fonte; demo P0 plana.
- Índices GeoPackage e restantes uploads originais não preservados listados com hashes em [STATUS](STATUS.md). Dados PortoSlop nunca entram no pipeline.

Para um novo produto guardar fonte/hashes de entradas, CRS/resolução, comando/script e commit, parâmetros, contagem/erros, licença e SHA-256 da saída. Ficheiros grandes em releases rascunho até aprovação. Não afirmar que há dados inexistentes.
