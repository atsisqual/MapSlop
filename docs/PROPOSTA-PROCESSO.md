# Proposta de reorganização — processo, documentação e ferramentas

Data: 2026-11-27. Análise do estado em `9e663bd` (55 commits, 12 workflows, 7 scripts, 8 notas de investigação).

## 1. Diagnóstico

### O que está bem
- Proveniência exemplar: SHA-256, commits exatos, licenças e limites sempre registados.
- Disciplina honesta: distingue "testado" de "assumido".
- Reutilização em vez de reescrita (Nairobi) — decisão certa.
- Validação real no browser no CI antes de publicar.

### Problemas que impedem um agente novo de retomar
| # | Problema | Impacto |
|---|---|---|
| 1 | Sem `AGENTS.md`/ponto de entrada | Agente não sabe por onde começar |
| 2 | `README.md` contradiz o estado real (Slop New York, "não executável") | Agente parte de premissas erradas |
| 3 | Estado e decisões espalhados por 8 notas de investigação, PT/EN misturado | Reconstruir o contexto custa horas |
| 4 | O jogo não existe no repo: é gerado por *string patching* de um commit externo (`prepare-pedome.py`) | Frágil; impossível editar/rever o código do jogo diretamente |
| 5 | Releases em **rascunho** | Invisíveis a agentes sem acesso de escrita → dados inacessíveis |
| 6 | Links para runs do Actions como evidência | Logs/artefactos expiram (90 dias por omissão) |
| 7 | Ficheiros só na conversa (ZIP P0, uploads) | Perdem-se com a conversa |
| 8 | 12 workflows, 9 deles de aquisição pontual, disparados por push do próprio ficheiro; histórico "Retry …/Permit …" | CI usado como terminal de depuração; ruído |
| 9 | Sem `LICENSE`, `.gitignore`, dependências fixadas, comando único de build/teste | Ambiente não reproduzível |
| 10 | Sem backlog (issues/projeto) | "O que fazer a seguir" só existe na cabeça/conversa |

## 2. Estrutura proposta
```
AGENTS.md               ← entrada para agentes (CLAUDE.md = symlink)
README.md               ← para humanos: o que é, demo, como correr
LICENSE                 ← MIT + avisos upstream
Makefile | justfile     ← make setup / build / test / serve / data
docs/STATUS.md          ← estado vivo (atualizado em cada sessão)
docs/ROADMAP.md         ← P0…P3 com critérios de aceitação
docs/decisions/         ← ADRs
docs/research/          ← notas datadas (histórico)
docs/data-catalog.md    ← cada dataset: fonte, licença, release, hash, script
engine/                 ← motor vendorizado (git subtree do Nairobi) + patches
pipeline/               ← scripts de dados (ex-tools/), com testes
data/                   ← extratos pequenos + manifests
.github/workflows/      ← ci.yml, pages.yml, data-*.yml (manual)
.devcontainer/          ← ambiente idêntico para qualquer agente
```

## 3. Mudanças de processo (por prioridade)
1. **Protocolo de passagem de turno**: cada sessão termina com `STATUS.md` atualizado + ADR se houve decisão. Regra escrita em `AGENTS.md`.
2. **Vendorizar o motor**: `git subtree add --prefix engine https://github.com/briankariuki/slop-nairobi 64b8599 --squash`, depois converter os `replace()` do `prepare-pedome.py` em commits normais sobre `engine/`. O código do jogo passa a ser legível, revisível e testável; `git subtree pull` para atualizações upstream.
3. **Separar mapa de motor**: um `maps/pedome/manifest.json` (bbox, origem, spawn, sentido de circulação, estilos) lido pelo motor, em vez de valores embutidos no script.
4. **Backlog no GitHub**: Issues com templates (tarefa, bug, dataset) + GitHub Project com colunas. Um agente pode listar issues com `gh`.
5. **Branches + PR**: nada direto em `main`; CI de testes em cada PR.
6. **Workflows de dados só manuais** (`workflow_dispatch`); depurar com [`act`](https://github.com/nektos/act) localmente. Consolidar os 7 workflows DGT num só parametrizado.
7. **Evidência no repo**: resultados de testes/validações relevantes copiados para `docs/research/` ou como asset de release; não depender de links do Actions.
8. **Releases**: publicar as que já têm licença clara (OSM ODbL, ortofotos CC BY 4.0); manter rascunho só o que estiver em dúvida, e documentá-lo.
9. **Ambiente reproduzível**: `.devcontainer` ou [`mise`](https://mise.jdx.dev) com Python/Node/GDAL/PDAL fixados; `requirements.txt`/`package.json` com versões.
10. **Guardrails**: `pre-commit` com `gitleaks` (segredos) e verificação de tamanho de ficheiros.

## 4. Ferramentas para não partir do zero

### Pipeline geográfico
| Necessidade | Ferramenta | Nota |
|---|---|---|
| Recortar OSM | `osmium-tool`, `pyosmium` | Já previsto |
| Rasters DGT (MDT/MDS) | GDAL, `rasterio`, `rio-cogeo` | MDS−MDT para alturas; COG para servir |
| Nuvens LAZ | **PDAL** | Classes 2/3-5/6 → solo, vegetação, edifícios; altura de árvores |
| Estatística por footprint | `rasterstats`, `geopandas` | Altura de edifício = percentil MDS−MDT dentro do polígono |
| Telhados LoD2 | **Roofer** (já arquivado, GPL) | Corre offline; exporta só geometria (dados não herdam GPL) |
| Edifícios 3D a partir de OSM | **OSM2World** (MIT na lista) | Gera glTF com telhados/janelas |
| Cobertura de edifícios extra | Overture Maps Buildings | Complementa OSM onde faltar |
| Malha de terreno com LOD | `martini`/`delatin` (Mapbox), `quantized-mesh` | Terreno leve para telemóvel |
| Tiles de ortofoto | `gdal2tiles`, PMTiles | Texturas por nível de detalhe |
| Inspeção visual | QGIS | Validar antes de gerar jogo |

### Runtime / jogo
| Necessidade | Ferramenta |
|---|---|
| Física de veículos se Nairobi não chegar | Rapier (`@dimforge/rapier3d-compat`) com controlador de veículo |
| Streaming de mundo grande | 3D Tiles + `3d-tiles-renderer` (NASA-AMMOS, Three.js) |
| Tráfego/rotas | Reaproveitar London Loop/Wuhan (MIT) — já mapeados |
| Multiplayer (P3) | Colyseus |
| Testes no browser | Playwright (já usado) |

### Processo e agentes
| Necessidade | Ferramenta |
|---|---|
| Instruções multi-agente | `AGENTS.md` (lido por Codex, Copilot, Cursor, Claude; `CLAUDE.md` como symlink) |
| Backlog consultável por agentes | GitHub Issues + Projects, `gh` CLI |
| Execução local de workflows | `act` |
| Ambiente igual para todos | Dev Containers / Codespaces |
| Dados grandes versionados | Releases + manifest (atual) ou DVC se crescer |
| Segredos | `gitleaks` via pre-commit |
| Atualizar dependências | Renovate / Dependabot |

## 5. Plano de execução sugerido
1. **Hoje (documentação)**: `AGENTS.md`, `STATUS.md`, ADRs, corrigir `README.md`, `LICENSE`, `.gitignore`. ← incluído nesta proposta
2. **Semana 1 (estrutura)**: subtree do motor, `Makefile`, devcontainer, CI de testes em PR, consolidar workflows de dados.
3. **Semana 2 (backlog)**: migrar "Próximos passos" para issues; publicar releases com licença clara; `data-catalog.md`.
4. **Depois**: pipeline MDT/MDS/LAZ → produtos de jogo com testes.

