# ADR 0014 — Circulação pela direita

Estado: proposta implementada, CI pendente. Issue #8.


## #8 — Circulação pela direita

O spawn anterior já usava sinal correto, mas o grafo ainda tinha offsets negativos (mão esquerda), faixas divididas deslocadas para o lado errado, stop bars/give-way no lado esquerdo e ACROSS='R'. Centralizar em tools/traffic-side.mjs: normal direita (-dz,dx), offsets positivos crescentes, sentido único centrado e reverse-oneway respeitado. Preservar pares de vias separados quando posição do sentido contrário não é compatível com mão direita; sem alterar níveis ou física. Linhas de paragem na metade de chegada, bordos brancos; prioridade de viragem à esquerda sobre tráfego oposto (ACROSS='L' significa a viragem que deve ceder). OSM de Pedome não contém junction=roundabout neste recorte; fixture sintético mantém sentido mapeado e prioridade do anel. Testes executam corpos reais do grafo via VM upstream, duas interseções, sentido único, reverse, rotunda, pintura/spawn; CI real e smoke pendentes. Sem ativar tráfego AI no shell P0, sem publicação. #9 investigação vegetação a seguir.
