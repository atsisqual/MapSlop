# MapSlop — investigação de reutilização
Data: 2026-11-27. Prioridade: conduzir livremente em terceira pessoa pelas ruas reais de Pedome. PortoSlop é referência funcional, não uma dependência.

## Decisão técnica provisória
Não reimplementar a física, controlador, câmara, tráfego ou renderização antes de avaliar implementações licenciadas. Começar por testar Slop Nairobi (MIT) como base de adaptação geográfica; comparar com Slop Wuhan (MIT), que usa Slop Taipei e já acrescenta corridas de táxi. Manter o importador MapSlop existente como protótipo; substituir/adaptar o formato apenas depois de testar o pipeline upstream. Não combinar motores de física ou versões de Three.js indiscriminadamente.

## Evidência e candidatos
| Projeto | Evidência disponível | Licença / decisão |
|---|---|---|
| [Slop New York](https://github.com/mrdoob/slop-newyork) | [PORTING.md](https://github.com/mrdoob/slop-newyork/blob/main/PORTING.md) identifica módulos de veículos, física, câmaras, controladores, edifícios, colisões, áudio, gamepad; importador OSM de edifícios/árvores. Grelha de ruas original específica de Manhattan. | MIT; base comprovada documentalmente |
| [Slop Nairobi](https://github.com/briankariuki/slop-nairobi) | OSM e Copernicus GLO-30; vias arbitrárias com lanes, one-way, bridge/tunnel/layer; terreno; caminhada, carro, bicicleta, helicóptero; testes de controladores, câmaras e declives; ferramentas fetch-geodata.sh, fetch-terrain.mjs, build-geodata.mjs. | MIT declarado no README; dados OSM ODbL e condições próprias de elevação; candidato principal |
| [Slop Wuhan](https://github.com/LightYearZh/slop-wuhan) | Táxis com passageiros, navegação, pagamento virtual, pontes e túneis; origem em Taipei; UPSTREAM.json e testes. | MIT; avaliar versão e avisos upstream; candidato para missões/economia |
| [NEON BAY](https://github.com/L1vsun/NEONBAY) | Física de veículos, derrapagem, trânsito, polícia, pedestres, dinheiro por manobras, testes de rampas e pontes. | MIT; fonte secundária para mecânicas, não o mapa |
| [Luxembourg City](https://github.com/donmutti/city) | [CLAUDE.md](https://github.com/donmutti/city/blob/main/CLAUDE.md): src/world/model.js, terrain.js, src/game/car.js, camera.js, traffic.js, pedestrians.js, police.js, signals.js; vias reais, entregas, colisões, relevo, níveis de pontes. | Licença não identificada na página consultada; estudar arquitetura, não copiar |
| [San Verde](https://github.com/ryanfitzpatrickio/san_verde) | Three.js WebGPU, garagem, tuning, som por RPM, suspensão e aderência, tráfego e exploração a pé. | Licença não confirmada; referência funcional apenas |
| [Mini GTA 6](https://github.com/imNauman/mini-gta6) | Rapier, entrar/sair de carros, NPC, polícia, missões, dinheiro e save local. | Licença não confirmada; referência funcional apenas |
| [Joyride](https://github.com/nitzangames/joyride) | Carros, entrar/sair, destruição de veículos, testes com Puppeteer e node:test. | Licença não confirmada; referência funcional apenas |
| [Arcade 3D](https://github.com/webgl-games/arcade-3d/) | Destruição de edifícios, colisões, multiplayer, inventário/loja. | MIT declarado; avaliar compatibilidade e assets |
| [Colyseus](https://github.com/colyseus/colyseus) | Framework Node.js para multiplayer autoritativo; [demo Three.js](https://github.com/colyseus/realtime-tanks-demo). | MIT; opção futura, requer servidor |
| [Rapier](https://github.com/dimforge/rapier) | Motor físico e controladores de veículos/personagens. | Apache 2.0; só adotar se física upstream insuficiente |
| [Awesome Slop Cities](https://github.com/zz85/slop-cities) | Índice de forks e variantes; London Loop, Taipei, Singapore, Berlin, etc. | Usar para descoberta de mais componentes, não como licença global |

## PortoSlop
- Jogo: https://porto.tremocogames.com/
- Publicação: https://www.reddit.com/r/aigamedev/comments/1y5jcde/portoslop_the_gta_we_deserve_but_in_porto/
- Publicação PT: https://www.reddit.com/r/PORTUGALCARALHO/comments/1y5ejbz/portoslop_o_gta_que_merecemos_mas_no_porto/
- Página pública observada: HUD de velocidade, mapa, chat, menu, reconexão. Snippets do Reddit descrevem OSM e monumentos feitos a partir de fotografias, cerca de 27 km². Não se confirmou repositório público, licença nem código dos servidores. As páginas completas Reddit não abriram; não se fez decompilação do cliente. A existência de uma feature semelhante em terceiros não implica equivalência com PortoSlop.
- Outras referências comunitárias: [St Louis](https://www.reddit.com/r/threejs/comments/1xnzbk4/i_built_a_whole_drivable_city_in_threejs_real_st/) (Rapier, OSM, streaming), [Driving Berlin](https://www.reddit.com/r/threejs/comments/1y2mv9e/using_threejs_for_a_berlin_city_driving_game/) (gémeo digital). São relatos, não testes independentes.

## Matriz funcional e fases
P0 condução livre: reutilizar runtime Nairobi; adaptar bbox e origem, tráfego à direita, nomes de vias, spawn; testar rede de estradas não ortogonal, rotundas, sentidos únicos, cruzamentos, pontes/túneis, colisão de edifícios, terreno, câmara em terceira pessoa, volante/teclado/gamepad conforme suporte. Não exigir condução apenas sobre o eixo da estrada. Primeiro mapa piloto ~1 km², expandir após validação.
P1 mundo vivo: tráfego, peões, minimapa, dia/noite, áudio, caminhada e entrar/sair de veículos. Avaliar módulos upstream e NEON BAY.
P2 mecânicas GTA: entregas e táxis, economia, polícia, garagem/tuning, personalização, saves. Wuhan para táxis; NEON BAY para perseguições e parâmetros de veículos. Verificar código/ativos e compatibilidade antes de transplantar.
P3 expansão: barcos (ainda sem implementação reutilizável selecionada), aeronaves (helicóptero upstream; avião por selecionar), destruição (Arcade 3D; persistência e colisões por integrar), multiplayer (Colyseus), chat, sincronização de economia e autoridade do servidor.
P4 detalhe local: pontos de referência, fachadas, vegetação e mobiliário local; dados abertos portugueses, modelos originais/licenciados.

## Critérios de aceitação antes de anunciar uma versão jogável
- Fixar SHA do upstream, reter LICENSE/NOTICE, inventariar licenças dos assets e dados; não copiar de repositórios sem autorização explícita.
- Reproduzir build e testes upstream sem alterações, guardar versão de Node/Three.js e resultados.
- Importar Pedome com dados reais e relatório de contagens; verificar origem, orientação, cobertura, vias ligadas e vias de diferentes níveis.
- Confirmar arranque no browser sem erros de consola; teste determinístico de aceleração, travagem, marcha atrás, direção e câmara.
- Conduzir manualmente pelo mapa piloto em vários cruzamentos, rotundas e declives; colisões e respawn; medir FPS em hardware real.
- Não chamar versão jogável até passar execução e interação reais.

Estado: investigação documental, não auditoria integral de código nem teste executado. Nenhum código de terceiros importado neste commit. Escolha final da base dependente de testes e licenças. O código MapSlop existente continua sem validação de importação real.
