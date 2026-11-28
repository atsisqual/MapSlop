# ADR 0015 — Extração privada de vegetação LiDAR

Estado: proposta implementada, extração real e validação pendentes (#9).

- Usar retornos classificados DGT LAZ 3/4/5, em vez de árvores aleatórias ou identificação de espécies por COS. Verificar SHA-256 e dimensão das quatro folhas LAZ e quatro MDT de 0,5 m contra inventário; verificar também OSM e COS versionados. CRS horizontal EPSG:3763; altura relativa ao MDT local.
- Células de 1 m, cobertura de retornos de todas as classes em células de 5 m >=95%; máximo de classe 5 entre 2,5 e 45 m com >=3 retornos plausíveis na célula. Máximos locais 5x5 e supressão espacial de 3 m. Raio proxy de ocupação (0,8–5 m), não uma medição de copa ou uma árvore confirmada. COS apenas contexto territorial; rejeitar classes de estrada/água e classificação ambígua/ausente.
- Excluir interseção da copa proxy com corredores OSM (meia largura + 1,5 m) e edifícios OSM (+0,75 m). Não confundir isto com garantia visual de ausência de vegetação; validar também contra geometria final do mapa.
- Guardar candidatos e relatório com estatísticas de classes, alturas, raios, cobertura, rejeições e SHA-256 em release draft dedicada. Nunca publicar LAZ/MDT originais ou este derivado sem autorização.
- Alternativa rejeitada: instâncias procedurais baseadas apenas no uso de solo, sem retornos medidos. Próxima fase: comparar deteções com ortofoto, confirmar exclusões no mapa, definir densidade/LOD e desempenho em browser antes de qualquer integração pública. Sem identificação de espécies.
