# 0006 — Ferramentas de reconstrução separadas do runtime

- Data: 2026-11-27 · Estado: aceite

## Contexto
Reconstruir terreno e edifícios sem reinventar ferramentas geoespaciais; código de terceiros tem licenças distintas.

## Alternativas
- Implementar tudo de raiz.
- Usar ferramentas offline existentes e exportar produtos de dados.
- Incorporar código GPL/AGPL no motor MIT (não adotado).

## Decisão
Arquivar os sete projetos nos commits exatos e o Roofer v1.0.0 Linux; testar Roofer e City4CFD como primeiros candidatos. Roofer/3dfier/City3D/BlenderGIS GPL-3.0; City4CFD AGPL-3.0; OSM2World e cjio MIT conforme metadados de repo. Executar ferramentas copyleft offline como processos separados; não ligar nem copiar o código para o runtime. Revisar licenças de dependências/assets e obrigações de redistribuição antes de publicar qualquer ferramenta ou versão modificada.

## Consequências
A saída não é automaticamente sujeita à licença do programa só por ter sido produzida por ele; verificar direitos dos dados de entrada e eventual material de código/ativos incluído. Sem alegar compatibilidade universal. Apenas `roofer --help` testado; nenhum edifício reconstruído. [Versões](../../data/reconstruction-sources.json) e [evidência](../research/evidence-20261127.md).
