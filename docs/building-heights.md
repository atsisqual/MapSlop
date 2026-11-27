# P1 — Alturas MDS−MDT (issue #7, fase 1)

## Entradas e produto

Quatro pares TIFF DGT MDT/MDS 0,5 m v02 (178494,178495,179494,179495), release rascunho geodata-dgt-pedome-20261127, SHA-256 no [inventário](research/release-assets-20261127.json). Terreno aprovado: terrain-tin.bin, rascunho geodata-dgt-terrain-agent-dgt-terrain-grid, SHA-256 93495e59862affea17c7202a089fe3203afb536184ab47740727194da669bb59; [evidência](research/dgt-terrain-final-evidence-20261127.json). Verificar os nove ficheiros antes de processar. OSM piloto versionado.

O adaptador exporta os registos de edifícios renderizados com tipo/ID OSM, anel e buracos. O script calcula building-heights.json com versão/proveniência, estatísticas, método/fallback, cotas e lista determinística de 20 casos para revisão, conforme [ADR 0011](decisions/0011-alturas-mds-mdt.md). O build verifica hashes OSM/terreno e igualdade de todos os fingerprints antes de aplicar. A TIN não muda. --building-heights exige --terrain-bin e --osm-json; --export-footprints exige OSM explícito. Sem opções, demo inalterada. Não reutilizar relatório para outra grelha ou recorte.

## Execução manual

Antes do merge: [Pedome real terrain fallback](https://github.com/atsisqual/MapSlop/actions/workflows/pedome-terrain.yml), branch agent/mds-building-heights, mode buildings.

```sh
gh workflow run pedome-terrain.yml --ref agent/mds-building-heights -f mode=buildings
```

O launcher chama pedome-building-heights.yml, exclusivamente manual/reutilizável. Um rascunho separado por branch recebe relatório, build/browser reports, logs, screenshots privados e SHA256SUMS. Não modifica originais nem rascunho do terreno; sem publicar Pages ou artefactos públicos com dados reais.

## Testes e limites

CI com raster sintético: pares, buracos, nodata, inset vazio, delta negativo, proveniência e fallback; build sintético com relatório marcado como sintético, render/condução e 20 probes de coerência footing/altura aplicada/colisões (≤0,05 m). Run real deve registar aceites/fallbacks, distribuição, 20 casos e coerência de colisões/condução. Inspeção visual dos 20 casos e Roofer/LAZ pendentes. Não fechar #7 sem estes critérios. Não afirmar precisão absoluta das alturas sem referência independente. Dependências GIS fixadas em requirements-terrain.txt; Shapely BSD-3-Clause. DGT/OSM mantêm termos próprios. Derivados apenas em rascunho.
