# MapSlop — Auditoria técnica, reconstrução 3D e infraestrutura

- Data: 2026-11-28 · Autor: agente Claude (sessão de auditoria) · Estado: proposta para revisão do dono
- Base auditada: `main` em `c9300db` (versão pública `255673d8bc58`) e PRs abertos #40 (`a4e4038`), #41 (`e8604ca`), #42 (`571d0ac`), #43 (`eae8c4b`).
- Este documento **não altera código funcional nem a versão pública**. Complementa `AGENTS.md`/`docs/STATUS.md`; onde houver conflito, o STATUS manda até o dono aprovar as recomendações abaixo.
- Registo tabular das ferramentas: [`ferramentas-estado.csv`](ferramentas-estado.csv).

---

## 1. Resumo executivo

1. **O que já funciona é bom e está publicado.** Terreno TIN DGT (788 KB gzip, erro ≤0,35 m nas estradas), estradas suavizadas, 371 alturas LiDAR, 17 telhados Roofer, 5 702 árvores LiDAR, ortofoto 25 cm em 64 tiles e circulação pela direita. Tudo isto passou por validação real e foi revisto pelo dono.
2. **Desde a publicação conjunta (#37), o projeto passou de "melhorar o jogo" para "acumular laboratórios".** Os PRs #40–#43 somam ~4 400 linhas e ~30 ferramentas novas. **Só um deles (#42, igreja) produz uma diferença visível no jogo**, e está bloqueado por um erro trivial (`KeyError: 'diff'` na API Poly Haven). A maioria dos "PASS" de #41 e #43 são **fixtures sintéticas** (níveis N4–N5 na escala da secção 2). Não provam qualidade nem fidelidade.
3. **Os testes não protegem a qualidade visual.** A ortofoto limpa V1 passou nos 13 critérios técnicos e piorou visivelmente a igreja e a mata. Só a revisão manual das capturas o detetou. Falta um gate visual com imagens de referência e aprovação explícita do dono.
4. **Riscos de licença e reputação no repositório público:**
   - O #43 instala `triangle==20250106`. O wrapper é LGPL, mas a biblioteca de Shewchuk só permite uso pessoal/académico, e o ADR 0012 já a tinha excluído.
   - O #41 contém código, testes e documentação para decodificar formatos de Google Earth e Apple Flyover (Earth-3D, LexSong, Earth Reverse Engineering, Flyover) e para usar MapsModelsImporter/RenderDoc. **Não há caminho legal para dados que alimentem estas ferramentas.** Recomendo retirá-las do repositório.
5. **Há referenciais geográficos a mais.** MOSAIQ trabalha em Web Mercator (escala ×1,33 a 41,4° N), SUMO em UTM 29N, OSM2World na sua própria projeção, e o jogo em PT-TM06 com origem na igreja. Cada conversor traz o seu referencial. Os testes atuais de alinhamento usam nós OSM como "verdade", o que **não é verdade de terreno**.
6. **O `docs/STATUS.md` deixou de ser fonte de verdade.** Novas secções foram sendo empilhadas no topo, e a secção "Em aberto" ainda diz que o relevo não está integrado. Um agente novo fica com informação contraditória.
7. **Recomendação central:** congelar a aquisição de ferramentas e aplicar a regra **"cada PR tem de mudar o que se vê no jogo, ou desbloquear diretamente algo que muda"**. As maiores melhorias visíveis **não precisam de dados novos**: iluminação e sombras, fachadas para os 527 edifícios, muros/portões/postes/mobiliário a partir do OSM com alturas LiDAR, e texturas de pormenor no chão.

---

## 2. Escala de maturidade usada

| Nível | Significado | Evidência mínima |
|---|---|---|
| N0 | Investigada | Nota/URL no repo |
| N1 | Instalada/arquivada | Versão + SHA-256 registados |
| N2 | Adaptador implementado | Script no repo |
| N3 | Teste unitário aprovado | Teste do adaptador com dados fabricados |
| N4 | Motor original executado | O executável/biblioteca original correu |
| N5 | Teste sintético aprovado | Fixture própria, gates semânticos |
| N6 | Teste com dados reais aprovado | Dados de Pedome, relatório e hashes |
| N7 | Integrado no jogo | Build jogável com o resultado |
| N8 | Validado visualmente pelo dono | Capturas antes/depois aprovadas |
| N9 | Em produção | Publicado no Pages |

Um workflow verde só prova o nível que o teste efetivamente exerce. **Nenhum nível ≥N6 se aplica a ferramentas testadas só com fixtures.**

---

## 3. Inventário auditado das ferramentas

Fontes: código e workflows dos branches, relatórios dos runs citados no STATUS e nos documentos de investigação, e as capturas que revi. Quando um resultado vem só do relatório escrito por outro agente e eu não verifiquei o artefacto, está marcado como *(reportado)*.

### 3.1 Reconstrução geométrica

| Ferramenta | Finalidade no MapSlop | Versão | Licença | E/S | Nível | Limitações e lacunas | Aplicabilidade e decisão |
|---|---|---|---|---|---|---|---|
| **Roofer** | Telhados LoD2.2 a partir de LAZ + footprints | v1.0.0 (binário arquivado) | GPL-3.0 (ferramenta offline; os outputs não herdam) | LAZ + GPKG → CityJSON/OBJ | **N9** (17 telhados) | 2/20 sem pontos; só 20 edifícios corridos; paredes lisas | **Principal para telhados.** Correr nos 527 edifícios (P2-3) |
| City3D | Reconstrução poligonal (paredes inferidas) | ZIP arquivado | GPL-3.0 | PLY → OBJ | N1 | Lento, focado em edifícios grandes; o Roofer já cobre | **Descartar** para o piloto |
| City4CFD | Domínios 3D para CFD | ZIP arquivado | GPL-3.0 | — | N1 | Objetivo errado (simulação de escoamento) | **Descartar** |
| 3dfier | Elevar polígonos 2D com LAS (estradas, separações, água) | imagem Docker oficial (digest por fixar) | GPL-3.0 | GPKG/SHP + LAS → CityJSON/OBJ | N5 (fixture; altura de muro correta só após o gate 05808d8) | Nunca corrido com LAZ DGT; a classe 17 usada é sintética; OBJ sem semântica rica | **Fallback** para muros/plataformas; a medição direta (PDAL HAG) é mais simples, ver §5 |
| Open3D | Registo/ICP, fusão de malhas | 0.19.0 | MIT | PLY/OBJ ↔ | N5 (ICP sintético 10,36 cm → 0,16 mm) *(reportado)* | Sem uso real; ICP precisa de duas nuvens reais (ex.: fotogrametria vs. LiDAR) | Manter como biblioteca; só útil quando houver fotogrametria própria (P4) |
| PyMeshLab | Limpeza e decimação de malhas | 2025.7.post1 | GPL-3.0 | OBJ/PLY ↔ | N5 *(reportado)* | Sobreposição com gltfpack/glTF-Transform no runtime | Usar só offline, para malhas fotogramétricas (P4) |
| Blender (bpy) | Importação, junção, bake, GLB | 4.0.2 / 4.2.0 / 4.4.0 | GPL (outputs livres) | vários → GLB | N5 | **Três versões diferentes** em workflows diferentes | Fixar uma versão (4.4 LTS ou a mais recente LTS) para todo o projeto |
| BlenderGIS | Georreferenciação em Blender | 2add45f | GPL-3.0 | — | N3–N4 *(reportado)* | Desnecessário: `asset-pipeline.py` + pyproj fazem o mesmo, testável sem GUI | **Descartar** da cadeia principal |

### 3.2 Fotogrametria

| Ferramenta | Finalidade | Versão | Licença | Nível | Observações | Decisão |
|---|---|---|---|---|---|---|
| COLMAP | SfM (poses + nuvem esparsa) | apt Ubuntu (não fixada) | BSD-3 | N5 (15/15 imagens sintéticas) *(reportado)* | Sem fotos reais de Pedome | P4: só com fotos próprias da igreja ou de drone |
| OpenMVS | Densificação, malha e textura | v2.4.0 | AGPL-3.0 | N5 (36,3 MB) *(reportado)* | Saídas muito pesadas; exigem decimação e atlas | P4, offline |
| OpenDroneMap | Pipeline aéreo completo | Docker 3.5.6 | AGPL-3.0 | N5 *(reportado)* | Só faz sentido com voo de drone próprio | P4 |

### 3.3 Infraestrutura e conversão

| Ferramenta | Finalidade | Versão | Licença | Nível | Lacunas | Decisão |
|---|---|---|---|---|---|---|
| **OSM2World** | OSM → GLB (muros, vedações, postes, sinais, mobiliário) | 0.4.0 (Java 17) | LGPL; estilo e texturas por omissão em domínio público/CC0 | **N6** (recorte da igreja: 341 meshes, 5 125 triângulos, **30,5 MB com 44 imagens**) | Referencial próprio; texturas pesadas; duplica edifícios e estradas já existentes | **Gerador secundário** só para classes que não fazemos (sinais, mobiliário): filtrar por tags, `gltfpack -tc`, alinhar por controlos |
| MOSAIQ | OSM → Blender | f73d030 | Apache-2.0 | N6 (geometria) | **Web Mercator: escala ≈1/cos(41,4°)=1,333**; materiais partidos em Blender 4.4 (`ShaderNodeTexMusgrave`) | **Descartar** da cadeia principal (escala errada, sobrepõe-se ao que já temos) |
| OSM Highway Junction | Malhas de cruzamentos em Blender | c138167 | Apache-2.0 | N6 (13 vias, 5 cruzamentos) | Sem relação com o TIN nem com a física; passeio fixo de 1,5 m | Avaliar contra o osm2streets (§5) antes de investir |
| OSM Street Roadrunner | Ruas e lancis em Blender | — | por verificar | N0 | — | Não investir enquanto o osm2streets não for avaliado |
| MRoadGen | Geometry Nodes para estradas | 50dec2e | CC0 | **N0** (o repo só tem LICENSE/README; o `.blend` não está disponível) | O "bake genérico de Geometry Nodes" do #43 **não é** o MRoadGen | **Parar**: não há asset para testar |
| SUMO netconvert | OSM → rede → OpenDRIVE | 1.28.0 (o 1.18.0 falhou) | EPL-2.0 | N6 (424 edges, 430 lanes, 161 junctions) | Referencial UTM 29N + netOffset; **teste de frame vermelho no último run** (46147123962) | Útil para tráfego NPC (P4); **não** para geometria visual |
| OpenDRIVE (.xodr) | Formato de estradas | 1.4 (via SUMO) | Norma ASAM | N6 (export) | Sem consumidor no jogo | P4, com tráfego |
| IfcOpenShell | IFC → GLB | 0.8.3.post2 | LGPL-3.0 | N5 (muro fixture 5×3×0,2 m) | Sem fonte IFC real; materiais perdidos | Dormente até a câmara fornecer BIM |
| cjio | CityJSON → GLB/OBJ | 0.10.1 | MIT | N5 | O export GLB **perde texturas** | Usar só para validar e converter outputs do Roofer |
| GDAL/OGR (+ rasterio, pyproj) | Reprojeção e formatos | 3.8.4 | MIT | **N9** (via o pipeline de terreno) / N5 (conversor GIS) | — | **Base canónica** de toda a cadeia |
| QGIS | Inspeção manual | — | GPL | N0 | Não automatizável no CI | Uso humano opcional |
| Geometry Nodes (bake) | Bake de redes de nós para GLB | Blender 4.4 | GPL (outputs livres) | N5 (2→10 triângulos) | Sem rede de nós real | Dormente |

### 3.4 Materiais, texturas e otimização

| Ferramenta | Finalidade | Versão | Licença | Nível | Observações | Decisão |
|---|---|---|---|---|---|---|
| OpenCV (Telea/NS) | Inpainting de objetos pequenos | 4.11.0.86 | Apache-2.0 | N6 (#40 V2) | Efeito quase nulo: só 2 297 px tratados, carros visíveis | Fechar o item A como "baixo impacto" |
| LaMa (ONNX) | Inpainting com IA | lama_fp32.onnx (SHA fixado) | Apache-2.0 | N5 (MAE 1,19 vs Telea 1,58) *(reportado)* | 208 MB, CPU lenta | Só se houver um caso real de valor |
| LilyTexturePacker | Atlas em Blender | 1.1.3 | GPL-3.0 (distribuído comercialmente) | N1 | Uma textura por material; sem PBR completo | **Substituir** por gltfpack/glTF-Transform (MIT) |
| LilySurfaceScraper | Importar materiais em Blender | 1.9.0 | GPL-3.0/MIT (LICENSE em falta no ZIP) | N1 | Pensado para uso interativo | **Substituir** por download direto ambientCG/Poly Haven com lockfile |
| Poly Haven | Materiais PBR | API | CC0 | **N2 partido** (`KeyError: 'diff'`) | Corrigir o parsing e fixar URL+SHA | Manter, com lockfile |
| ambientCG | Materiais PBR | API v3 | CC0 | N0 | Mais de 2 000 materiais, incluindo granito, reboco, telha e calçada | **Adotar** (P1-2/P1-3) |
| Atlas/UV/alinhamento próprios | `texture-atlas.py`, `asset-pipeline.py` | — | MIT (projeto) | N5 | Remaps não aplicados a PBR completo | Manter `asset-pipeline.py`; o atlas fica coberto pelo gltfpack |

### 3.5 Importação e visualização 3D

| Ferramenta | Finalidade | Licença | Nível | Decisão |
|---|---|---|---|---|
| NASA 3DTilesRendererJS | Streaming de 3D Tiles em Three.js | Apache-2.0 | N6 (tileset da igreja) | **Adotar** para a fase de blocos (P3) |
| RenderDoc | Captura de frames GPU | MIT | N4 (**job a falhar**, exit 139) | Retirar do CI; para o próprio jogo, usar **Spector.js** (MIT) no browser |
| MapsModelsImporter | Importar capturas Google Maps em Blender | GPL-3.0 | N0–N3 (só helpers) | **Retirar do repo**: a única finalidade é importar dados Google, e não há caminho legal |
| Earth-3D / Earth Reverse Engineering / LexSong | Decodificar formatos do Google Earth | MIT/vários | N3 (decoders com bytes sintéticos) | **Retirar do repo**: mesmo motivo |
| Apple Flyover (código Go) | Decodificar o Flyover | por confirmar | N3 | **Retirar do repo**: mesmo motivo |

> Justificação: os termos da Google Maps Platform proíbem construir modelos 3D, guardar ou derivar conteúdo das suas imagens, e os da Apple são semelhantes. Ter decoders e testes destes formatos num repositório público, sem nenhum uso legítimo possível, só traz risco e ruído para quem retomar o projeto. A visualização ao vivo via API (Photorealistic 3D Tiles) é uma questão diferente e fica fora deste PR.

---

## 4. Matriz: funcionalidades implementadas versus disponíveis

| Domínio | Já no jogo (N7+) | Disponível nos dados, ainda por usar | Ferramenta que o desbloqueia |
|---|---|---|---|
| Terreno | TIN DGT 0,5 m, carve rodoviário | Linhas de quebra de taludes (2 `retaining_wall` OSM), passeios elevados | road_carve + polígonos osm2streets |
| Estradas | Faixas Nairobi, perfis suaves, pintura pela direita | 34 `lanes`, 30 `sidewalk`, 15 `crossing`, 100 `surface` | **osm2streets** (polígonos de faixa, passeio e cruzamento) |
| Edifícios | 371 alturas LiDAR, 17 Roofer, fundações, cor de telhado | Roofer nos 527; fachadas; 16 `building:levels`; `buildings.yaml` | Roofer + gerador de fachadas generalizado |
| Muros e portões | — | 25 `wall`, 2 `retaining_wall`, 16 `gate`, 3 `hedge`, 1 `fence`; alturas no LAZ | **PDAL HAG** + extrusão própria |
| Energia | — | 20 `power=pole`, 10 `tower`, 3 `line`, 7 `minor_line`, 6 `transformer` | Instancing + catenária procedural |
| Mobiliário | — | 9 paragens, 4 bancos, 5 ecopontos, 3 marcos de correio, 1 armário técnico | Instancing de modelos CC0 |
| Escadas e túneis | — | 10 `steps`, 1 `tunnel=building_passage`, 1 `tunnel=yes`; **0 pontes** no piloto | Extrusão procedural por degraus |
| Vegetação | 5 702 árvores LiDAR | 3 sebes, classes COS2025, relvados (`leisure`/`landuse`) | Shader de solo + cercas vivas |
| Iluminação | Luz direcional simples | — | CSM (three.js addon) + AO (N8AO) + céu |
| Chão | Ortofoto 25 cm | Classes COS, máscaras OSM (asfalto, calçada, relva) | Texturas de pormenor ambientCG/Poly Haven |

---

## 5. Investigação: ferramentas complementares recomendadas

Só incluo ferramentas com um método de integração concreto no MapSlop.

| Ferramenta | URL | Licença | Atividade | Uso concreto | Integração |
|---|---|---|---|---|---|
| **osm2streets** | https://github.com/a-b-street/osm2streets · npm `osm2streets-js` | Apache-2.0 | Moderada (último push há ~1 ano: risco de manutenção) | Polígonos de faixa, passeio e cruzamento; marcações; junta faixas paralelas (resolve o caso da Via Intermunicipal) | Offline em Node/WASM: OSM XML do piloto → GeoJSON de faixas → `tools/build-street-geometry.mjs` → malhas + máscaras de chão + polígonos de colisão. Substitui larguras fixas do Nairobi |
| **PDAL** | https://pdal.io | BSD-3 | Muito ativa | Altura acima do solo (`filters.hag_delaunay`), recorte por buffer de linha OSM e estatística de altura de muros/sebes | `pdal pipeline` sobre os 4 LAZ: buffer de 0,4 m em torno de cada `barrier=wall` → p90 da HAG = altura medida |
| **Myria3D + modelo FRACTAL** | https://github.com/IGNF/myria3d · https://huggingface.co/IGNF/FRACTAL-LidarHD_7cl_randlanet | BSD-3 (código), Etalab 2.0 (modelo) | Ativa (IGN) | Reclassificar LiDAR em 7 classes, incluindo "estrutura permanente" e "ponte" | Experiência P4: inferência CPU num tile; comparar com a classificação DGT. Treinado em França, por isso pode errar em Portugal |
| **samgeo (SAM)** | https://github.com/opengeos/segment-geospatial | MIT (SAM: Apache-2.0) | Muito ativa | Segmentar a ortofoto: piscinas, painéis solares, pátios pavimentados, campos | P2: máscaras GeoPackage → materiais de chão e telhado. Pesado em CPU; corre offline num tile |
| **glTF-Transform CLI** | https://gltf-transform.dev | MIT | Muito ativa | Dedup, quantização, meshopt, KTX2, WebP, junção | Passo final obrigatório de todos os GLB |
| **gltfpack / meshoptimizer** | https://github.com/zeux/meshoptimizer | MIT | Muito ativa | Simplificação, LOD, junção de meshes, KTX2 | LODs dos edifícios e do output OSM2World |
| **KTX-Software (toktx)** | https://github.com/KhronosGroup/KTX-Software | Apache-2.0 | Ativa | Encoder Basis Universal | Dependência das duas ferramentas anteriores |
| **3d-tiles-tools + 3d-tiles-validator** | https://github.com/CesiumGS/3d-tiles-tools | Apache-2.0 | Ativa | Criar, validar e combinar tilesets | Fase de blocos (P3) |
| **three.js CSM** (addon oficial) + **N8AO** | https://threejs.org/docs/pages/CSM.html · https://github.com/N8python/n8ao | MIT · licença do N8AO por confirmar antes de usar | Ativas | Sombras do sol de qualidade; oclusão ambiente com modo "performance" para telemóvel | P1-1 |
| **ambientCG** | https://ambientcg.com | CC0 | Ativa | Granito, reboco, telha, calçada portuguesa, asfalto, relva | Lockfile URL+SHA; texturas de 1K/2K → KTX2 |
| **Streets GL** (referência) | https://github.com/StrandedKitty/streets-gl | MIT | **Sem manutenção** | Implementação completa de OSM 3D em WebGL2 (telhados por straight skeleton, muros, vedações, árvores) | Ler como referência; reutilizar módulos MIT isolados (ex.: `straight-skeleton`) com atribuição. **Não** trocar de motor |
| **Spector.js** | https://github.com/BabylonJS/Spector.js | MIT | Ativa | Inspeção de frames WebGL no browser | Substitui o RenderDoc para diagnosticar draw calls |
| Infraestruturas de Portugal — Rede Rodoviária Nacional | https://dados.gov.pt/pt/datasets/rede-rodoviaria-nacional | CC BY 4.0 | Atualizada a 15/04/2026 (segundo o #43) | Eixos de estradas nacionais | Baixo valor no piloto (as vias municipais não estão cobertas) |

**Projetos de cidades reais para motores de jogo (referência, não adoção):** Streets GL (MIT, WebGL2), OSM2World (LGPL, Java), Blosm (add-on Blender comercial) e plugins Cesium para Unreal/Unity (dependem de 3D Tiles; os tiles Google ficam fora). Nenhum substitui o pipeline atual. O Streets GL é o mais próximo do MapSlop e serve como checklist de funcionalidades.

---

## 6. O que os dados reais de Pedome permitem reconstruir

Legenda: **M** = medido, **I** = inferido, **P** = procedural.

| Elemento | Como | Natureza | Precisão esperada |
|---|---|---|---|
| Percurso dos muros | Linhas OSM `barrier=wall` (25) | M (traçado OSM) | ~1–3 m (qualidade do OSM) |
| Altura dos muros | PDAL: p90 da HAG num buffer de 0,4 m em torno da linha | **M** | ±0,3 m se houver ≥5 retornos/m; muros <0,8 m ficam ambíguos |
| Muros não mapeados | Linhas de HAG 0,8–3 m, estreitas (<0,6 m) e contínuas, fora de edifícios e vegetação | I | Candidatos a confirmar pelo dono; nunca publicar como reais |
| Desníveis entre propriedade e estrada | MDT 0,5 m: gradiente >45° ao longo de linhas → muro de suporte/talude | M/I | Bom para ≥0,5 m |
| Portões | Nós OSM `gate` (16), na interseção com o muro | M (posição) / P (forma) | — |
| Limites de passeio | `sidewalk=*` + osm2streets; confirmação por cor na ortofoto | I | ~0,5 m |
| Lancis | Degrau de ~0,15 m na borda do passeio | P | Abaixo da resolução do LiDAR aéreo |
| Postes | Nós OSM `power=pole` (20)/`tower` (10); confirmação por máximos estreitos de HAG | M | ~1 m |
| Cabos | Catenária entre postes da mesma `line`/`minor_line` | P (posições M) | Visual |
| Coberturas e alpendres | Classe 6 do LiDAR fora dos footprints OSM; Mapa de Construções 2024 | M/I | — |
| Elementos arquitetónicos | Não são mensuráveis por LiDAR aéreo (janelas, portas) | P + notas do dono | — |
| Materiais predominantes | Telhado: cor da ortofoto (já feito); fachada: notas do dono, fotos, paleta regional | I/P | — |
| Objetos não mapeados | Piscinas e painéis solares (samgeo na ortofoto), árvores (já feito) | I | — |

---

## 7. Pipeline integrado recomendado

```
[Aquisição]  DGT (LAZ, MDT/MDS COG, orto 25 cm) · OSM PBF · COS/CAOP · fotos do dono
     │  lockfile: URL, versão, licença, SHA-256 → Releases (rascunho)
[Normalização]  EPSG:3763 (PT-TM06) + altitudes ortométricas DGT
     │  GeoPackage (vetor) · LAZ 1.4 (nuvem) · COG (raster)        ← formatos canónicos
[Segmentação]  PDAL (HAG, classes DGT) · máscaras OSM · (opcional) samgeo/Myria3D
     │  GeoPackage de features com atributo origem = M | I | P
[Reconstrução]
     ├─ Terreno: terrain_tin + road_carve (já existe)
     ├─ Ruas: osm2streets → polígonos de faixa/passeio/cruzamento → carve + malhas
     ├─ Edifícios: Roofer (telhados) + gerador de fachadas (paredes, aberturas, socos)
     ├─ Muros/portões/sebes: extrusão própria com altura PDAL
     └─ Postes/cabos/mobiliário/sinais: instancing a partir de nós OSM
     │  GLB local: X este, Y acima da base DGT, Z sul, metros, origem na igreja
[Alinhamento]  asset-pipeline.py + controlos independentes (§10.2)
[Materiais]  ambientCG/Poly Haven (CC0, lockfile) → atlas via gltfpack
[Otimização]  glTF-Transform: dedup → weld → simplify (LOD1/LOD2) → meshopt → KTX2
[Divisão]  blocos de 250 m (manifesto + SHA) → 3D Tiles 1.1 (3d-tiles-tools) quando o mapa crescer
[Colisores]  geometria simplificada gerada da MESMA fonte (caixas/cascos), nunca da malha visual
[Runtime]  Nairobi/Three.js + InstancedMesh + CSM + AO + 3DTilesRendererJS (fase de blocos)
[Validação]  câmaras fixas → gate visual + percurso de condução + orçamento de desempenho + aprovação do dono
```

**Conversões a evitar** (perdem informação):
- OSM → Blender via MOSAIQ (Web Mercator, escala ×1,33) → GLB.
- CityJSON → GLB via cjio (perde texturas). Usar o OBJ do Roofer → Blender → GLB, ou o gerador próprio.
- IFC → GLB por tesselação (perde materiais e semântica): só quando não houver alternativa.
- OSM JSON → OSM XML → SUMO (UTM 29N) → OpenDRIVE → jogo: três mudanças de referencial para uma geometria que o osm2streets dá diretamente.
- OBJ como formato intermédio (sem PBR nem instancing): usar GLB.
- Cada ferramenta com o seu próprio referencial: o único contrato aceite é **EPSG:3763 + origem da igreja + altitude ortométrica**.

---

## 8. Estratégia por tipo de infraestrutura

| Tipo | Principal | Fallback | Quando usar o fallback | Porque não as alternativas |
|---|---|---|---|---|
| **Muros** | Extrusão das linhas OSM com altura PDAL (M), espessura de 0,25 m, material pela região | Altura de 1,2 m (P), marcada como estimada | Menos de 5 retornos LiDAR no buffer | 3dfier: mais complexo e sem ganho; OSM2World: alturas fixas e texturas pesadas; fotogrametria: sem fotos |
| Muros de suporte | OSM `retaining_wall` + quebra no TIN + face vertical | Talude no TIN | Sem linha OSM | — |
| Portões e vedações | Nós OSM `gate` cortam o muro; modelos CC0 instanciados | Abertura simples | — | — |
| Passeios e lancis | **osm2streets** (largura e lado) + degrau de 0,15 m + calçada CC0 | Regras atuais (#36: só onde o OSM tem passeio explícito) | O osm2streets falha numa via | O Nairobi gera passeios de 4,2 m por todo o lado (já corrigido no #36) |
| Estradas e cruzamentos | Perfis atuais (#32) + polígonos osm2streets para a forma dos cruzamentos | Faixas atuais | — | SUMO/OpenDRIVE: bom para tráfego, mau para malha visual; Junction (Blender): fora do TIN |
| Rotundas | osm2streets (`junction=roundabout`); **não há nenhuma no piloto** | — | — | Fica para a #35 |
| Pontes | **Não há no piloto** | — | — | Não investir agora |
| Túneis e passagens | 1 `building_passage`: buraco no edifício | Ignorar | — | — |
| Taludes | MDT 0,5 m (já no TIN) + material de terra/relva pela inclinação | — | — | — |
| Postes e cabos | Nós OSM + modelo CC0 + catenária procedural | Só os postes | Linha incompleta | OSM2World tem postes, mas traz a cena inteira |
| Sinalização | 1 `traffic_sign` + `stop` (3) + passadeiras (15) + regras (sinal de STOP nas entradas de prioridade) | Pintura no chão | — | — |
| Mobiliário | Nós OSM → instancing (paragens, bancos, ecopontos, marcos) | Omitir | — | — |
| Fachadas | Gerador procedural generalizado a partir de `facade_details.py`: pisos = altura/2,9 m, vãos a cada 2,5–3,5 m, soco de granito, reboco por paleta, override pelo `buildings.yaml` | Reboco liso | — | LoD3 real exige fotos ou varrimento ao nível do chão |
| Escadas | `highway=steps` (10) → degraus de 0,17 m | Rampa | — | — |
| Telhados complexos | Roofer → fit de planos (#42) | Duas ou quatro águas | Roofer falha | — |
| Materiais | ambientCG/Poly Haven (CC0) com lockfile, em KTX2 | Cores sólidas | — | Lily: GPL e interativo |
| Vegetação | Já feito (LiDAR) + sebes OSM | — | — | — |

---

## 9. Plano de melhoria visual de Pedome (sem dados novos)

Ordem por **impacto visível ÷ esforço**:

1. **Iluminação** (CSM, céu, nevoeiro, AO em modo "performance"): muda tudo o que se vê de uma vez.
2. **Fachadas em todos os edifícios**: hoje só a igreja tem aberturas.
3. **Muros, portões e sebes**: 25 + 16 + 3 elementos que definem a paisagem do Minho.
4. **Pormenor no chão**: calçada, asfalto e relva misturados com a ortofoto ao perto.
5. **Postes, cabos e mobiliário**: 30 postes e torres, 10 linhas, 22 objetos de mobiliário.
6. **Igreja (#42)**: corrigir o fetch e integrar.
7. **Passeios e cruzamentos com osm2streets**.

---

## 10. Critérios de aceitação e estratégia de testes

### 10.1 Situações em que os testes atuais passam com o resultado errado

| Falha | Teste atual | Porque não deteta | Correção |
|---|---|---|---|
| Regressão visual | `same_*`, `texture`, variância | Mede invariância e presença, não qualidade (a V1 da ortofoto passou) | Gate visual (§10.3) |
| Geometria no sítio errado | Controlos = nós OSM | Os nós OSM também podem estar errados | Controlos independentes, visíveis na ortofoto |
| Escala errada | Bounds e contagens | MOSAIQ em Web Mercator passa | Distâncias conhecidas entre controlos (erro <0,5 %) |
| Altitude ou datum | Comparação ao MDT só no terreno | Objetos importados não são comparados | Base do objeto vs. TIN em cada vértice de contacto |
| Materiais ou texturas perdidos | Contagem de imagens | Uma textura magenta também conta | Histograma da captura vs. referência; sem `FF00FF` |
| Duplicados | — | OSM2World + edifícios existentes não são comparados | Interseção 2D de footprints entre camadas (IoU >0,3 = duplicado) |
| Atravessar estradas ou edifícios | Condução de 104 m | Só um percurso | Teste de interseção de todas as malhas novas com polígonos de faixa e footprints |
| A flutuar ou enterrado | Fundações (só edifícios) | Muros, postes e mobiliário não são verificados | Mesma verificação para todas as classes |
| Colisor ≠ visual | Comparação em pontos junto à igreja | Amostragem local | Hausdorff colisor↔visual por objeto, ≤0,3 m |
| Desempenho móvel | SwiftShader | CPU de software, não reflete o telemóvel | Telemóvel real (#19) + Playwright com throttling como proxy |
| Fixture ≠ real | Muitos jobs do #41/#43 | Pastas e nomes "reais" com dados sintéticos | Campo `data_kind: synthetic|real` obrigatório no relatório; o CI recusa "real" sem hashes DGT/OSM |

Casos específicos:
- **OSM2World:** o teste só conta meshes e triângulos. Não verifica o referencial, os duplicados nem os 30 MB de texturas.
- **MOSAIQ:** "PASS" com escala errada.
- **OSM Highway Junction:** sem relação com o TIN.
- **SUMO:** o teste de frame está vermelho, e a métrica usa nós OSM como verdade.
- **3dfier:** a altura do muro só ficou correta depois de endurecer o gate, e mesmo assim com classe 17 sintética.
- **Open3D e PyMeshLab:** fixtures; nada no jogo depende deles.

### 10.2 Conjunto de controlos independentes (novo)

`data/pedome/controls.geojson`: 20 a 30 pontos identificáveis na ortofoto de 25 cm (cantos de passadeiras, esquinas da igreja, tampas, cantos de muros), com coordenadas EPSG:3763, altitude do MDT e um campo `verified_by`. Todos os conversores e objetos novos passam a ser avaliados contra estes pontos: **p95 ≤0,5 m em planimetria, ≤0,3 m em altimetria e escala com erro <0,5 %**.

### 10.3 Gate visual

- Câmaras fixas (JSON versionado): Rua das Bouças, igreja (rua e aérea de 30 m), mata, Via Intermunicipal, entrada norte. Duas resoluções: 1280×720 e 390×844 (telemóvel).
- Cada PR visual gera capturas `before` (versão publicada) e `after`, mais um diff (pixelmatch, ISC) e o SSIM (ssim.js, MIT). O relatório põe-nas lado a lado.
- **Merge só com a label `visual-approved` posta pelo dono.** Os agentes nunca a aplicam.
- Gates automáticos só bloqueiam desastres (imagem preta, magenta, céu a ocupar >80 % onde antes não ocupava). Não decidem a qualidade.

### 10.4 Orçamentos de desempenho

| Recurso | Medido hoje | Objetivo para o telemóvel (por validar no #19) |
|---|---|---|
| Download inicial | Terreno 788 KB + estradas 1,04 MB + resto por medir | ≤8 MB no piloto (≤3 MB por bloco na expansão) |
| Triângulos visíveis | Edifícios 100k (#30), mata 284k (#34) | ≤400k no total, ≤250k em média |
| Draw calls | Edifícios 10, mata 48 | ≤100 |
| Memória de texturas | Ortofoto ~15 MB (#36) | ≤96 MB com KTX2 |
| FPS | Nunca medido num aparelho | Mediana ≥30, p5 ≥20 num Android de gama média |

---

## 11. Backlog técnico

Formato: **Objetivo** · Ferramentas · Dados · Dependências · Ficheiros · Processo · Aceitação · Testes · Evidência visual · Riscos · Impacto.

### P0 — bloqueios críticos

**P0-1 Higiene do repositório e da fonte de verdade**
- Objetivo: um agente novo retomar o projeto sem ler 300 linhas contraditórias.
- Ferramentas: nenhuma nova. Dados: nenhuns. Dependências: nenhuma.
- Ficheiros: `docs/STATUS.md` (reescrito: estado → próximos passos → bloqueios, ≤120 linhas), `docs/history/2026-11.md` (o log atual, movido), `tools/registry.yaml` (uma entrada por ferramenta com o nível N0–N9 e o run de evidência), `AGENTS.md` (regra "cada PR muda o jogo ou desbloqueia diretamente").
- Processo: mover o histórico, reescrever o STATUS e gerar o registry a partir de `ferramentas-estado.csv`.
- Aceitação: o STATUS não contradiz a versão pública (verificado por script contra `build-report.json` do Pages); o registry tem as mesmas ferramentas que o CSV.
- Testes: `tools/check-repo.py` passa a validar o registry. Evidência visual: n/a. Riscos: perder informação histórica (mitigado: movida, não apagada). Impacto no jogo: indireto.

**P0-2 Retirar riscos de licença**
- Objetivo: nenhuma dependência ou código sem uso legítimo possível.
- Ficheiros: `.github/workflows/infrastructure-converters.yml` (remover `triangle`; se o cjio ou o IfcOpenShell o exigirem, usar `mapbox_earcut`), PR #41 (retirar `tests/earth3d-offline.cjs`, `tests/lexsong-offline.py`, `tests/flyover-math_test.go`, `docs/research/earth-3d-photogrammetry-20261128.md`, os jobs RenderDoc/MMI e as menções em `AGENTS.md`), ADR 0020 (decisão e motivo).
- Aceitação: `grep -ri "triangle==\|MapsModelsImporter\|LexSong\|Flyover\|earth-3d"` sem resultados fora do ADR; CI verde.
- Riscos: nenhum funcional. Impacto: reputação e clareza.

**P0-3 Contrato de referencial e controlos independentes** (§10.2)
- Ferramentas: pyproj, GDAL. Dados: ortofoto e MDT já arquivados.
- Ficheiros: `data/pedome/controls.geojson`, `tools/check-alignment.py`, `tests/test_alignment.py`, ADR 0021.
- Processo: o agente propõe 30 pontos com recortes da ortofoto; **o dono confirma** (campo `verified_by`); qualquer GLB passa por `check-alignment.py`.
- Aceitação: §10.2. Testes: teste com um GLB deslocado 1 m, que tem de falhar. Evidência: mosaico de recortes. Riscos: escolha de pontos ambíguos. Impacto: impede objetos fora do sítio.

**P0-4 Gate visual** (§10.3)
- Ferramentas: Playwright, pixelmatch (ISC), ssim.js (MIT).
- Ficheiros: `tests/visual/cameras.json`, `tests/visual/capture.mjs`, `.github/workflows/visual-gate.yml`, regra no `AGENTS.md`.
- Aceitação: o gate gera o relatório em todos os PRs com label `visual`; o merge é bloqueado sem `visual-approved` (branch protection definida pelo dono).
- Testes: reproduzir a V1 da ortofoto (#40) e confirmar que o relatório a mostra. Riscos: falsos positivos por ruído de render (mitigado: só bloqueia desastres). Impacto: alto.

**P0-5 Desempenho num telemóvel real (#19)**
- Ficheiros: `js/perf-overlay.mjs` (com `?perf=1`: FPS, frame time, `renderer.info`, memória JS), `docs/perf/README.md`.
- Processo: o dono abre `mobile.html?perf=1`, conduz 2 minutos e copia o JSON para uma issue.
- Aceitação: há pelo menos um registo de um aparelho real. Riscos: variabilidade entre telemóveis. Impacto: valida todos os orçamentos.

**P0-6 Fechar o #42 (igreja)**
- Corrigir o `KeyError: 'diff'` (estrutura real da API Poly Haven), criar o lockfile `materials.lock.json` (URL, resolução, SHA) e usar os ficheiros fixados se a API falhar; resolver o erro "door does not fit" com fallback; voltar a lançar `mode=roofs`.
- Aceitação: run real PASS; capturas antes/depois aprovadas pelo dono. Impacto: o marco principal do mapa.

### P1 — impacto visual elevado, sem dados novos

**P1-1 Iluminação**
- Ferramentas: three.js CSM (addon), céu (`Sky` do three.js), `FogExp2`, N8AO (licença a confirmar) ou o SAO do three.js.
- Ficheiros: `tools/lighting.mjs`, patch em `prepare-pedome.py`, `?quality=low|high`.
- Processo: sol a ~45° de elevação, 3 cascatas de 1024 em `high` e 2 de 512 em `low`; AO só em `high`.
- Aceitação: gate visual aprovado; em `low`, no máximo +8 draw calls e +2 ms de frame no proxy; o FPS em telemóvel não desce mais de 15 % (P0-5).
- Riscos: shadow acne no TIN (bias), custo em GPUs fracas. Impacto: muito alto.

**P1-2 Pormenor no chão**
- Ferramentas: ambientCG (CC0) com lockfile; shader de mistura.
- Dados: COS2025, máscaras OSM (asfalto, passeios, relva), ortofoto.
- Ficheiros: `tools/fetch-materials.py` (substitui o `fetch-cc0-materials.py`), `js/ground-detail.mjs`, `materials.lock.json`.
- Processo: a cor vem da ortofoto; o pormenor (normal map e luminância de alta frequência) vem do material da classe; desvanece a partir de 60 m.
- Aceitação: gate visual; ≤+16 MB de texturas KTX2; sem costuras nos tiles.
- Riscos: padrões repetidos (mitigado com rotação/escala aleatória por tile). Impacto: alto ao perto.

**P1-3 Fachadas para os 527 edifícios**
- Ferramentas: `facade_details.py` generalizado; materiais CC0; InstancedMesh (já existe).
- Dados: alturas (371 M / 156 P), `building:levels` (16), `buildings.yaml`.
- Ficheiros: `tools/facade_generator.py`, `tests/test_facade_generator.py`.
- Processo: pisos = round(altura/2,9 m); vãos por fachada voltada para a rua (frente = aresta mais próxima de uma via); porta na frente; soco de granito de 0,6 m; reboco a partir de uma paleta regional; override pelo YAML. **Sem falhas fatais**: uma abertura que não cabe é omitida e registada.
- Aceitação: 100 % dos edifícios processados, 0 exceções; ≤+60k triângulos e ≤+6 draw calls; gate visual aprovado.
- Riscos: uniformidade repetitiva (variar seeds por osm_id). Impacto: muito alto.

**P1-4 Muros, portões e sebes medidos**
- Ferramentas: PDAL (BSD), Shapely, extrusão própria.
- Dados: 4 LAZ, MDT, linhas OSM.
- Ficheiros: `tools/measure-barriers.py` (gera o GeoPackage com `height_m`, `n_returns`, `origin=M|P`), `tools/build-barriers.py` (gera o GLB), `tests/test_barriers.py`.
- Processo: buffer de 0,4 m → HAG p90; segmentar a linha de 2 em 2 m para seguir o terreno; o topo segue a altura medida; os portões cortam o muro.
- Aceitação: ≥80 % dos 25 muros com altura medida; nenhum muro sobre uma faixa (interseção com o polígono da estrada = 0); base a ≤0,1 m do TIN; gate visual aprovado.
- Riscos: muros cobertos por vegetação dão HAG falsa (excluir pontos de classe 3–5). Impacto: alto (é a "assinatura" visual do Minho).

**P1-5 Postes, cabos e mobiliário**
- Ferramentas: modelos CC0 (Poly Haven, Kenney) com lockfile; InstancedMesh.
- Dados: nós OSM (secção 4).
- Ficheiros: `tools/build-street-furniture.py`, `js/street-furniture.mjs`.
- Processo: uma instância por nó; catenária com flecha de 2 % do vão; colisores em cilindro.
- Aceitação: todos os nós representados; ≤+6 draw calls; nenhum objeto numa faixa.
- Impacto: médio–alto.

**P1-6 Passeios, lancis e cruzamentos via osm2streets**
- Ferramentas: osm2streets-js (Apache-2.0).
- Ficheiros: `tools/build-street-geometry.mjs`, `tests/street-geometry.test.mjs`, ADR.
- Processo: OSM XML do piloto → osm2streets → polígonos de faixa, passeio e cruzamento em EPSG:3763 → carve do TIN e malhas de passeio com degrau de 0,15 m e calçada CC0.
- Aceitação: a área de faixa difere ≤10 % da atual; o percurso de 104 m mantém os critérios de condução (#32); passeios só onde há tag ou inferência do osm2streets; gate visual aprovado.
- Riscos: projeto com pouca manutenção; casos falhados (mitigado com fallback para as faixas atuais por via). Impacto: alto.

### P2 — fidelidade e automação

- **P2-1 Roofer nos 527 edifícios**, com fit de planos (#42) e relatório por edifício. Aceitação: ≥70 % com LoD2.2 aceite (RMSE ≤0,5 m) e os restantes com fallback procedural.
- **P2-2 Segmentação da ortofoto (samgeo)**: piscinas, painéis e pátios → materiais. Aceitação: ≥80 % de precisão num conjunto de 50 objetos marcados pelo dono.
- **P2-3 Candidatos a muros não mapeados (PDAL)**: publicados só depois de o dono os confirmar (origem I).
- **P2-4 Fotos do dono e Mapillary próprio** → `buildings.yaml` e texturas de fachada CC BY-SA isoladas.
- **P2-5 OSM2World filtrado** só para sinais e mobiliário que o P1-5 não cobre; `gltfpack -tc`; verificação de duplicados.

### P3 — otimização e escalabilidade

- **P3-1 Passo final glTF-Transform/gltfpack** em todos os GLB (meshopt + KTX2). Aceitação: −50 % de bytes e −30 % de memória de texturas sem diferença visível no gate.
- **P3-2 LOD/HLOD** para edifícios e árvores (gltfpack `-si`).
- **P3-3 Blocos de 250 m e 3D Tiles** (3d-tiles-tools + 3DTilesRendererJS), validados no piloto antes de qualquer expansão (o pedido anterior de 3×3 km fica pendente disto).
- **P3-4 Colisores gerados da fonte**, com teste de Hausdorff contra o visual.
- WebGPU: só quando o Three.js WebGPURenderer suportar CSM e o Nairobi sem regressões. Não é prioridade.

### P4 — experimental

- Fotogrametria da igreja com fotos próprias (COLMAP → OpenMVS → PyMeshLab → Open3D ICP contra o LiDAR → gltfpack).
- Reclassificação do LiDAR com Myria3D/FRACTAL num tile.
- Tráfego NPC com SUMO/OpenDRIVE.
- IFC/BIM se a câmara municipal fornecer levantamentos.

---

## 12. Dados ou ficheiros adicionais realmente necessários

**Nenhum é obrigatório para P0–P1.** Os opcionais, por ordem de valor:

1. **Fotos do dono** (igreja: 4 fachadas; ~20 casas da Rua das Bouças e da zona da igreja), para `data/pedome/references/photos/` com o osm_id no nome. Licença: do dono. Finalidade: P1-3/P2-4.
2. **Gravação Mapillary própria** das ruas do piloto (app Mapillary, telemóvel no tablier, ~15 min). Licença CC BY-SA 4.0. Finalidade: referência de fachadas e de mobiliário.
3. **Confirmação dos 30 controlos** (P0-3) pelo dono: não é um ficheiro novo, é uma revisão.
4. *(Opcional, baixo valor no piloto)* Infraestruturas de Portugal — Rede Rodoviária Nacional (CC BY 4.0), https://dados.gov.pt/pt/datasets/rede-rodoviaria-nacional → arquivo `geodata-ip-rrn-<data>`.

Não peço ficheiros que já estão no arquivo (LAZ, MDT/MDS, ortofotos, OSM, COS/CAOP, toolchain).

---

## 13. Recomendação concreta para os próximos PRs

| PR | Recomendação |
|---|---|
| **#40** ortofoto limpa | **Merge** (seguro, sem regressão) e fechar o item A como "baixo impacto". Não investir mais |
| **#41** toolchain | **Não fazer merge tal como está.** Dividir: (a) manter `asset-pipeline.py`, `inpaint-local.py`, `mesh-fusion.py` e testes num PR "ferramentas offline" sem Google/Apple/RenderDoc; (b) fechar o resto (P0-2) |
| **#42** igreja | **Corrigir e fazer merge** (P0-6). É a única melhoria visível em curso |
| **#43** conversores | **Manter como laboratório, sem merge**, até o teste de frame estar verde e o `triangle` ter sido retirado. Retirar o MOSAIQ. Manter SUMO, IfcOpenShell e GDAL como ferramentas dormentes, documentadas |
| Novo | **P0-1 + P0-2** (higiene e licenças) num só PR documental |
| Novo | **P0-3 + P0-4** (controlos e gate visual) |
| Novo | **P1-1** iluminação → **P1-3** fachadas → **P1-4** muros → **P1-5** postes e mobiliário → **P1-2** chão → **P1-6** osm2streets |

**Regra proposta para o `AGENTS.md`:** *"Uma ferramenta nova só entra no repositório quando um PR a usar para mudar o que se vê no jogo. Investigação sem integração vai para `docs/research/` como nota, sem workflows nem dependências."*
