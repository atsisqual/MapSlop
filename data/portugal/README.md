# Portugal — fonte geográfica nacional

O utilizador disponibilizou `portugal-261126.osm.pbf`, com 429648916 bytes. Cabeçalho OSM PBF observado; conteúdo nacional ainda não validado integralmente.

SHA-256: `983c1ffcc59535d53b674ae0caeac3e4d25f28d93a7a635f2a9a531c4445bc91`.

Fonte de referência: https://download.geofabrik.de/europe/portugal.html . O nome corresponde a uma exportação datada de 2026-11-26; o ficheiro de download e a sua igualdade com o fornecido ainda não foram confirmados online.

Não versionar o PBF nacional no Git normal (limite 100 MiB por ficheiro). O ficheiro original permanece no upload da conversa; não foi carregado para o GitHub. Para arquivo duradouro, usar armazenamento de dados ou Git LFS se houver quota e acesso. Este documento não substitui os bytes originais.

## Preparação de outras localidades (com osmium-tool)

Conservar o PBF original fora do checkout. Para reproduzir uma extração, por exemplo Pedome e imediações:

```sh
osmium extract --bbox=-8.405,41.405,-8.375,41.435 --strategy=complete_ways --output=pedome.osm portugal-261126.osm.pbf
python tools/osm-xml-to-json.py pedome.osm pedome-osm.json
```

O conversor tem a caixa piloto de Pedome por omissão e aceita `--bbox S W N E` para outras localidades. O extract deve conter uma margem que cubra a caixa piloto. As relações podem ficar incompletas, sendo descartadas pelo conversor. O comando de extração ainda não foi testado neste ambiente (osmium-tool indisponível).

© OpenStreetMap contributors, ODbL 1.0. https://www.openstreetmap.org/copyright . Respeitar atribuição e condições de redistribuição de bases derivadas. O PBF não é um modelo de elevação.
