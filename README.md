# MapSlop

Simulador 3D de localidades reais. Primeiro mapa: Pedome, Vila Nova de Famalicão, Portugal. A base prevista é [Slop New York](https://github.com/mrdoob/slop-newyork), código MIT, com uma camada geográfica independente da grelha de Manhattan.

## Fase 0 — importação geográfica

Requer Node.js 18 ou superior:

```sh
node tools/import-osm.mjs
```

O importador consulta Overpass/OpenStreetMap. O mapa piloto é um retângulo de aproximadamente 1 km por 1 km centrado em Pedome (41.4155, -8.3869), não os limites administrativos completos. Para outras zonas: `--bbox sul,oeste,norte,este --name nome-do-mapa`.

Saídas em data/pedome:
- osm.json: dados originais com geometria e atributos.
- roads.json: eixos das vias em metros e IDs dos nós; ainda não é uma rede navegável.
- summary.json: contagens e metadados.

Use `--input caminho/osm.json` para reprocessar sem rede, com a mesma caixa geográfica, e `--out pasta` para escolher outro destino.

## Próximas etapas

1. Validar a importação com dados reais.
2. Integrar o upstream MIT, preservando a licença original.
3. Substituir a grelha de Manhattan por estradas de geometria arbitrária, cruzamentos e passeios, incluindo sentidos únicos e níveis de pontes.
4. Reutilizar os geradores de edifícios e árvores, com a mesma origem e orientação.
5. Integrar relevo (o primeiro mapa será plano), colisões, condução e exploração a pé.
6. Acrescentar referências locais e missões.

O jogo ainda não é executável. O código upstream ainda não foi incorporado e o importador ainda não foi validado com dados reais.

## Créditos

[Guia técnico de adaptação do upstream](https://github.com/mrdoob/slop-newyork/blob/main/PORTING.md).
Dados: © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), ODbL 1.0. Manter a atribuição na interface e nas distribuições e cumprir as condições ODbL para bases derivadas. Código e recursos de terceiros mantêm as suas licenças.
