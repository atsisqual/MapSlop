# 0012 — Perfis longitudinais e TIN rodoviária

- Data: 2026-11-27 · Estado: proposta experimental, issue #27

## Contexto

O terreno natural TIN aprovado está publicado desde PR #25, mas reproduzir cada irregularidade do MDT sob o asfalto não produz condução suave. A [análise PortoSlop](../research/portoslop-map-format.md) confirma apenas o conceito de perfil e carving; não reutilizar código/dados ou assumir o seu algoritmo offline.

## Alternativas e decisão

1. Filtrar o terreno inteiro: rejeitado, perde fidelidade fora das vias.
2. Malha de asfalto independente e consultas de altura especiais: risco de superfícies físicas/visuais inconsistentes.
3. Perfil explícito + deformação local do TIN (primeira experiência): aproveitar sampler, normals, drape, mesh e colisões já existentes. Se a retriangulação Delaunay sem breaklines falhar, migrar para triangulação constrained e/ou superfície rodoviária explícita com consulta física unificada, mantendo as medições.

Recortar os ways ao envelope TIN, amostrar eixo OSM a cada ~3 m (intervalos menores em troços curtos e nós partilhados), MDT original 0,5 m verificado por hash. Usar variável única por nó OSM ao mesmo nível e resolver LP esparso SciPy/HiGHS (dependência já fixada): minimizar maior desvio, depois soma de resíduos, limitando diferença de grade normalizada a 2 pontos percentuais por 3 m (0,006667 m⁻¹). A 5,5 m/s essa curvatura ideal implicaria cerca de 0,20 m/s² de aceleração vertical geométrica a velocidade constante; não é garantia de comportamento do controlador. Medir também sondas independentes de 0,5 m entre amostras, desvio máximo ≤0,5 m; se impossível, registar falha e rever casos, não relaxar automaticamente. Pontes/túneis/aterros/cortes/layers OSM listados e excluídos; interação com vias adjacentes requer inspeção. Não certificar estruturas a partir de ausência de tags.

Secção plana, altura por projeção longitudinal, empate determinístico no eixo mais próximo; nó comum e zona de junção suavemente nivelada. Berma de 2,5 m com smoothstep até terreno natural. Inserir pontos de controlo no centro, limites de faixa e berma; ajustar alturas de vértices e retriangular com SciPy Delaunay. Usar exatamente as faces resultantes no build privado; não adicionar offset rodoviário na física separado do visual. Não se garante que Delaunay não altere faces fora do corredor, que a aproximação por segmentos produza cruzamentos perfeitos, nem que as curvas/retas passem; medir o produto descodificado. O perfil é linear por troços, com variação de grade limitada, não spline C1. Malha nova não tem identidade geométrica com terreno natural; a codificação compacta verifica apenas identidade do candidato antes/depois de codec.

## Gates experimentais

- Perfil: ≤0,5 m em nós e sondas intermédias, variação normalizada ≤2 pp/3 m, altura comum dos nós.
- Malha: ≤1° de inclinação transversal nas sondas afastadas de cruzamentos, centro vs perfil ≤0,1 m, cruzamentos vs perfil ≤0,02 m, diferença fora do corredor ≤0,1 m nas 101×101 sondas disponíveis; <150k vértices. Sondas não são garantia contínua; detalhes de limites/overlap, casos de rotunda e estruturas necessitam testes adicionais.
- Browser: percurso de referência Rua das Bouças ≥104 m, mesma rota baseline/candidato, sem colisões, contacto ≤0,5 m; aceleração vertical da superfície ≤2 m/s² pela segunda diferença numa janela total 0,2 s (reportar também pico por passo e aceleração do carro), roll de carro em retas ≤1° com ≥30 amostras. Mede aceleração cinemática, não acelerómetro físico. Não confundir pitch com roll, nem roll de suspensão em curva com inclinação de estrada.
- Testar e medir, não declarar aprovação antes de CI e execução real. Release experimental sempre em rascunho; Pages continua com o derivado #25. Publicação de candidato novo só mediante autorização.

## Execução

```sh
gh workflow run pedome-terrain.yml --ref agent/smooth-road-profiles -f mode=roads
```
