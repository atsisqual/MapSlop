# 0002 — Dados brutos em Releases, não no Git

- Data: 2026-11-27 · Estado: aceite (rever visibilidade)

## Decisão
Originais geográficos (PBF, GeoTIFF, LAZ, ortofotos) ficam em GitHub Releases com `SHA256SUMS` e manifesto. No Git só ficam extratos pequenos e documentação de proveniência.

## Consequências
- Releases em rascunho não são visíveis a agentes sem acesso de escrita. Um agente novo sem token não consegue obter os dados → ou publicar os releases quando as licenças estiverem reconciliadas, ou documentar em `AGENTS.md` como pedir acesso.
- Os scripts de jogo devem conseguir reconstruir produtos derivados a partir destes originais sem novo download.
