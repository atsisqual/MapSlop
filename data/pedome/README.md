# Pedome — base geográfica P0

Dados de OpenStreetMap, © OpenStreetMap contributors, ODbL 1.0: https://www.openstreetmap.org/copyright e https://opendatacommons.org/licenses/odbl/1-0/.

- Origem: exportação XML da API OpenStreetMap fornecida em 2026-11-27 (`map.osm (1).xml`, caixa 41.405,-8.405,41.435,-8.375).
- Ficheiro versionado: `pedome-osm.json`, 1208 elementos com IDs, tags e coordenadas, sem usernames, UID, changesets ou timestamps individuais. Seleção por interseção da caixa envolvente das geometrias com a caixa piloto [41.4105,-8.395,41.4195,-8.383] (S,W,N,E). Não é a fronteira administrativa.
- 200 ways com highway antes da filtragem do motor, 527 ways com building. Sem ways incompletas no XML; sem relações relevantes incompletas na área.
- O ZIP experimental construído localmente teve 179 registos rodoviários, 527 edifícios, 511 alturas estimadas, 113 nós e 134 links de navegação, 12 171 triângulos de asfalto; 67 testes aprovados. Relevo plano. Browser ainda não validado.
- SHA-256 do ZIP experimental original MapSlop-Pedome-P0.zip: 8b8cc4963694404669965f83ea2eb6c4b9874e01226ebfd44b19ecd2fccb7cf2 (ZIP original não guardado no Git).
- Motor de referência: Slop Nairobi commit 64b8599ae7dd7ba56ffbe68f19cc1423a9e7f903. README upstream declara MIT, inventário de licenças de código/ativos ainda não concluído. O repositório público não incorpora os bundles PortoSlop nem o ZIP completo do jogo.

## Reproduzir

Com Python 3.10+, Node 22 e o Git, na raiz do MapSlop:

```sh
git clone https://github.com/briankariuki/slop-nairobi.git ../slop-nairobi
git -C ../slop-nairobi checkout 64b8599ae7dd7ba56ffbe68f19cc1423a9e7f903
python tools/prepare-pedome.py ../slop-nairobi ./pedome --osm-json data/pedome/pedome-osm.json --flat
python -m http.server 8080 --bind 127.0.0.1 --directory ./pedome
```

Abrir http://localhost:8080/?webgl. O build necessita de CDN Three.js para o browser. Não confundir testes automatizados com validação interativa.
