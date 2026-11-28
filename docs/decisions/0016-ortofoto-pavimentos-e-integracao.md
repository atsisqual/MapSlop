# ADR 0016 — Ortofoto como solo de referência e integração de derivados

Estado: implementado no PR #36, validação conjunta pendente.

## Contexto
Run 46096919931 validou textura e TIN, mas o dono identificou a oclusão por passeios de 4,2 m em ambos os lados, independentes de OSM. Não é um problema de resolução ou UV.

## Decisão
- Manter o TIN aprovado (run 46085062868, SHA-256 36019dfc…) e a geometria de asfalto. A ortofoto é a base visual, sem pintura genérica de zonas urbanas.
- Gerar passeios com lado OSM explícito (origem e direção preservadas nos segmentos), largura mapeada dentro de 0,6–6 m ou 1,5 m de fallback. Não criar passeios em vias sem atributo, com sidewalk=no ou separate. Em vias divididas colapsadas, não inventar offsets de lado ambíguos. Caminhos pedonais explícitos: respeitar superfície e largura; não criar cinzento para terra/relva/gravilha. Áreas explícitas pedonais/pavimentadas trianguladas com restrições; overlay a nível do chão parcialmente transparente para manter o detalhe da imagem. Polígonos de edifícios não são praças.
- Amostrar RGB dos tiles near (25 cm) no interior do footprint, sem anel de borda, rejeitando verde dominante e sombra escura; classificar terracota e cinza com paleta discreta para limitar materiais/draw calls. Não é identificação física do material. Sem amostras suficientes, fallback neutro declarado. Roofs Roofer validados conservam os materiais existentes.
- Comparar duas builds idênticas exceto estas regras; mesma câmara, imagens before/after e percurso 104 m. Exigir proveniência OSM dos polígonos emitidos, redução da área de passeios, asfalto invariável, fundações e aceitação de roofs, árvores 5702, textura near ligada, colisão e contacto válidos. Timings de software comparados com tolerância para variabilidade do runner, não um certificado de desempenho físico.
- Reutilizar os derivados privados já revistos, verificar checksums e relatórios, não repetir os downloads dos rasters originais. O runtime candidato fica em draft único para preflight de Pages posterior; nenhum original ou relatório privado vai para o site.
- Não alterar o TIN para encaixar um telhado. A exceção de fallback de 223354671 continua específica, não se aceitam novas rejeições silenciosas.

## Alternativas rejeitadas
Ocultar apenas os passeios mantendo a colisão invisível; pintar todos os telhados da mesma cor; publicar o run ortofoto isolado; reutilizar o TIN anterior ao carve; gerar o mapa de 25 km² antes de validar o piloto integrado.
