# Alinhamento e união de modelos — Open3D / PyMeshLab

Decisão do dono: avançar sem adquirir LilyCaptureMerger. Ferramentas independentes e reutilizáveis; não substituir dados originais nem alterar o jogo nesta fase.

## Instalação

Python 3.12, ambiente isolado. Open3D 0.19.0 (MIT), PyMeshLab 2025.7.post1 (GPL-3.0), NumPy 1.26.4. Executar PyMeshLab como ferramenta offline separada; não incorporar bibliotecas no runtime do jogo. Fontes: https://github.com/isl-org/Open3D ; https://github.com/cnr-isti-vclab/PyMeshLab ; https://pypi.org/project/pymeshlab/2025.7.post1/ ; https://www.open3d.org/docs/0.19.0/tutorial/pipelines/icp_registration.html ; https://pymeshlab.readthedocs.io/en/latest/filter_list.html . Dependências SO Ubuntu: libgl1 libegl1 libopengl0 libglu1-mesa libxkbcommon0. CI guarda pip freeze; ainda não lock completo por plataforma.

```sh
python -m venv .venv-fusion
# ativar o ambiente
python -m pip install numpy==1.26.4 open3d==0.19.0 pymeshlab==2025.7.post1
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 QT_QPA_PLATFORM=offscreen python tests/mesh-fusion-fixture.py outputs/mesh-fusion-fixture
```

## Alinhamento

Inputs PLY de pontos 3D na mesma unidade métrica; origem local MapSlop X este, Y acima da base DGT, Z sul. GLB opcional autocontido, exatamente no mesmo frame da nuvem source. Manifestos JSON por input (source_type, license, author, reviewed_by, source_url_or_archive, files nome:SHA256). Controles JSON: initial_matrix 4x4 row-major (similaridade própria, sem reflexão/shear); check_source e check_target pelo menos três pontos não colineares, independentes do ajuste inicial e correspondentes. Preparar controlo inicial com asset-pipeline.py ou levantamento. ICP é refinamento local, não alinhamento global sem inicialização. Exemplo:

```sh
python tools/mesh-fusion.py register --source inputs/source.ply --target inputs/target.ply --source-manifest inputs/source-manifest.json --target-manifest inputs/target-manifest.json --controls inputs/controls.json --voxel .08 --max-error .05 --min-overlap .55 --output outputs/aligned
```

Opções --method colored (ambas as nuvens RGB, estimativa de normais, ICP colorido) e --glb inputs/source.glb (inventariado no manifesto source). 3 níveis voxel 4x/2x/1x, radius 2.5 voxels, até 60 iterações. Gate full-res bidirecional: overlap >= mínimo, RMSE <= voxel, erro máximo independente <= limite, sem piorar RMSE inicial. Resultados alinhados escritos só se PASS. GLB preserva BIN e materiais/UV originais, adicionando nó transformador; não faz atlas ou baking. ICP colorido usa RGB por vértice, não correspondência de texturas em imagens nem equivalência completa ao LilyCaptureMerger. O usuário deve fornecer nuvens com RGB coerente para usar esse modo.

## Limpeza de geometria

Para fundir peças previamente alinhadas, usar --mesh repetido no mesmo diretório e manifesto, com common_metric_frame_confirmed:true. A ferramenta concatena vértices/faces com offsets de índices e deduplica automaticamente. Exemplo de peça única:

```sh
python tools/mesh-fusion.py clean --geometry-only --mesh inputs/merged.ply --manifest inputs/manifest.json --output outputs/clean
```

Para várias peças: `python tools/mesh-fusion.py clean --geometry-only --mesh inputs/a.ply --mesh inputs/b.ply --manifest inputs/manifest.json --output outputs/merged`. Manifesto inclui geometry_only:true. Rejeita cor de vértice, UV e textura. PyMeshLab remove vértices duplicados exatos, faces degeneradas/duplicadas e vértices não referenciados; preservação do conjunto de triângulos não degenerados em coordenadas verificada. Não faz união booleana, remeshing, soldadura com tolerância nem eliminação de superfícies sobrepostas não idênticas. Para malha texturada, usar Blender/importador existente sem destruir seams. Não aceitar automaticamente orientação de faces duplicadas conflitantes.

## QA e próximos passos

Job mesh-fusion do toolchain-validation.yml instala e executa ambas bibliotecas reais; fixture de três superfícies assimétricas com sobreposição parcial, transformação conhecida, 4 controles independentes, ICP geometria/cor, rejeição de controles errados, limpeza 2 peças e preservação do BIN GLB. Evidência: report.json, source/target/clean PLY, GLB fixture e pip freeze. Execução ainda pendente ao criar. Após passar, testar duas capturas próprias/autorizadas de um edifício real (p.ex. igreja) e comparar correspondência, cor, geometria e colisão antes de integrar. Sem captura real adicional por agora; dados proprietários Google/Apple não utilizados. LilyTexturePacker/SurfaceScraper originais têm QA separado e dependem de ambiente compatível. Não comprar LilyCaptureMerger sem uma limitação concreta.
