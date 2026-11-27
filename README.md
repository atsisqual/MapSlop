# MapSlop

Simulador 3D em browser de localidades reais, com condução livre em terceira pessoa. Primeiro mapa: Pedome, Vila Nova de Famalicão.

**[Jogar a pré-visualização](https://atsisqual.github.io/MapSlop/)** · [Versão tátil](https://atsisqual.github.io/MapSlop/mobile.html?webgl)

## Estado atual

P0 experimental: mapa piloto OSM, 179 registos de vias, 527 edifícios, condução, HUD tátil, minimapa e reposicionamento. A versão publicada usa relevo plano e alturas maioritariamente estimadas. Não representa toda a freguesia. A reconstrução DGT ainda não está integrada. Estado, testes e bloqueios: [STATUS](docs/STATUS.md).

## Executar localmente

Requisitos: Git, Python 3.10+, Node.js 22/npm. O motor externo é Slop Nairobi no commit fixado `64b8599ae7dd7ba56ffbe68f19cc1423a9e7f903`.

```sh
git clone https://github.com/atsisqual/MapSlop.git
cd MapSlop
git clone https://github.com/briankariuki/slop-nairobi.git ../slop-nairobi
git -C ../slop-nairobi checkout 64b8599ae7dd7ba56ffbe68f19cc1423a9e7f903
python tools/prepare-pedome.py ../slop-nairobi ./pedome --osm-json data/pedome/pedome-osm.json --flat
python -m http.server 8080 --bind 127.0.0.1 --directory ./pedome
```

Abrir http://localhost:8080/?webgl. A pasta de saída não pode existir. O build executa testes upstream; sem `--three-vendor`, o browser usa o CDN Three.js. O workflow Pages fornece a versão fixada e local dos módulos.

Controlo: WASD/setas, comando ou botões táteis; M amplia o mapa; R repõe o carro. A publicação é feita pelo GitHub Pages, sem servidor de jogo.

## Documentação e dados

- [AGENTS.md](AGENTS.md): regras obrigatórias para agentes.
- [Estado do projeto](docs/STATUS.md) e [decisões](docs/decisions/README.md).
- [Arquivo de dados](data/GEODATA-ARCHIVE.md), [dados piloto](data/pedome/README.md), [ferramentas de reconstrução](data/reconstruction-sources.json). Originais grandes nas Releases em rascunho, com acesso de escrita; não são distribuídos na demo.

## Créditos e licenças

Código MapSlop: [MIT](LICENSE). Base [Slop Nairobi](https://github.com/briankariuki/slop-nairobi), MIT declarado no README, adaptado de [Slop New York](https://github.com/mrdoob/slop-newyork) (Mr.doob, MIT); [Three.js](https://github.com/mrdoob/three.js), MIT. Inventário de assets upstream por concluir; não reutilizamos modelos capturados ou código/dados PortoSlop.

Dados © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), ODbL 1.0. DGT: Direção-Geral do Território, CC BY 4.0 quando confirmado para o produto; licenças contraditórias mantêm arquivos em rascunho. Relevo alternativo: Copernicus WorldDEM-30 © DLR e.V. 2010–2014 e © Airbus Defence and Space GmbH 2014–2018, disponibilizado pela UE e ESA no programa COPERNICUS. Ferramentas GPL/AGPL de reconstrução são processos separados, não dependências do runtime. Cada fonte mantém os seus próprios termos.
