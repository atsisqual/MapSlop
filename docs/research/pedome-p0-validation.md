# Pedome P0 — resultados e decisão (2026-11-27)

## Testes executados localmente
Arquivos ZIP fornecidos pelo utilizador, SHA identificada nos comentários dos ZIP, Node.js 22.16.0. Comando em cada raiz: `node --test tests/*.test.*`.

| Base | Commit | Passou | Falhou |
|---|---|---:|---:|
| London Loop | 3c7525e03804322f9c957984c88020a00e447a51 | 66 | 45 |
| Slop Nairobi | 64b8599ae7dd7ba56ffbe68f19cc1423a9e7f903 | 67 | 0 |
| Slop Taipei | 1d70708fc92a088b779c8c0e22677adb64966a1b | 9 | 0 |

Londres: 24 falhas Missing import stub ./geo-frame.js; 3 testes referem city-config.js inexistente; 7 testes Overpass com ficheiro de chamadas inexistente; outras falhas de asserts/imports/preload. Não interpretar como 45 defeitos de jogo. Taipei tem cobertura muito menor. Nairobi é a base inicial escolhida para condução livre, terreno e colisão, e Londres é candidato para missões e mecânicas adicionais. Não misturar dois runtimes nem duas versões de Three.js.

## Implementação
[tools/prepare-pedome.py](../../tools/prepare-pedome.py) adapta o snapshot Nairobi para uma saída separada. Retira os dados e modelos capturados da cidade original, preserva avisos do upstream, substitui origem, caixa geográfica, estimativas de altura para casas, spawn e UI inicial. Reutiliza o gerador de ruas, terreno, edifícios, controlador, câmaras e colisores. Liga teclado e gamepad. Sem tráfego automático, sem multiplayer, sem serviços de terceiros. A configuração indica circulação pela direita e o spawn usa a direita, mas os algoritmos de faixas/sinalização de Nairobi ainda são orientados à esquerda: validar/adaptar antes de ligar tráfego e rever a pintura de estrada. Os materiais/procedural roofs e faixas continuam com limitações do upstream.

A área piloto de ~1 km² está perto da Igreja de São Pedro de Pedome (OSM way 149406360, 41.41501,-8.38809; https://mapcarta.com/pt/W149406360). BBox S,W,N,E 41.4105,-8.395,41.4195,-8.383. Não é a fronteira administrativa. A caixa é uma escolha de implementação reversível.

Teste do adaptador: dados sintéticos explicitamente rotulados, 2 vias, 1 edifício, 5 nós, 4 ligações. Passaram novamente 67/67 testes após ajustar exclusivamente os metadados da rua fictícia no fixture dos testes para o novo spawn; asserts originais mantidos. Geração de malha de ruas: 8 arestas visuais, 264 triângulos de asfalto; rede de tráfego deixa 1 aresta após SCC, o que demonstra por que a rede de renderização não deve ser filtrada pela rede de IA. A renderização no browser não foi validada: Chromium bloqueou navegação localhost por política administrativa. A obtenção de OSM falhou neste ambiente por DNS e HTTP 406 pelo serviço de acesso. Não anunciar Pedome jogável. Não foram usadas imagens Google Street View.

## Compilar
Python 3.10+ e Node 22/npm, snapshot Nairobi indicado. A pasta de saída não pode existir. Na raiz MapSlop:
```sh
python tools/prepare-pedome.py /caminho/slop-nairobi-main ./pedome
python -m http.server 8080 --directory ./pedome
```
Abrir localhost:8080; opção ?webgl para testar fallback. Usa CDN pinado do original. --osm-json caminho.json permite importação offline; --dem-json permite fornecer DEM conforme esquema upstream; --flat permite protótipo sem relevo real, identificado na interface. --fixture só para testes. --three-vendor experimental, compatibilidade não validada. Para distribuir o jogo será necessário confirmar inventário de licenças dos recursos procedurais e dependências (README Nairobi declara MIT, ZIP Nairobi não inclui LICENSE separado; avisos de copyright do Mr.doob nos ficheiros). Não utilizar assets capturados ou dados PortoSlop.

Workflow [Pedome P0 build](../../.github/workflows/pedome-p0.yml) executa o fixture, tenta obter OSM/DEM reais e executa o build/testes num runner com rede; run inicial https://github.com/atsisqual/MapSlop/actions/runs/46028051942 confirmado em fila no momento da escrita. Só publica relatório, não o jogo. Ainda não concluído. A publicação de build e testes interativos é uma fase posterior.
