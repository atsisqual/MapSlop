# Estado do projeto

> Atualizar no fim de cada sessão de trabalho. Última atualização: 2026-11-27 (reorganização documental).

## Fase atual: P0 — conduzir livremente em Pedome

### Feito
- Base de motor escolhida: Slop Nairobi `64b8599` (ver `decisions/0001`).
- Build Pedome com dados OSM reais (1 208 elementos, 527 edifícios, 179 vias), 67/67 testes upstream a passar.
- Pré-visualização no GitHub Pages com HUD táctil, minimapa, marcador da igreja, botão de reset; validação Chromium com toque a dois dedos no CI.
- Terreno alternativo com Copernicus GLO-30 (enquanto DGT estava bloqueado).
- Arquivo geográfico expandido (~8,4 km²): DGT MDT/MDS 0,5 m e 2 m, LAZ, ortofotos 2025 e históricas, vetores OGC, OSM — em Releases rascunho.
- Toolchain de reconstrução 3D arquivada (Roofer v1.0.0 testado em Linux).

### Em aberto / conhecido como incompleto
- Faixas e sinalização ainda orientadas à esquerda (herança Nairobi).
- Relevo DGT 0,5 m ainda não integrado no jogo.
- Edifícios: alturas estimadas; ainda sem MDS−MDT nem telhados.
- Inventário de licenças de assets do Nairobi por concluir.
- Licenças por coleção DGT inconsistentes → releases continuam rascunho.
- README corrigido; MIT/avisos upstream, .gitignore e symlink CLAUDE.md adicionados (tarefa 1). Inventário de assets permanece pendente.

### Próximos passos (por prioridade)
1. Integrar MDT DGT 0,5 m → terreno do jogo (substituir GLO-30).
2. Alturas de edifícios via MDS−MDT por footprint OSM.
3. Circulação pela direita: faixas, pintura, rotundas.
4. Árvores/vegetação a partir de LAZ (classes 3–5) e COS2025.
5. Ortofoto como textura de solo (tiles com LOD).

### Bloqueios
- Nenhum ativo. (Registar aqui: o quê, desde quando, o que desbloqueia.)

## Ficheiros recebidos fora do repo
| Ficheiro | Bytes | SHA-256 | Onde está arquivado |
|---|---:|---|---|
| portugal-261126.osm.pbf | 429 648 916 | 983c1ffc…5bc91 | Release `geodata-portugal-20261126` |
| MapSlop-Pedome-P0.zip | ? | 8b8cc496…ccb7cf2 | **Não arquivado** |
| HAR PortoSlop / map.json PortoSlop | — | — | Não arquivar (terceiros) |

## Passagem de turno — processo
- PR #1: verificação de seis documentos por script JS (links relativos existentes e blocos de código equilibrados); integrado.
- Tarefa 1: verificação estática de README/STATUS/LICENSE/.gitignore e symlink no Git; não altera o runtime. Não representa novo teste de condução.
