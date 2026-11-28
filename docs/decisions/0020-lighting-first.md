# ADR 0020 — Iluminação com mapa de sombras limitado

Estado: proposta para revisão visual. Após auditoria 28/11/2026, privilegiar alterações visíveis. Primeiro usar iluminação nativa do Three.js no motor existente, evitar dependência CSM/AO até verificar compatibilidade e orçamento. Sombras estáticas de edifícios com região centrada na câmara, quality=off/low/high, sem mudar terrenos, colisores ou texturas. Custo medido em software apenas proxy; teste em telemóvel necessário. A aprovação do CI não equivale a aprovação visual. Não publicar automaticamente.
