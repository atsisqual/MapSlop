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

## Execução e extensão — pedido de implementar todas as ferramentas úteis

Run 46145498302:
- OSM2World 0.4.0 PASS job 140980538971, recorte igreja 1047 nodes/171 ways, 341 meshes/341 primitives/5125 triângulos/29 materiais/44 imagens/30480444 bytes, SHA ae5b21302df0fdb18c8e0e96453ae0df56f6332aea6e50dc8dc74ec0b3e17b02. 796 ways excluídas por não caber inteiras, 5 relações incompletas; não é geometria fiel/levantamento. Falta alinhar CRS/estilo/licença.
- IFC/cjio PASS job 140980538849, IFC4 IfcWall 12 triângulos, bounds [0,0,-.2] a [5,3,0] m; CityJSON 12 triângulos, 3564 bytes GLB. Fixtures, não projetos reais.
- SUMO job 140980538969 FAIL (assert interno NBNodesEdgesSorter, ângulo fora [0,360) no 1.18.0). Troca para wheel oficial eclipse-sumo==1.28.0; sem alterar/remover elementos para forçar aprovação. Não declarar corrigido até teste.

Implementações adicionais:
- MOSAIQ (Apache-2.0, f73d030aecd3289007472a887d78aae2e74b6ea0) e OSM Highway Junction (Apache-2.0, c1381679da46c9e4700876c7840fa54a6c7f038b): tools/blender-infrastructure.py chama operador original MOSAIQ e pipeline original Junction, bpy 4.4.0, osmium 4.3.2, OSM da igreja, inventário de objetos, bounds, materiais e GLB. MOSAIQ Web Mercator com origem SW: escala horizontal não métrica no terreno, requer alinhamento; POIs desativados por falta prefabs licenciados. Junction circulação direita, largura passeio fallback 1.5, sem inferência de relva. Não substituir vias/colliders do jogo.
- GDAL/OGR: tools/gis-infrastructure.py converte camadas SHP/DXF/GPKG para GPKG, EPSG explícito, rejeita CRS desconhecido/contraditório, valida contagem e atributos. Fixture linha Z em EPSG3763, ida/volta WGS84, <1cm erro, preservação Z. Não equivale à instalação do GUI QGIS nem prova reprojeção vertical; DXF sem CRS precisa confirmação. Em produção inventariar TODOS sidecars SHP/DXF e não só hash do .shp.
- 3dfier: tools/3dfier-infrastructure.py gera LAS class2/17 com CRS EPSG3763, polígonos Road e Separation, configuração YAML; corre imagem oficial tudelft3d/3dfier por digest, offline, cópia de inputs; gate existência OBJ, faces, bounds Z conhecidos. Tag latest usada só para resolução inicial de digest; fixar digest observado depois do PASS. Classe17 sintética, não afirmar que DGT tem retornos apropriados. Ainda não reconstrução real de muros.
- MRoadGen (CC0, 50dec2e600980f5128cda8ab0d59f137d0d80095) exige Blender >=5.0 e collection MRoadGenerator num .blend; repo contém apenas LICENSE/README, não ficheiro. Página autor https://www.patreon.com/MaartenNauta/posts/this-free-tool-163179046 ; fonte repo https://github.com/MaartenNauta-Pathtrace/MRoadGen . Se necessário obter .blend oficial, enviar como anexo/draft privado e registar nome/tamanho/SHA/licença; não adivinhar URL direta nem assumir nome. Não implementado/testado sem o asset; útil para taludes e estradas visuais, não bloqueia restante pipeline.

### Reproduzir novos conversores
```sh
python -m pip install eclipse-sumo==1.28.0
# Usar comando sumo anterior sobre o mesmo OSM.
python -m pip install bpy==4.4.0 osmium==4.3.2 numpy==1.26.4
# checkout upstream nos commits acima, MOSAIQ pasta mosaiq_osm_vr
python tools/blender-infrastructure.py mosaiq /tmp/mosaiq_osm_vr outputs/osm/map.osm outputs/mosaiq --bounds -8.395 41.4105 -8.383 41.4195 --input-sha256 "$(sha256sum outputs/osm/map.osm | cut -d' ' -f1)"
python tools/blender-infrastructure.py junction /tmp/osm_highway_junction outputs/osm/map.osm outputs/junction --bounds -8.395 41.4105 -8.383 41.4195 --input-sha256 "$(sha256sum outputs/osm/map.osm | cut -d' ' -f1)"
# Ubuntu python3-gdal gdal-bin
/usr/bin/python3 tools/gis-infrastructure.py --fixture outputs/gis-fixture
/usr/bin/python3 tools/gis-infrastructure.py --input inputs/map.dxf --source-epsg 3763 --output outputs/gis
python -m pip install numpy==1.26.4 laspy==2.6.1 pyproj==3.7.2
python tools/3dfier-infrastructure.py fixture outputs/lift-input
docker pull tudelft3d/3dfier:latest
image=$(docker image inspect --format '{{index .RepoDigests 0}}' tudelft3d/3dfier:latest)
python tools/3dfier-infrastructure.py run outputs/lift-input outputs/lift-output --image "$image"
```
Novos jobs em infrastructure-converters.yml: blender-roads (matrix), gis-conversion, lidar-3dfier. Resultados pendentes. Testes iniciais 2/3 PASS; sem integração, sem publicação. Prioridade após gates: comparar segmentos reais de muros/portões e lancis com TIN/LiDAR e capturas, escolher a ferramenta por evidência e evitar duplicar objetos.

### Resultados efetivamente observados

Run 46145829568 (commit 55e2fbf), e repetição 46145984476 (1b72f2e): OSM2World 0.4.0, MOSAIQ, OSM Highway Junction, SUMO 1.28.0 e IFC/cjio PASS nos respetivos ensaios. SUMO: piloto inteiro (166 ways rodoviárias inteiras, 855 nós, 34 excluídas), 424 edges /430 lanes/1090 OpenDRIVE roads/161 junctions inferidos; UTM29WGS84, netOffset -550568.25,-4584532.83, sem validação de tráfego integral. MOSAIQ: recorte igreja 171 ways/1047 nodes, 147 meshes/2614 triângulos, 205340 B, SHA d0d01a24014590ef9b6eb41e856063f947f8fa1d2c9f0639d0b558272107fa21. Junction: 13 roads,21 road meshes,5 junctions,14 connectors,41 meshes/926 tris,79724 B, SHA 3a6a2ea015620c35d57bbf94d4a022807a58a34c5c95bc901afdb2930934f13c. OSM2World: bin ZIP SHA c05b37920d29c26710a06e30c170ca62e5e8ea653cccbbb3243dfc7e5d20b899 agora fixado; resultado idêntico 341 meshes,5125 tris,44 images,30480444 B. GLB style license audit still required. IFC/cjio fixture 12 triangles each. GIS e 3dfier ainda FAIL: 46145984476 jobs 140982044596 (Dataset iteration) e 140982044553 (duplicate --yaml). Correções 3d66cd0 e 347799d; digest container sha256:95a8e1defe7d8f2e105758bc5ed96e7964f97bda6fb07e577c8ff67cf9dd8264 fixado; novo CI pendente. Não equiparar testes de conversão a precisão geográfica ou integração no jogo.

### Geometry Nodes: bridge genérico para MRoadGen e ferramentas semelhantes

`tools/bake-infrastructure-nodes.py`: bpy 4.4.0 para fixture; ficheiro .blend verificado SHA256, scripts auto desativados, rede Python bloqueada; usar ambiente isolado e assets revistos, isto não é sandbox de segurança. Rejeita libraries externas, imagens FILE não packed, UDIM/sequências, instâncias não realizadas; exporta só malhas/curvas/superfícies visíveis avaliadas por depsgraph, materiais/atributos preservados quando suportados pelo exportador glTF, frame e contagem de triângulos, bounds finitos, 2M triangles/100MB ceilings. Não altera ficheiro de origem. Fixture próprio extrude strip 5m×3m×0.2m, gate bounds, triângulos antes/depois e contagem GLB real. Novo job geometry-nodes-bake. MRoadGen original exige Blender >=5 e collection MRoadGenerator: não testado sem .blend oficial; após receber ficheiro, avaliar compatibilidade, preparar curva/terreno e realizar instâncias, bake com versão 5 compatível e --collection quando adequado. Este conversor não configura automaticamente a ferramenta nem reproduz seu algoritmo de taludes. Não necessário adquirir agora.

```sh
python -m pip install bpy==4.4.0 numpy==1.26.4
python tools/bake-infrastructure-nodes.py fixture /tmp/road.blend
python tools/bake-infrastructure-nodes.py bake /tmp/road.blend outputs/baked-road --sha256 "$(sha256sum /tmp/road.blend | cut -d' ' -f1)"
```

Run 46146179120: GDAL PASS job 140982640251, 3.8.4, erro roundtrip 9,9476e-10m, Z preservado, CRS desconhecido rejeitado; Geometry Nodes PASS job 140982640260 Blender4.4, 2→10 triângulos, bounds [0,0,0]–[5,3,.200000003], GLB 1568B SHA 8e17c346972fb4ec050ba8ab16cc5a14a99568c786d1f45bd3ac1aac46282f02. 3dfier PASS técnico anterior job 140982640106, OBJ SHA1090bfac28b45420819e9ba801aefb315ec0e4b2a8ec65e3e993818e442b227f, 8 vertices/6 faces, bounds [-50000,180000,100]–[-49980,180004.6,100.41]; wall height not recovered (~101.3–101.7 expected). Strengthen gate in 05808d8: fixture LAS single return flags, Separation uses class17 only (synthetic, not actual DGT class attribution), compare per-material heights Road vs Separation, require both; retest pending. No actual wall reconstruction PASS yet. Do not publish or integrate these surfaces into TIN/physics.
