# 0011 — Alturas MDS−MDT e ensaio Roofer

- Data: 2026-11-27 · Estado: proposta experimental (issue #7)

## Decisão

Medir percentis da diferença MDS−MDT nos footprints OSM, com máscara interior, indicadores de cobertura e heterogeneidade, e conservar fallback existente quando não houver suporte. Preservar alturas OSM explícitas. Alternativas: níveis estimados, máximo raster (sensível a árvores), classe 6 isolada ou reconstrução integral imediata. O percentil 90 é um candidato de altura total, não uma medida certificada de fachada. Ver [critérios e workflow](../buildings-dgt.md).

Reutilizar Roofer 1.0.0 como ferramenta offline separada para vinte footprints e quatro LAZ verificados. CityJSONSeq é o produto experimental; não incluir código copyleft no runtime. Comparar qualidade e resultados antes de converter telhados em meshes e colisões do jogo. CI sintético e execução real pendentes; nenhum dado publicado.

## Run real 46066175261 — correções

Job 140731913913: medições concluídas (527 footprints, 371 candidatos, 156 fallback; alturas min/Q1/mediana/Q3/max 1,61/4,195/5,46/7,355/14,1 m). Preview falhou na asserção inline antes do diagnóstico; causa concreta de identidade/altura ainda não provada. Normalização estrita int, string decimal ou way/ID, rejeição de duplicados, relatório e log de contagens/IDs em falta/diferenças antes de manter gate 527 e erro ≤0,011 m. Roofer falhou PermissionError em bin/roofer; restaurar bits de execução após extração, bibliotecas locais legíveis/executáveis e LD_LIBRARY_PATH dos diretórios arquivados, confirmar --version e registar no log antes de chamar. Testes de regressão preparados; novo run real e CI pendentes. PR #25 integrado pelo utilizador (75a0b2b034ed822aa680bb73745554196f67602f), deploy verificado segundo utilizador. Não publicar edifícios. Comando: gh workflow run pedome-terrain.yml --ref agent/dgt-building-heights -f mode=buildings.
- Inspeção adicional do upstream fixado confirmou q(h) = Math.round(h * 10) / 10, incompatível com o gate 0,011 m para alturas MDS em centímetros. Adaptador passa a exportar altura h a 0,01 m, mantendo a tolerância; novos logs confirmarão se havia também divergência de IDs. CI e run real ainda pendentes.
