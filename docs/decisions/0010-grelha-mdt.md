# 0010 — Grelha MDT no referencial do motor

- Data: 2026-11-27 · Estado: aceite para implementação experimental

## Contexto
O MDT DGT já está arquivado, mas o motor Nairobi tem um filtro DSM e grelha fixa de 25 m. Aplicá-lo ao MDT perde detalhe e pode alterar terreno já classificado como solo.

## Alternativas
- Reusar o filtro GLO-30 no MDT.
- Converter diretamente o MDT para a grelha do motor.
- Migrar para terrain streaming/3D Tiles ou subtree desde já.

## Decisão
Conversão offline com rasterio, amostragem bilinear no CRS de origem e grelhas estáticas 2/5/10 m (1 m opcional). Preservar eixo/origem do motor, base na igreja, interpolação triangular. Carregar JSON no adaptador sem filtro DSM. Comparar 100 pontos interiores com fonte, tolerância de 1 m no produto primário. Manter fallback anterior. Não executar subtree nem streaming nesta tarefa.

## Consequências
LOD estático não é seleção dinâmica; malha fina aumenta vértices, memória e custo de render. Verificar limites em dispositivo real. Produtos DGT só em rascunho enquanto licenças e autorização estiverem pendentes. Testes de raster sintético são apenas testes do código; dados reais carecem de workflow manual e evidências. Ver [pipeline](../terrain-dgt.md).
