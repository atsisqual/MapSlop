# Evidência — ambiente P0, 2026-11-27

Executado no PR #12, run 46044314224, job 140659613926, commit `d990fa790616c9b073f14085dea2fead79ced2e9`. Resultado do job: success. O workflow executou `make setup` (npm ci com lockfile), `.venv/bin/python -m pip check`, `make build`, `make test`, `make serve PORT=8080` e pedidos HTTP, `docker build` e `docker run` com verificação das versões. Excerto de resultados lidos do log:

```text
git version 2.56.1
Python 3.12.10
v22.16.0
10.9.2
Pinned upstreams ready
No broken requirements found.
# pass 67
# fail 0
# pass 67
# fail 0
BUILD_REPORT {"fixture": false, "flat": true, "bbox": [41.4105, -8.395, 41.4195, -8.383], "roads": 179, "buildings": 527, "nodes": 113, "links": 134, "estimatedBuildings": 511}
MAKE_SERVE_OK
Python 3.12.10
v22.16.0
10.9.2
git version 2.39.5
GNU Make 4.3
git version 2.56.1
```

Limites: imagem base fixada por tags de versão, não digest; pacotes do sistema seguem o repositório Debian da imagem. GDAL/PDAL não instalados porque o pipeline P1 ainda não existe. Não constitui teste físico em telemóvel nem validação da reconstrução.
