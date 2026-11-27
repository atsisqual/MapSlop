# Evidência de CI — 2026-11-27

## Tarefa 7 — PR #13

- Run 46044980735, job 140661859061, head `6bd7d1ca6ca89c7ab9dd0f9a3dace8fd8bfcffa0`: **success**, todos os passos concluídos.
- [Run original](https://github.com/atsisqual/MapSlop/actions/runs/46044980735) (referência suplementar; os resultados abaixo ficam em Git).
- Ambiente reproduzível e lockfile: OK.
- Verificação offline do repositório: 61 links internos, 9 workflows YAML, 116 digests de assets arquivados, 4 hashes de pequenos datasets.
- `tests/test_dgt_workflow.py`: 6/6 testes passaram (assinatura inválida, corrupção, parcial verificado, caminhos/duplicados/vazios, modos e parâmetros inválidos). Resultado: Ran 6 tests in 0.007s; OK.
- Compilações fixture e Pedome real e execução npm test: três relatórios de 67 pass / 0 fail.
- BUILD_REPORT: fixture=false; flat=true; bbox=[41.4105,-8.395,41.4195,-8.383]; roads=179; buildings=527; nodes=113; links=134; estimatedBuildings=511.
- Chromium headless: desktop condução, distância 2.1776351719997 m; velocidade após toque 1.4410232578772608; multiTouch=true; touchRelease=true; success=true. Inclui verificação de HUD, minimapa, erros WebGL/JavaScript e pedidos externos.
- Não foi feita aquisição DGT live neste PR. Os testes do workflow usam fixtures; não validam autenticação real, disponibilidade futura ou upload real. Não houve publicação de releases. O teste Chromium não equivale a medição em dispositivo móvel físico.
