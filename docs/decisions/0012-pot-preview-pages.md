# 0012 — Pirâmide POT e preview Pages isolada
- Data: 2026-11-28 · Estado: proposta

## Contexto
O gate #46 rejeitou o manifesto real: 128 m de tile + 4 m de gutter produziam 66/132/528 px, NPOT. WebGL2 e WebGPU podem suportar NPOT com mipmaps, logo é uma hipótese forte a validar no dispositivo, não prova definitiva da causa do ruído.

## Alternativas
Redimensionar em JS (rejeitado: memória/CPU e perde proveniência); remover gutter (rejeitado: costuras e desalinhamento); reprojetar originais para o mesmo footprint POT. Publicar branch por cima de main (rejeitado); preview com raiz main e candidato separado no mesmo Pages.

## Decisão
Reprojetar dos dois TIFFs DGT originais verificados para near 512, gerar mid 128/far 64 offline; manter extensão 132 m, recalcular m/px e usar UV normalizada pelo footprint com gutter, manter geometria, TIN e geodata aprovados. Verificar os 192 ficheiros descodificados e SHA, arquivar derivado em release draft única por run/attempt/role. WebP base, mipmaps gerados no backend com filtros explícitos, não no browser por reamostragem do original. Gate de alinhamento, dimensões, filtros e geração. Preview manual a partir do workflow já existente: checkout de main e branch fixados por SHA, build/test em jobs separados, publicação agregada única, faixa PREVIEW e verificação HTTPS. Inicialmente allowlist #46, não suportar silenciosamente outros branches que ainda não têm contrato de overlay Pages.

## Consequências
Near passa a 0,2578125 m/px, ligeira perda de resolução face a 0,25 m; sem alteração de extensão ou UV. Descarga privada de ~1,1 GB por build POT; nunca nos artefactos Pages. Preview publicamente acessível pelo URL; apenas derivados autorizados. GitHub Pages pode exigir autorização de environment para o branch; não contornar proteção. A raiz mantém main e um deploy normal remove previews antigas. Aprovação física explícita do SHA candidato antes de merge visual. A geração real e o deploy não foram executados localmente.
