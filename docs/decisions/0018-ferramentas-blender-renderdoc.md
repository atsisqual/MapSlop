# ADR 0018 — Ferramentas offline Blender e RenderDoc

Estado: proposta implementada parcialmente; teste sintético pendente. Não altera runtime, publicação ou ordem A–F.

## Referência

Pedido do dono: aproveitar [MapsModelsImporter](https://github.com/eliemichel/MapsModelsImporter). O README descreve captura GPU por [RenderDoc](https://github.com/baldurk/renderdoc), importação em Blender, união de blocos por LilyCaptureMerger, atlas por LilyTexturePacker, e refere BlenderGIS (já arquivado em data/reconstruction-sources.json). O autor adverte contra uso comercial/redistribuição do conteúdo capturado. Licença de código ou ferramenta nunca transfere direitos dos dados.

## Decisão

- Não instalar nem usar o importador de capturas Google/Mapy, nem obter amostras de capturas externas, imagens ou geometria Google. Não usar captura de terceiros/PortoSlop. Respeitar AGENTS.md.
- RenderDoc é ferramenta de diagnóstico opcional para frames do nosso próprio MapSlop (backend suportado, máquina de teste, sem sessão autenticada). Inspecionar draw calls, shaders, texturas, overdraw e recursos de GPU; guardar métricas, não redistribuir capturas. Não exigir RenderDoc na CI headless nem afirmar desempenho físico com SwiftShader. A captura GPU não foi executada.
- Blender + BlenderGIS offline: partir dos dados DGT/OSM já autorizados, Roofer GLB e fotos com proveniência/autorizações; manter referenciação métrica e origem. Preparar igreja (C) e objetos (E/F) com malhas dedicadas, triangulação, UV, materiais PBR e LOD. Ferramentas GPL não entram no runtime MIT. As notas do dono prevalecem sobre valores procedurais; conservar evidência de altura/footprint.
- Aproveitar os conceitos de união de blocos e atlas, não importar os add-ons Lily sem verificar versão/licença. Consolidar só por materiais/licença compatíveis e preservar costuras/UV, não unir a totalidade da cidade. Texturas CC BY-SA ficam separadas, com créditos.
- Ferramenta inicial tools/blender-asset-audit.py: GLB de origem autorizado com manifesto de proveniência e SHA-256, auditoria de triângulos, vértices, materiais, dimensões de imagens, bbox e criação de candidato LOD com decimation; exportar e reimportar GLB, gate de redução e desvio bbox. Sem edição da origem, sem publicação automática. Um gate bbox não prova silhueta/UV/fidelidade; revisão visual e física obrigatória antes de integração. CI separada usa fixture sintética, sem dados privados; versão do Blender da distribuição registada, não pin de produção.
- No item C, reavaliar Roofer para OSM 149406360 e comparar modelo dedicado Blender com LiDAR, fotografias autorizadas e câmaras fixas. Escolher solução por fidelidade e orçamento, não pela existência de ferramenta.

## Execução

Fixture local:

```sh
blender --background --factory-startup --python-exit-code 1 --python tools/blender-asset-audit.py -- --fixture --output outputs/blender-qa
```

Para um GLB autorizado: substituir --fixture por --input ficheiro.glb --provenance provenance.json; manifesto exige source_type (DGT_LiDAR, DGT_orthophoto, owner_authorized_photos ou authorized_open_asset), source_url_or_archive, license, author, sha256 e reviewed_by. Só utilizar dados autorizados pelas regras do projeto. O manifesto é declaração de revisão, não verificação jurídica automática.

Alternativas rejeitadas: capturar Google para redistribuição, adicionar dependências de ferramentas comerciais sem revisão, publicar LOD sem teste visual, iniciar C antes de A/B aprovados.
