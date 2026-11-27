# 0008 — PortoSlop como referência, não dependência

- Data: 2026-11-27 · Estado: aceite

## Contexto
O objetivo é recriar mecânicas e reconhecimento geográfico em Pedome. HAR e resposta /api/map permitiram analisar o cliente público, sem licença de redistribuição identificada.

## Alternativas
- Copiar bundles, mapas ou modelos de terceiros (rejeitado).
- Implementação independente por motor open source e dados licenciados.

## Decisão
Registar apenas observações funcionais, estruturas em termos gerais e métricas; manter PortoSlop fora do runtime e do arquivo de dados. Reutilizar Slop Nairobi/London/Taipei conforme licenças e inventário.

## Consequências
Não versionar HAR, URLs de sessão, código proprietário ou mapa original. [Auditoria](../research/portoslop-client-audit.md) e [formato](../research/portoslop-map-format.md).
