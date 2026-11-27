# MapSlop — geographic source archive

## Scope

Expanded Pedome and surroundings: WGS84 bounds west -8.405, south 41.405, east -8.375, north 41.435 (~8.4 km²). Keep all original intersecting tiles, rather than downsampling them for the game. Portugal-wide OSM is separately archived; not requesting country-wide LiDAR or orthophotos.

## Archives (GitHub Releases, drafts)

- `geodata-portugal-20261126`: exact uploaded Portugal OSM PBF, 429648916 bytes, SHA-256 verified.
- `geodata-pedome-vectors-20261127`: expanded OSM extract plus DGT OGC layers (municipalities, parishes, COS2025v1, CRUS, cadastral geometries), inventory and SHA256SUMS.
- `geodata-dgt-pedome-20261127`: original DGT MDT/MDS at 0.5 m and 2 m, LiDAR point clouds and 2025 orthophotos where retrieval succeeds. As checked on 2026-11-27, all 15 MDT 0.5 m and 15 MDS 0.5 m were already uploaded; remainder was still uploading.
- `geodata-dgt-history-20261127`: historical aerial imagery, acquisition started; check workflow and release manifest for actual coverage.

See [Releases](https://github.com/atsisqual/MapSlop/releases), [current raster acquisition](https://github.com/atsisqual/MapSlop/actions/runs/46038918273), [vector acquisition](https://github.com/atsisqual/MapSlop/actions/runs/46039014994), [historical ortho acquisition](https://github.com/atsisqual/MapSlop/actions/runs/46039259098). Workflows retain successful originals even if another collection fails.

## Additional building source

DGT [Mapa de Construções LiDAR 2024](https://dados.gov.pt/pt/datasets/mapa-de-construcoes-lidar-2024) identifies permanent structures from class 6 of the classified point cloud, minimum area 10 m²; nearby buildings can merge and some classifications are wrong. Use as complementary geometry, not an authoritative count of individual buildings. Official dataset listed as public; no national ZIP downloaded here. Locally deriving class-6 structures from original LAZ is an alternative. Preserve OSM identities and avoid duplicate footprints.

## Data use

DGT states its [nine orthophoto coverages](https://www.dgterritorio.gov.pt/novo-catalogo-de-ortofotos-de-portugal-continental-no-centro-de-dados-da-dgt) are CC BY 4.0; attribute Direção-Geral do Território. [LiDAR documentation](https://www.dgterritorio.gov.pt/atividades/cartografia/cartografia-topografica/modelos-digitais). Some STAC licence labels conflict with the official open-data policy; raw archives remain unpublished pending reconciliation. OSM © OpenStreetMap contributors, ODbL 1.0. Preserve separate licences and source dates. No credentials, session cookies, signed URLs or private cadastral owner attributes in the repository. Do not republish data merely because it can be downloaded.

## Game preparation

Original tiles are archival source data, not files served to mobile clients. Generate terrain meshes at suitable levels of detail, surface-minus-terrain height statistics for building footprints, tree/vegetation classes and canopy structure from LAZ, tiled aerial textures, hydrography, road elevations and land-use surfaces. Keep full-resolution originals so these products can be rebuilt without re-downloading. All archive assets require manifest/hash verification; numerical resolution is not a guarantee of survey accuracy.

## Atualização de conclusão (2026-11-27)
As recolhas LAZ e histórico terminaram com sucesso; 15 LAZ e 16 ortofotos históricas foram arquivadas. Ver [evidência e contagens](../docs/research/evidence-20261127.md) e [digests completos](../docs/research/release-assets-20261127.json). Cadastro vazio. Todas as releases em rascunho; publicação requer autorização.
