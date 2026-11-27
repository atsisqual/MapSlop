# 0007 — GitHub Pages e condução tátil

- Data: 2026-11-27 · Estado: aceite

## Contexto
Utilizador quer testar no telemóvel e não executar serviços locais. Versão inicial exigia teclado; não havia referência visual clara.

## Alternativas
- Servidor dedicado desde P0.
- Site estático Pages, interação no browser.
- Controlos apenas teclado/comando (insuficientes).

## Decisão
Publicar site estático após validação Chromium, com dependências Three.js fixadas/localizadas, HUD tátil, minimapa, reposição, entrada mobile e módulos JS com versão de build. Não distribuir dados brutos no site.

## Consequências
Testes automatizados de condução e multitoque emulado passaram; não equivalem a teste em hardware móvel. Multiplayer exige arquitetura posterior. [Evidência](../research/evidence-20261127.md).
