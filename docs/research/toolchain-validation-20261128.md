# Validação da cadeia de ferramentas de reconstrução

Objetivo do dono: não basta investigar; cada método precisa de ferramenta reutilizável, execução de teste e evidência. Não confundir "código implementado", "teste sintético aprovado", "motor externo executado" e "dados reais integrados". Não modificar o jogo/Pages neste PR. Todos os ensaios de CI usam apenas fixtures próprias ou software/pesos explicitamente licenciados; não usar tokens de mapas.

## Matriz e comandos

| Ferramenta | Implementação | Teste mínimo / evidência |
|---|---|---|
| Blender | tools/blender-asset-audit.py; tools/blender-import-assets.py | auditoria/decimação: Blender 4.0.2 PASS 46137932115, 2988→1500 triângulos, drift 0; novo teste OBJ + MTL + PNG, join por material e GLB |
| Georreferenciação (alternativa offline ao fluxo BlenderGIS) | tools/asset-pipeline.py | transformação de similaridade 3D com controles independentes, limiar 0,5 m; testes de rejeição de controle errado, colinearidade, hash errado e GLB autocontido |
| Atlas e união (conceitos Lily) | tools/texture-atlas.py; tools/blender-import-assets.py | atlas sem reamostragem, gutters, UV clamp e rejeição de UV repetido; join só material único comum. Remaps exportados, ainda não aplicados automaticamente a todos os materiais PBR |
| NASA 3DTilesRendererJS | #42; tools/asset-pipeline.py gera estrutura multi-bloco | run real 46138928840 PASS, GLB/3D Tiles igreja, RMSE 0,43179 m; testes de boxes/URI da estrutura multi-bloco, ainda não teste de streaming da cidade |
| OpenCV | #40, tools/inpaint-local.py | Telea e Navier-Stokes com máscara pequena, erro versus ground truth sintético e igualdade exata fora da máscara; #40 CI corrigido 46140172093 PASS, V2 real pendente |
| LaMa | tools/inpaint-local.py | ONNX Runtime CPU, modelo FP32 Carve fixo 512², SHA256 1faef5301d78db7dda502fe59966957ec4b79dd64e16f03ed96913c7a4eb68d6; teste real de inferência e MAE/igualdade; não executar TorchScript/pickle desconhecido; resultado do novo job pendente |
| COLMAP | tools/reconstruct-photos.py colmap | 15 imagens sintéticas de superfícies não coplanares, CPU features/matching/mapper; >= metade registadas, >=30 pontos; versão apt registada; job pendente |
| OpenMVS | tools/reconstruct-photos.py openmvs | v2.4.0 binário Ubuntu oficial, COLMAP+undistort+InterfaceCOLMAP+dense+mesh+texture; verificar digest de release quando fornecido, ficheiros de output; job pendente |
| OpenDroneMap | tools/reconstruct-photos.py odm | Docker 3.5.6, resolver digest e executar por digest sem rede; 15 vistas aéreas sintéticas, geo.txt UTM, OBJ georreferenciado e GeoTIFF exigidos; job pendente |
| RenderDoc | tools/renderdoc-audit.py; tools/renderdoc-fixture.c | captura OpenGL própria via SDL/API, replay real, contagem draw/resources; job pendente; captura real de MapSlop precisa hardware/local |
| Earth-3D | upstream MIT 54194adca25a266582200a8aa114ef1288b1e40b; tests/earth3d-offline.cjs | compilar módulo puro LatLonBox e testar geometria, sem instanciar NodeManager; job pendente. Não é teste de decoder, streaming ou acesso a dados Google |
| MapsModelsImporter | upstream 70fca735bd42b1785356622a07e13c2604ff9af1 | não instalado/testado como add-on; fluxo equivalente de ingestão de OBJ/GLB autorizado, não equivale a importação de RDC Google. Compatibilidade de versões específica; falta captura legal apropriada e ambiente |
| retroplasma Earth / LexSong / Apple Flyover | upstream 35af10d0e1a133dc217d63c59545a917f4e5fc3f / cd5c4d66760d44d1388ee9634a8d3a35876b284c / ce5f9c6fa873e65709c31c604b8296e35da1db85 | código estudado; nenhum endpoint proprietário, autenticação, extração ou decoder completo integrado/testado. Licenças do código e direitos dos dados não confirmados em todos. Importação de modelos já legalmente obtidos por formatos abertos é separada |
| BlenderGIS | ZIP já inventariado em data/reconstruction-sources.json | add-on ainda não executado; georreferenciação independente não prova BlenderGIS |
| LilyCaptureMerger/LilyTexturePacker | referências de conceitos | add-ons originais não instalados; não declarar testados; licença/versão e autorização pendentes |

## Executar

CI automática no PR #41: workflow `.github/workflows/toolchain-validation.yml`, jobs separados asset-import, colmap, openmvs, odm, lama, renderdoc, earth3d-offline. Cada job tem artefacto de evidência próprio; não tratar "skipped", falha de dependência ou apenas teste de compilação como PASS do motor. Depois do merge, `gh workflow run toolchain-validation.yml --repo atsisqual/MapSlop` (antes de existir em main, usar CI de PR). O CI principal executa igualmente os unit tests.

```sh
python -m pip install numpy==2.2.6 Pillow==11.3.0 opencv-python-headless==4.11.0.86
python -m unittest discover -s tests -p test_asset_toolchain.py -v
python tools/generate-photo-fixture.py outputs/photos
python tools/reconstruct-photos.py colmap --input outputs/photos --manifest outputs/photos/manifest.json --output outputs/sfm
# Com executáveis OpenMVS v2.4.0 instalados no PATH:
python tools/reconstruct-photos.py openmvs --input outputs/photos --manifest outputs/photos/manifest.json --output outputs/mvs
python tools/generate-photo-fixture.py outputs/aerial --aerial
docker pull opendronemap/odm:3.5.6
image=$(docker image inspect --format '{{index .RepoDigests 0}}' opendronemap/odm:3.5.6)
python tools/reconstruct-photos.py odm --input outputs/aerial --manifest outputs/aerial/manifest.json --output outputs/odm --odm-image "$image"
python tools/generate-obj-fixture.py outputs/obj
blender --background --factory-startup --python-exit-code 1 --python tools/blender-import-assets.py -- --input outputs/obj/fixture.obj --manifest outputs/obj/manifest.json --output outputs/glb
python tools/texture-atlas.py outputs/obj outputs/obj/manifest.json outputs/atlas
```

A ferramenta de alinhamento recebe GLB autocontido, manifesto JSON e controles: `source`, `target` (>=3 não colineares), `check_source`, `check_target` (>=1 independente). Coordenadas fonte glTF Y-up, destino X este/Y acima da base DGT/Z sul; não usar EPSG/ECEF diretamente nem confundir datum. `python tools/asset-pipeline.py asset.glb manifest.json controls.json outputs/aligned`. Não modifica original. Produz GLB alinhado e relatório. Para inpainting: `python tools/inpaint-local.py --image image.png --mask mask.png --truth original.png --output outputs/inpaint` (truth opcional, só ground truth sintético ou validação controlada); acrescentar checkpoint ONNX e SHA/licença se disponível. Para RenderDoc executar com Python das bindings locais, `python tools/renderdoc-audit.py frame.rdc manifest.json report.json`; manifest source_type own_mapslop_capture, reviewed_by e sha256. Captura do nosso jogo num ambiente suportado, sem credenciais e sem dados de terceiros.

## Proveniência e aquisição

- COLMAP CLI: https://colmap.github.io/legacy/3.9/cli.html; OpenMVS: https://github.com/cdcseacave/openMVS/releases/tag/v2.4.0; ODM: https://hub.docker.com/r/opendronemap/odm/tags e https://docs.opendronemap.org/outputs/ ; geo: https://docs.opendronemap.org/geo/ . Registar versões executadas, executáveis e hashes; versão apt/digest resolvido ainda não lock permanente de produção.
- LaMa ONNX Apache-2.0: https://huggingface.co/Carve/LaMa-ONNX/blob/main/lama_fp32.onnx, 208 MB, SHA256 acima, download https://huggingface.co/Carve/LaMa-ONNX/resolve/main/lama_fp32.onnx. Código original https://github.com/advimman/lama. Teste descarrega diretamente, sem intervenção do dono. Não redistribuir peso sem conservar licença/atribuição. O workflow não publica o modelo.
- RenderDoc: https://renderdoc.org/builds ; API https://github.com/baldurk/renderdoc/blob/v1.31/renderdoc/api/app/renderdoc_app.h . Captura real do próprio jogo e relatório ficam locais.
- Dados reais adicionais necessários para fotogrametria: imagens sobrepostas próprias/autorizadas, preferencialmente geolocalização e controles independentes, não ortofoto única. https://www.dgterritorio.gov.pt/atividades/cartografia/fotografia-aerea ; https://www.dgterritorio.gov.pt/loja/fotografia . Disponibilidade de fotografias originais DGT/IFAP 2025 e autorização de transformação em 3D ainda pendentes; pedir ficheiros específicos só após confirmação.
- Manifesto de inputs: source_type, license, author, reviewed_by, source_url_or_archive, files {nome:SHA256}; nomes e bytes inventariados, inputs originais fora de Git normal. Fotos e modelos autorizados são locais/privados. Nenhum Google/Apple nem material PortoSlop em CI, Git, Releases, Pages; direitos do fornecedor necessários para processamento proprietário, mesmo pessoal.

## Execuções observadas e extensão da validação — 28/11/2026

Run 46140715436: asset-import job 140965790046 PASS (5 unit tests; Blender 4.0.2 OBJ 2 objetos/2 triângulos -> 1 objeto/2 triângulos, drift 0, textura preservada, GLB SHA e53c5339941153fd87d4528b3aeafbf6933ad7c45e341e0ef248e9d4d985b5a6); LaMa job 140965790052 PASS (checkpoint SHA verificado, MAE Telea 1,5773, NS 1,3318, LaMa 1,1894; RMSE 1,9365/1,7360/1,4180, pixels exteriores iguais); COLMAP job 140965790060 PASS (15/15 imagens, 13818 pontos); Earth-3D job 140965790055 PASS apenas matemática pura; ODM job 140965789992 PASS (OBJ geo 37440465 bytes, ortho TIF 70256 bytes, imagem Docker digest sha256:56be7b87a5ef3abfc0bb2afe88df839862fd18c41d26ca13672bf79cd2d59dd1 agora fixado); RenderDoc job 140965789857 FAIL por pacotes indisponíveis no Ubuntu 24.04, mudar runner para 22.04, API header v1.18, apenas captura sintética nossa em ambiente descartável (não usar a versão antiga com capturas desconhecidas; ver https://ubuntu.com/security/notices/USN-9124-1). OpenMVS ainda em execução à última consulta.

Novos testes: compilar e executar upstream MeshDecoder/BufferGeometryUtils (vertices, índices, varints, tri strips) com bytes sintéticos; LexSong octant_to_latlong.py sem rede; Go Flyover pkg/mth/mth.go com dados sintéticos e GOPROXY=off. Não equivale a exportador completo, captura de dados Google/Apple, textura proprietária ou autenticação. BlenderGIS 2add45f e MapsModelsImporter 70fca73: Blender oficial 4.2.0 com SHA oficial, registar add-ons, testar CRS/roundtrip BlenderGIS e helpers originais MMI addMesh/addImageMaterial com triângulo e imagem próprios. Não chamar importCapture nem processar RDC de terceiros; o parser de captura é específico do serviço, integração completa continua não validada. Scripts e jobs versionados. Versões/licenças: MMI README/header MIT, LICENSE raiz GPL-3.0; manter execução offline separada, não incorporar código. LexSong/retroplasma direitos de redistribuição não confirmados; checkout temporário para teste puro, não arquivar código derivado.

LilyCaptureMerger e LilyTexturePacker são add-ons comerciais do autor (páginas oficiais https://eliemichel.gumroad.com/l/KSvXuu e https://eliemichel.gumroad.com/l/DFExj ; preços observados $9+ e $6+, respetivamente). Para testar originais o dono pode adquirir/descarregar ZIP de cada um e conservar licença/versão, enviar como ficheiro para validação local ou draft privado autorizado; nome exato só visível após compra. Não guardar código comercial em Git público nem redistribuir; não comprar sem autorização. O atlas e a união por material próprios já passaram, não equivalem ao alinhamento por correspondência de texturas do LilyCaptureMerger nem a instalação dos add-ons originais.

## Lily — ficheiros do dono (28/11/2026)

Ver [inventário JSON](lily-owner-archives-20261128.json). Recebidos TexturePacker 1.1.3 e SurfaceScraper 1.9.0, não CaptureMerger. TexturePacker GPLv3 per LICENSES, Python 3.7 x64, Blender mínimo 2.83, base color preferencial, uma textura/material/UV por objeto e sem UDIM; não usar para atlas PBR completo sem verificar. SurfaceScraper GPLv3 indicado em __init__, ficheiros individuais MIT, LICENSE.md referenciado ausente no ZIP; lxml 5.2.1 CPython 3.11. Fontes AmbientCG, Poly Haven, CGBookcase, Textures.one, IES Library e local; cada asset exige licença própria. A versão local pode acrescentar PBR de granito, asfalto, reboco, solo e vegetação, não prova correspondência real ao edifício. Teste original local PASS: seis mapas, seleção de variantes, pastas, metadados, erro caminho inexistente; sem rede ou Blender, preferência injetada. Preservar originais separados.

```sh
python -m pip install Pillow requests lxml
python tools/lily-archive-qa.py /caminho/ZIPs outputs/lily-archive-report.json
blender-2.83 --background --factory-startup --python-exit-code 1 --python tools/lily-blender-qa.py -- /caminho/LilyTexturePacker-v1.1.3-64bit.zip outputs/lily-packer-report.json
blender-4.2 --background --factory-startup --python-exit-code 1 --python tools/lily-blender-qa.py -- /caminho/LilySurfaceScraper-v1.9.0.zip outputs/lily-surface-report.json
```

Substituir nomes de executáveis por caminhos locais. Testes Blender ainda pendentes, executar em ambiente descartável offline. Não abrir binários fornecidos fora do ABI; nunca contornar incompatibilidade renomeando .so/.pyd. Receção na conversa não é arquivo GitHub; dono pode criar draft `toolchain-lily-owner-20261128` e anexar os dois ZIPs exatos, nunca publicar, SHA confere antes da execução. Repositório permanece público. Não houve download/compra adicional.
