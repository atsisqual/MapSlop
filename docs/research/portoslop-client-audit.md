# PortoSlop — análise estática do cliente (HAR, 2026-11-27)

## Método e limites
HAR disponibilizado pelo utilizador, 32 entradas, 26 do domínio do jogo. Extração e inspeção local dos corpos JavaScript presentes, sem executar o jogo, contactar WebSocket, usar debug ou interagir com terceiros. Não publicar HAR, tokens, dados de contas, assets ou código proprietário. Não foram encontrados sourcemaps nos oito ficheiros JS capturados. Não existe licença verificada para o código do jogo (Three.js é MIT, não implica que o restante seja MIT). Esta análise descreve conceitos e interfaces observadas, para implementação independente.

## Inventário dos recursos
| Recurso | Bytes descodificados | Responsabilidade observada |
|---|---:|---|
| main-Dlp29ogQ.js | 1253507 | Bootstrap, renderização, mundo paginado, HUD, rede e previsão local |
| models-C3iHxFJv.js | 2548609 | Three.js r170, física, geometria, veículos, personagens, terreno, colisões |
| mundo-CFvCYsQM.js | 206832 | Configurações Porto/Ferreira, economia, locais, texto |
| veiculos-obra-j8qWhcwP.js | 1962843 | Web Worker de preparação de modelos de veículos |
| lingua-DFfFolac.js | 17477 | Localização pt/en, módulo inglês carregado a pedido |
| saltos-BpOXC_ad.js | 1087 | Diagnóstico de saltos; não utilizado nesta análise |
| modulepreload-polyfill-B5Qt9EMX.js | 711 | Compatibilidade Vite |
| preload-helper-D7HrI6pR.js | 1017 | Preload dinâmico Vite |
| estilos-porto.json | 524626 | Classificação arquitetónica de 33630 edifícios |
| manifest.webmanifest | 515 | Metadados de instalação da aplicação web |

O renderer é WebGLRenderer (r170) com WebGL2, canvas, limitação de pixel ratio, fog, câmara perspectiva e iluminação. Vite identificado por helper e nomes dos chunks. Não se identificaram referências a Rapier/Cannon/Ammo nos ficheiros; as funções de física inspecionadas são implementações próprias em JavaScript.

## Mundo configurável — confirmado
mundo contém registo explícito de duas configurações, ferreira e porto, selecionadas pela propriedade world do mapa, com Ferreira como fallback. A configuração agrega personagens, casas, economia, serviços, segurança, heliportos, idioma, parâmetros de condução e tuning, nomes, regras e interface. main carrega configuração do editor, depois mapa, depois pontos de interesse, e atualiza a configuração e texto da interface. Há exceções específicas do Porto (pontes, cais, estilos, stands), pelo que não é um motor totalmente genérico. A presença de ambas as configurações prova suporte no cliente, não demonstra uma implantação Ferreira acessível separadamente.

## Geografia
O bootstrap solicita /api/map, com fallback map.json indicado no código. A resposta no HAR tem estado 200 e tamanho registado 11021802 bytes, mas o corpo não foi guardado. /api/editor tem metadados de configuração; /api/landmarks contém 16 itens na captura. Não divulgar registos individuais.
Campos observados no consumo do mapa: world, bounds, spawn, dem, roads, buildings, landmarks, tubes, cais, decks, degraus, muros, passadeiras. Contornos de edifícios são arrays planos p de coordenadas x/z e alturas h, com campos adicionais de estrutura/elevação; vias possuem geometria e em alguns casos perfil vertical y. A cena usa consultas de suporte, altura do solo, água, pontes, túneis, superfícies e edifícios. Há modo de paginação espacial para mapas grandes em condições específicas (limiar observado 30 milhões de m², sujeito ao tipo de mundo), células 512 m nesse modo. Isto é paginação de processamento espacial do mapa já carregado, não prova streaming de dados pela rede. Origem/projeção exata, fontes DEM, dados completos e pipeline de importação não confirmados.

## Estilos e modelos
JSON de estilos usa 12 categorias: baixa, ribeira, moradia, boavista, bloco, bairro, operario, industrial, caves, campus, igreja, estrutura. 33630 registos; chave é primeiro canto do contorno, estilo codificado em base 36 e indicação de pisos usada quando OSM não os fornece. Contagens por categoria na ordem anterior: 17724, 2223, 3191, 401, 2811, 516, 4958, 359, 389, 323, 135, 600. A chave por canto é frágil a alterações geométricas; preferir identificador OSM estável no MapSlop. Modelos de edifícios/monumentos usam geometria procedural; landmark-specific dados e modelos. Worker recebe pedidos de geração de modelos e configurações do mundo, com fallback no cliente. InstancedMesh, BufferGeometry, áudio Web Audio e gestão de distância/pixel ratio presentes.

## Condução e rede
Namespace de física preserva nomes stepCar, stepPed, wheelGround, tyreFx, tyrePull, collideCars, collideCarsPred, collidePedCar, collidePeds, floatBoat, carSpeed, marcha, rotacoes. TICK_RATE=30, DT=1/30 segundos. O controlador divide um passo em subpassos conforme a velocidade/deslocamento, mínimo de três. Mede apoio individual das quatro rodas, distingue superfícies/aderência, contempla marcha/rotação, suspensão, impulso/colisão e parâmetros por tipo de veículo (dimensões, distância entre eixos, largura, centro de gravidade, massa, potência, velocidade, aderência). Colisões carro-carro usam formas circulares compostas, altura e impulsos. Modos de pessoa, carro, barco e voo são implementados no cliente. Não se validou o comportamento em execução.

Rede: WebSocket, snapshots binários, mensagens JSON para eventos, número sequencial dos inputs e tick/ack. O cliente mantém inputs pendentes, descarta os confirmados, repõe a posição fornecida pelo servidor e reaplica os inputs ainda pendentes, com suavização de erro ou correção imediata se excessivo. Outros veículos interpolados entre snapshots, extrapolação limitada se faltar amostra. Evidência de previsão/reconciliação com snapshots do servidor; implementação e autoridade das restantes regras do servidor não disponíveis. Não documentar detalhes de autenticação nem interfaces debug.

## Recomendação MapSlop
Arquitetura independente a aproveitar: separar manifesto do mundo, dados geográficos, estilo procedural, runtime de física, renderização e rede. P0: escolher um upstream MIT já testável, condução offline em terceira pessoa, importar OSM e DEM, mundo Pedome, verificações de curvas, declives, colisão e travagem. P1: editor de pontos de interesse e estilos em dados, minimizar custos de modelação manual, incorporar outros mapas sem alterar o controlador. P2: entrada/saída, tráfego, missões, economia e tuning. P3: multiplayer com servidor próprio e previsão/reconciliação. Não copiar bundles PortoSlop. Não identificámos assinatura direta de Slop New York nos bundles (ausência de termos não prova ausência de derivação). Comparação linha a linha com upstreams e execução ainda não realizadas.

## Próximo insumo
Guardar a resposta pública https://porto.tremocogames.com/api/map como JSON (não é necessário entrar no jogo). Permitirá verificar schema completo, projeção, contagens, camadas e resolução do relevo. O HAR já permitiu analisar o cliente; não pedir novamente. O conteúdo de servidor permanece fora do alcance da engenharia inversa cliente.
