# Workflows e execução manual

## CI e publicação

Cada PR para main executa ci.yml (permissões contents: read, sem segredos DGT): setup fixado, verificações offline de links/formatos/digests/triggers, testes unitários DGT sem rede, build fixture e mapa real, npm test e browser Chromium com multitoque. Também pode ser acionado manualmente para depuração. Pages publica apenas a partir de main, depois do smoke test partilhado. Os workflows pedome-p0 e pedome-browser permanecem manuais para diagnóstico. O build de devcontainer foi testado em [evidência de ambiente](research/environment-evidence-20261127.md).

## Dados: exclusivamente workflow_dispatch

Executar na interface Actions → workflow → Run workflow → main, ou com gh autenticado e autorizado. Nenhuma recolha corre em push/PR. Não publicar releases em rascunho sem autorização. Nenhum segredo em argumentos, logs ou Git.

| Workflow | Função |
|---|---|
| dgt.yml | Único workflow DGT autenticado ou público; piloto, área alargada, LAZ, ortos históricos ou coleção individual |
| archive-portugal.yml | Verifica/arquiva snapshot PBF nacional exato |
| expanded-vectors.yml | OGC e recorte OSM alargado |
| pedome-terrain.yml | GLO-30 fallback, artefacto de teste |
| reconstruction-archive.yml | Ferramentas fixadas por commits/hashes; release rascunho |

DGT:
```sh
gh workflow run dgt.yml --ref main -f mode=pilot-authenticated
gh workflow run dgt.yml --ref main -f mode=collection -f collection=MDT-50cm -f snapshot=20261127
gh workflow run dgt.yml --ref main -f mode=laz -f snapshot=20261127
```

Modos pilot-public e pilot-authenticated só guardam manifesto de verificação; expanded, laz, historical e collection arquivam originais. snapshot YYYYMMDD seleciona o rascunho geodata-dgt-pedome-YYYYMMDD (historical: geodata-dgt-history-YYYYMMDD). Os originais existentes são comparados por tamanho e SHA-256; conflito obriga novo snapshot, não clobber. O workflow só aceita main, verifica os ficheiros e os digests após upload e marca falhas parciais como falhas. Requer os segredos de repositório DGT_USERNAME e DGT_PASSWORD para modos autenticados. Não os pedir em chat. Nenhuma transferência live foi executada para testar esta refatoração; CI usa fixtures.

Ver [catálogo](data-catalog.md), [STATUS](STATUS.md), [evidência histórica](research/evidence-20261127.md). Os nomes de workflows antigos nos registos de runs são históricos.
