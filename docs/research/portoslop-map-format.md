# PortoSlop — mapa geográfico: análise de formato (2026-11-27)

## Método e limites
JSON de 11 021 802 bytes enviado pelo utilizador, parseado integralmente; cruzamento com o JavaScript público capturado no HAR anterior. Análise estática, sem executar o jogo. Não incorporar o mapa, os bundles nem os recursos do PortoSlop neste repositório. Dados geográficos do original atribuem OSM/ODbL; restantes licenças e fonte do DEM não confirmadas. Gerar Pedome a partir de dados independentes e licenciados.

## Medições
- v=1; world=porto; origin latitude/longitude [41.1462,-8.6112]; bounds [minX,minZ,maxX,maxZ] = [-3312,-3239,2825,2012]; retângulo 6.137 x 5.251 km, 32.225387 km²; polígono fronteira (21 pares x,z) 27.042506515 km² por fórmula shoelace. Três zonas de detalhe, sobrepostas.
- roads: 13 119 registos; comprimento acumulado de polilinhas 846.5097 km (inclui caminhos não automóveis, não deduplicado); 12 953 têm perfil vertical, 4 988 nome, 4 410 largura de passeio, 932 st, 158 dk, 8 tb.
- buildings: 33 826 registos (33 030 com c e 796 com struct); altura h min/mediana/máx 1.51/11.7/71.54 m; 32 449 com g. Não confundir com 33 630 classificações de estilos no ficheiro separado do HAR.
- land: 5 904 polígonos (14 categorias); trees: 15 453; parking: 380; pois: 7 154; places: 130.
- decks: 561 segmentos (não 561 pontes distintas); tubes: 73 registos; passadeiras: 1 325; degraus: 2 419; muros: 2 419.
- landmarks vazio no mapa base, embora o HAR inclua uma resposta separada de landmarks; aero sem pistas, aeros vazio.
- graph.n: 28 316 pares coordenadas; graph.e: 29 972 pares de índices; graph.o: 15 172 pares; graph.l: 11 398 quádruplos (dois índices e dois códigos). Índices no intervalo válido 0..28315. Semântica exata de e/o/l e utilização servidor ainda por confirmar.

## Formato observado
Top-level: v, attribution, origin, bounds, spawn, posto, roads, buildings, land, trees, parking, pois, places, landmarks, aero, aeros, graph, dem, cais, tubes, world, decks, passadeiras, zonas, fronteira, degraus, muros.
Road: p = pares x,z em metros locais, w = largura, k = classe numérica, d = flag binária (significado exato a confirmar), n = nome opcional, sw = passeio, y = perfil de altura, st = escadas, dk/tb = referências de estruturas. Não inferir enum k ou d só pelos valores.
Building: p = polígono, h = altura, g = nível de implantação observado no tratamento de terreno, struct = ligação a estrutura, yt/yb = alturas; outros códigos por confirmar. land: k e p; POI: n,k,x,z; árvores/parking vetores compactos. Conservar IDs OSM na implementação própria (ausentes nos registos principais deste mapa).
 
## Descoberta crítica: relevo e perfis rodoviários
DEM grosseiro: origem x/z -7600/-4800, passo 50 m, 242×172 = 41 624 amostras, valores -0.5..207.9. Um patch: origem -1851/-1082, passo 25 m, 131×136 = 17 816 amostras, valores -0.5..147.9. Total 59 440 amostras; relief=1. JavaScript confirma armazenamento row-major (x+z*nx), interpolação bicúbica e mistura suave na fronteira do patch. Referência vertical = altura da amostra mais próxima da origem do mundo, escolhendo patch quando aplicável: 65 m nesta captura. O DEM bruto é convertido em alturas relativas; valores negativos de y não significam necessariamente abaixo do nível do mar. 
A geometria p e o perfil y NÃO têm relação 1:1. O runtime subdivide cada segmento em max(1,ceil(comprimento/8)) intervalos uniformes, inclui o vértice final uma única vez, e usa uma altura por amostra. Verificação independente com Python: a regra reproduz exatamente a quantidade de valores y em todos os 12 953 registos que possuem perfil. Passo máximo 8 m, não resolução efetiva do DEM. O código calcula declives usando pontos vizinhos, considera ligações nas extremidades/cruzamentos e ajusta o terreno ao traçado das ruas (road carving). O código também cria plataformas sob edifícios usando g, adapta passeios/frentes, e trata separadamente cais, pontes, túneis, muros e pilares. No modo com perfis usa groundStep=4; não confundir espaçamento de malha com resolução da fonte altimétrica. Fonte do DEM e algoritmo offline de geração/suavização dos perfis ainda desconhecidos.

## Implementação recomendada para MapSlop (independente)
1. Definir manifesto de localidade com limites, projeção métrica verificável, spawn, regras de circulação e estilos.
2. Importar OSM com IDs, geometria e atributos; obter DEM licenciado com metadados. Verificar cobertura Pedome antes de assumir área do piloto.
3. Pré-processar vias: grafos por nós OSM, respeitar níveis e sentidos, amostrar alturas com espaçamento configurável, suavizar declives e garantir continuidade entre ruas ao mesmo nível.
4. Separar malha rodoviária, terreno visual e consultas de colisão/apoio; usar a mesma altura da superfície física e visual. Tratar plataformas de edifícios, muros e vias elevadas quando necessário.
5. Adaptar o upstream MIT escolhido, não reescrever física ou renderização por defeito; condução offline antes de multiplayer. Usar o formato compacto como referência conceitual, não copiar os dados/código originais.
6. Testes: projeção e limites, topologia, alturas finitas e contínuas, perfis, travagem, curvas, declives, colisões, spawn em via e ausência de veículos a flutuar/atravessar chão; inspecionar no browser e medir FPS.
 
Estado: formato geográfico e vários algoritmos cliente confirmados por análise estática; não foi recuperado o gerador original nem o servidor, não foram executados testes dos três upstreams nesta etapa, e o mapa de Pedome ainda não foi construído.