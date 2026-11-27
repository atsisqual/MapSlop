# AGENTS.md — ponto de entrada para qualquer agente (Claude, Codex, Copilot, …)

Lê este ficheiro primeiro. Depois lê `docs/STATUS.md`. Não precisas de mais contexto de conversas anteriores: se algo não está no repositório, não existe para o projeto.

## O que é
MapSlop: simulador 3D em browser de localidades reais (condução livre em 3.ª pessoa). Primeiro mapa: Pedome, Vila Nova de Famalicão. Referência funcional: PortoSlop (não é dependência, não copiar código nem dados).

## Arquitetura atual (resumo)
- **Motor**: não está no repo. É o [Slop Nairobi](https://github.com/briankariuki/slop-nairobi) (MIT, Three.js) no commit `64b8599ae7dd7ba56ffbe68f19cc1423a9e7f903`, transformado em build por `tools/prepare-pedome.py` (substituições de texto + ficheiros gerados).
- **Dados de jogo versionados**: `data/pedome/` (OSM filtrado, CAOP, COS2025).
- **Arquivo geográfico bruto**: GitHub Releases em **rascunho** (só visíveis a quem tem acesso de escrita). Índice: `data/GEODATA-ARCHIVE.md`.
- **Pré-visualização pública**: https://atsisqual.github.io/MapSlop (workflow `pages.yml`).
- Decisões registadas em `docs/decisions/`. Investigação em `docs/research/` (histórico, não normativo).

## Mapa do repositório
| Caminho | Conteúdo |
|---|---|
| `tools/` | Scripts de dados e build (Python 3.10+, Node 22) |
| `data/pedome/` | Dados do mapa piloto + proveniência |
| `data/portugal/` | Instruções para o PBF nacional (o ficheiro não está no Git) |
| `data/reconstruction-sources.json` | Ferramentas 3D arquivadas (atenção: várias GPL/AGPL) |
| `.github/workflows/` | Build, validação no browser, Pages, aquisição de dados |
| `docs/STATUS.md` | Estado atual, próximos passos, bloqueios — **fonte de verdade** |
| `docs/decisions/` | ADRs: decisões e porquê |
| `docs/research/` | Notas de investigação datadas |

## Build local
```sh
make setup
make build
make test
make serve
```
Abrir http://localhost:8080/?webgl. Python 3.12.10, Node 22.16.0/npm 10.9.2, Git, Make. Ver .devcontainer. A pasta de saída não pode existir e `./pedome` não deve ser commitada. Usar OUT=outputs/nome para novos builds, sem destruir ficheiros existentes. Dados DGT e ferramentas offline não são necessários para P0.

## Regras invioláveis
1. Nunca commitar credenciais, cookies, URLs assinadas, HAR, ou atributos privados de cadastro.
2. Não copiar código, bundles ou dados do PortoSlop.
3. Licenças: o jogo é MIT-compatível. Ferramentas GPL/AGPL (Roofer, City3D, 3dfier, City4CFD, BlenderGIS) só como ferramentas offline separadas; o código delas nunca entra no runtime.
4. Atribuição obrigatória: OSM (ODbL), DGT (CC BY 4.0), Copernicus, Mr.doob/Nairobi.
5. Ficheiros > 50 MB ou dados brutos: Releases + manifest com SHA-256, nunca Git normal.
6. Não declarar nada "validado" sem teste executado e registado (comando + resultado).

## Fluxo de trabalho
1. Escolher uma tarefa em `docs/STATUS.md` → "Próximos passos" (ou uma issue).
2. Trabalhar num branch `agent/<tema>`; PR para `main`.
3. Depurar workflows com `workflow_dispatch` / `act`, não com commits "Retry …" sucessivos em `main`.
4. **Antes de terminar a sessão** (obrigatório):
   - Atualizar `docs/STATUS.md` (o que mudou, o que falta, bloqueios).
   - Se tomaste uma decisão com alternativas, criar `docs/decisions/NNNN-titulo.md`.
   - Se recebeste ficheiros do utilizador fora do repo, registar nome, tamanho, SHA-256 e onde ficou arquivado.
5. Commits: frase no imperativo, em português ou inglês, um tema por commit.

## Idioma
Documentação em português (PT-PT). Identificadores de código em inglês.
