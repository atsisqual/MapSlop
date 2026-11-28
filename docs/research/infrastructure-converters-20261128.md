# Conversões de infraestrutura e interoperabilidade — 2026-11-28

Pedido do dono: estudar ferramentas que complementam Blender, Open3D, PyMeshLab, LiDAR e PBR, para elementos de infraestrutura realistas. Laboratório offline, sem alterar runtime, física, TIN, ortofoto ou Pages; respeitar ordem A–F e não iniciar publicação antecipada.

## Dados já existentes

Extrato versionado data/pedome/pedome-osm.json (1208 elementos, 236 nodes, 967 ways, 5 relations). Contagens tags no extrato integral: wall 25, retaining_wall 2, gate 16, fence 1, hedge 3, wicket_gate 1, power=pole 20, tower 10, bus_stop 9, crossing 15, steps 10, bench 4, recycling 5, letter_box 3, traffic_sign=PT:B2 1. Não é cobertura completa nem inventário dentro do recorte exato. Algumas ways incluem geometria muito fora do piloto (lat 41.3628..41.5913, lon -8.4354..-8.2353). Não usar a caixa global para gerar cidade, não inventar coordenadas nem relações incompletas.

## Ferramentas verificadas e plano

| Ferramenta | Entrada -> saída e uso | Estado |
|---|---|---|
| OSM2World | OSM -> GLB/OBJ/3D Tiles; muros, cercas, sinais, postes, mobiliário | código já inventariado commit 8a1c17e; inspecionado BarrierModule (wall, hedge, railing, balustrade, chain-link/pole fence). Release estável 0.4.0 Java 17; ZIP oficial 431 MB separado do snapshot; default style é repo separado. Teste real piloto limitado preparado; estilo/licenças e georreferenciação por validar. https://osm2world.org/download/ |
| SUMO netconvert | OSM XML -> .net.xml -> ASAM OpenDRIVE .xodr; topologia e faixas | teste real no extrato; export 1.4, inferência de ligações/larguras, limitações de alargamento/unidirecionalidade. Não substituir road graph aprovado. https://sumo.dlr.de/docs/Networks/Export.html |
| cjio | CityJSON -> GLB (sem texturas) / OBJ (texturas) | snapshot 3572853, CLI export format filename confirmado; versão PyPI 0.10.1. Teste sólido sintético; preservar semântica no sidecar e validar eixos. https://github.com/cityjson/cjio |
| IfcOpenShell | IFC -> GLB, BIM de pontes/estruturas/muros, GUID por objeto | 0.8.3.post2, offline LGPL; adaptador usa tesselação, material neutro, sem preservação de materiais IFC, origem local obrigatória. Teste muro 5×3×.2m. https://docs.ifcopenshell.org/ifcconvert.html |
| 3dfier | polígonos + LAS/LAZ -> CityJSON/OBJ; classes Road, Bridge/Overpass, Separation, Water, Terrain | snapshot 9f7fece já inventariado; ainda não executado nesta sessão. Testar com polígonos reais, LAS e CRS EPSG:3763; sem substituir TIN. https://tudelft3d.github.io/3dfier/supported_file_formats.html |
| GDAL/QGIS | GPKG/SHP/DXF -> GeoPackage/GeoJSON com reprojeção | investigação; usar ogr2ogr, preservar layers/IDs/CRS e Z, validar controlo; DXF pode não ter CRS, exigir confirmação. https://gdal.org/en/stable/programs/ogr2ogr.html |
| MOSAIQ | OSM/PBF -> Blender, edifícios/estradas/POI | candidato, código/licença/versão e execução ainda não verificados, não dependência. https://github.com/TUMFTM/MOSAIQ-OpenStreetMap-to-Blender-Add-On |
| osm_highway_junction / osm_street-roadrunner | geometria de cruzamentos, faixas e lancis Blender | candidatos; verificar licença, compatibilidade e comparar com física existente antes de adotar. https://github.com/p-schulz/osm_highway_junction ; https://github.com/p-schulz/osm_street-roadrunner |
| MRoadGen | Blender Geometry Nodes, taludes, marcas, curvas | candidato; avaliar bake glTF/PBR, licença e headless. https://github.com/MaartenNauta-Pathtrace/MRoadGen |

## Novas fontes

Infraestruturas de Portugal — Rede Rodoviária Nacional, SHP PT-TM06/ETRS89, CC BY 4.0, atualização 15.04.2026: https://dados.gov.pt/pt/datasets/rede-rodoviaria-nacional . Dados reais de eixo/atributos, não prova de geometria 3D da infraestrutura nem cobertura de vias municipais. A página confirma catálogo/licença, URL de ficheiro ainda não obtido; não pedir download antes de verificar recurso concreto. DGT BDNC/SMOS: https://smos.dgterritorio.gov.pt/cartografia-de-base e https://www.dgterritorio.gov.pt/dados-abertos ; verificar catálogo vetorial por cobertura, escala, licença e atributos. Município de Famalicão: pedir levantamento topográfico autorizado em DXF/GPKG/IFC se disponível; não presumir dados abertos ou adquirir cartografia paga. Nenhum download novo de dados reais efetuado.

## Implementação e reprodução

```sh
python -m unittest discover -s tests -p test_infrastructure_conversion.py -v
python tools/osm-json-to-xml.py data/pedome/pedome-osm.json outputs/osm --bounds -8.395 41.4105 -8.383 41.4195
python tools/osm-json-to-xml.py data/pedome/pedome-osm.json outputs/roads --bounds -8.395 41.4105 -8.383 41.4195 --mode roads
python tools/convert-infrastructure.py sumo outputs/roads/map.osm outputs/sumo --input-sha256 "$(sha256sum outputs/roads/map.osm | cut -d' ' -f1)"
python tools/convert-infrastructure.py osm2world outputs/osm/map.osm outputs/o2w --executable /caminho/osm2world.sh --input-sha256 "$(sha256sum outputs/osm/map.osm | cut -d' ' -f1)"
python -m pip install numpy==1.26.4 ifcopenshell==0.8.3.post2 cjio==0.10.1 triangle==20250106
python tools/generate-infrastructure-fixture.py outputs/fixture
python tools/ifc-to-glb.py outputs/fixture/wall.ifc outputs/ifc --origin 0 0 0 --input-sha256 "$(sha256sum outputs/fixture/wall.ifc | cut -d' ' -f1)"
python tools/convert-infrastructure.py cityjson outputs/fixture/wall.city.json outputs/cj --input-sha256 "$(sha256sum outputs/fixture/wall.city.json | cut -d' ' -f1)"
```

Converter OSM mantém IDs/nodes partilhados, rejeita conflito de coordenadas, exclui ways que não estejam inteiras no bbox e relações incompletas (relatório). Não produz recorte topologicamente completo; não utilizar para simulação de tráfego sem tratar fronteiras. Conversor GLB verifica estrutura, não recursos externos, triângulos e hashes. Inputs reais devem ter manifesto de licença/autorização separado (hash não é autorização). IFC usa geometria em metros, subtrai origem IFC XYZ e converte x,y,z -> x,z,-y; sem CRS global automático. Não sobrescrever original. CI workflow infrastructure-converters.yml: 3 jobs independentes (OSM/SUMO real, OSM2World real recorte igreja, IFC/cjio sintético), resultados pendentes. OSM2World só logs/contagens no artifact até licença dos assets do style revista; checksum do ZIP registado na primeira execução, fixar posteriormente. Não publicar modelos nem desenhos municipais privados.

## Ligação às ferramentas existentes

Dados vetoriais / BIM / CityJSON -> conversão -> manter IDs e atribuição -> alinhamento com TIN DGT e pelo menos 3 controlos independentes (asset-pipeline/Open3D, após #41) -> limpar geometria sem UV só com PyMeshLab -> Blender PBR/LOD, atlas sem destruir UV -> GLB/3D Tiles. Para novos muros/portões, usar medição LiDAR se houver suporte, senão defaults explicitamente estimados e notas do dono. Para postes, instancing; para muros, segmentos por altura do terreno, não construir sobre o eixo da estrada; para bridges, verificar deck e clearance, colisores só em PR separado. Medir sobreposição com roads/buildings, evitar duplicação do terreno, verificar alinhamento <=0,5m em controlos, capturas fixas, orçamento drawcalls/triângulos, 104m replay e teste de dispositivo. Este PR é laboratório de conversão; não é ainda cenário melhorado nem implementação das fases B/E/F. Não usar dados Google/Apple sem direitos. Nenhum merge ou Pages até resultados e revisão.
