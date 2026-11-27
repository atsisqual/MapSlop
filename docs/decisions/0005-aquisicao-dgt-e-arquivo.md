# 0005 — Aquisição DGT por STAC e arquivo de originais

- Data: 2026-11-27 · Estado: aceite

## Contexto
Os índices enviados continham GeoPackages, não rasters. Os pedidos GET por bbox e downloads não autenticados não foram suficientes; o portal redireciona os ficheiros.

## Alternativas
- Descarregar manualmente e transferir ZIPs.
- Usar autenticação normal e STAC POST, com arquivo cloud.
- Publicar diretamente os originais (rejeitado enquanto direitos/consentimento pendentes).

## Decisão
Usar sessão autorizada com Actions secrets, POST /search por coleção e BBOX, allowlist explícita para hosts oficiais e armazenamento observado, verificação de assinatura de ficheiro/tamanho/SHA-256. Preservar originais em Releases em rascunho de acordo com [ADR 0002](0002-dados-brutos-em-releases.md).

## Consequências
Nunca guardar credenciais, cookies ou URLs assinados. Arquivo confirmado de 15 MDT 0,5 m, 15 MDS 0,5 m, 30 rasters 2 m, 15 LAZ e 18 ortofotos (2 atuais + 16 históricas). Não publicar releases sem autorização expressa. Licenças STAC e política institucional divergem; esclarecer por coleção. [Hashes](../research/release-assets-20261127.json).
