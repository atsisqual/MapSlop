# MapSlop

Simulador 3D em browser de localidades reais, com condução livre em terceira pessoa. Primeiro mapa: Pedome, Vila Nova de Famalicão.

**[Jogar a pré-visualização](https://atsisqual.github.io/MapSlop/)** · [Versão tátil](https://atsisqual.github.io/MapSlop/mobile.html?webgl)

## Estado atual

P0 experimental: mapa piloto OSM, 179 registos de vias, 527 edifícios, condução, HUD tátil, minimapa e reposicionamento. A versão publicada usa relevo plano e alturas maioritariamente estimadas. Não representa toda a freguesia. A reconstrução DGT ainda não está integrada. Estado, testes e bloqueios: [STATUS](docs/STATUS.md).

## Executar localmente

Requisitos fixados: Python 3.12.10, Node.js 22.16.0/npm 10.9.2, Git e Make, em Linux/macOS/WSL ou [devcontainer](.devcontainer/devcontainer.json).

```sh
git clone https://github.com/atsisqual/MapSlop.git
cd MapSlop
make setup
make build
make test
make serve
```

Abrir http://localhost:8080/?webgl. Setup instala as dependências e verifica os commits exatos de Nairobi e Three.js em .cache/mapslop; build usa OSM versionado e Three.js local, sem serviços de mapas. A pasta de saída não pode existir: para outro build, usar `make build OUT=outputs/pedome2`, e o mesmo OUT no test/serve. O build atual é plano. O devcontainer prepara o ambiente P0; GDAL/PDAL serão definidos quando o pipeline P1 for implementado.

Controlo: WASD/setas, comando ou botões táteis; M amplia o mapa; R repõe o carro. A publicação é feita pelo GitHub Pages, sem servidor de jogo.

## Diagnóstico gráfico no Android

A build pública 255673d8bc58 apresentou ruído cromático em taludes e riscas no pavimento em Chrome Android físico. A causa ainda não está comprovada; o hotfix não altera o TIN, os dados, a física ou as reconstruções. Validar a build candidata do PR na rota isolada de preview, sem promover alterações visuais à raiz antes da aprovação do dono.

Parâmetros (podem ser combinados):
- `?debug=1` — painel com backend efetivo, GPU/adapter quando exposto pelo browser, anisotropia máxima, filtros, POT, número de texturas cuja geração de mipmaps foi chamada, níveis GPU alocados (WebGPU), erros e sombras. Relatório integral: `window.mapslop.renderDebug()` na consola.
- `?renderer=webgl&debug=1` — WebGL2 obrigatório; o antigo `?webgl` continua a funcionar.
- `?ortho=0&debug=1` — sem pedidos de ortofoto; no runtime combinado mostra o TIN sem fotografia (solo liso).
- `?anisotropy=8&debug=1` — comparação com anisotropia antiga (limitada ao máximo do dispositivo); default Android 1, outros 8. `?paving=0` e `?shadows=0` isolam camadas e sombras.
- Sem parâmetro renderer, Three tenta WebGPU e pode recorrer a WebGL2. O painel mostra o backend real, não o solicitado. O browser pode ocultar a identificação GPU; consulta alternativa do adapter não prova que é o mesmo dispositivo. O contador de geração regista a chamada no backend, não garante que o driver produziu pixels corretos.

### Preview HTTPS antes do merge e gate

No PR, o workflow Pages valida os dados aprovados, aplica o overlay e executa a condução, o gate WebGL2 (SwiftShader), o gate WebGPU quando houver adapter e, se houver /dev/dri/renderD*, o gate WebGL2 sem SwiftShader (identificação GPU obrigatória). Sem GPU real, o relatório assinala essa limitação. Capturas e JSON: artefactos `android-render-evidence-candidate` (PR) e `android-render-evidence-preview` (dispatch). `mapslop-site-candidate` contém a build estática do PR. O gerador recupera os dois TIFFs DGT originais do draft, valida SHA, reprojeta offline a extensão de 132 m (128 m + gutter 2 m por lado) para near 512, mid 128, far 64; resoluções efetivas 0,2578125 / 1,03125 / 2,0625 m/px. O manifesto e hashes novos são arquivados num draft único por run; o WebP contém a imagem base e o backend gera mipmaps, sem redimensionamento JS.

Para lançar a preview do #46 antes do merge, usar o workflow já registado em main, mas com a definição do branch:

```sh
gh workflow run pages.yml --repo atsisqual/MapSlop --ref agent/android-render-hotfix -f preview_ref=agent/android-render-hotfix
```

Após o deploy passar: https://atsisqual.github.io/MapSlop/preview/agent/android-render-hotfix/mobile.html?debug=1 . O workflow resolve os dois SHAs uma vez, faz checkout/build/test separados e agrega um único artefacto Pages. A raiz é main; a faixa `PREVIEW <sha>` só aparece na preview. Não há promoção automática. O caminho conserva a barra de `agent/`; inicialmente apenas este branch é autorizado, outros precisam de contrato de build/overlay específico para não publicar silenciosamente código antigo. Se a environment `github-pages` só autorizar main, o dono tem de permitir este branch para o dispatch (ou integrar apenas infraestrutura de preview, não o hotfix visual). A preview é pública por URL, não privada. Um deploy normal de main remove previews anteriores. Confirmar SHA na faixa e `version.txt`; sem PASS e aprovação física não fazer merge.

Testar no mesmo telemóvel, na mesma posição e ângulo onde ocorreram os defeitos: automático, WebGL2, orto desativada e, se necessário, sem pavimento. Filmar/capturar taludes de perfil e chão próximo ao conduzir. Anexar painel e indicar GPU, versão Chrome e qual variante elimina o ruído/riscas. **Não fazer merge nem publicar #42/#45 antes de confirmação visual do dono.**

## Documentação e dados

- [AGENTS.md](AGENTS.md): regras obrigatórias para agentes.
- [Estado do projeto](docs/STATUS.md) e [decisões](docs/decisions/README.md).
- [Arquivo de dados](data/GEODATA-ARCHIVE.md), [dados piloto](data/pedome/README.md), [ferramentas de reconstrução](data/reconstruction-sources.json). Originais grandes nas Releases em rascunho, com acesso de escrita; não são distribuídos na demo.

## Créditos e licenças

Código MapSlop: [MIT](LICENSE). Base [Slop Nairobi](https://github.com/briankariuki/slop-nairobi), MIT declarado no README, adaptado de [Slop New York](https://github.com/mrdoob/slop-newyork) (Mr.doob, MIT); [Three.js](https://github.com/mrdoob/three.js), MIT. Inventário de assets upstream por concluir; não reutilizamos modelos capturados ou código/dados PortoSlop.

Dados © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), ODbL 1.0. DGT: Direção-Geral do Território, CC BY 4.0 quando confirmado para o produto; licenças contraditórias mantêm arquivos em rascunho. Relevo alternativo: Copernicus WorldDEM-30 © DLR e.V. 2010–2014 e © Airbus Defence and Space GmbH 2014–2018, disponibilizado pela UE e ESA no programa COPERNICUS. Ferramentas GPL/AGPL de reconstrução são processos separados, não dependências do runtime. Cada fonte mantém os seus próprios termos.
