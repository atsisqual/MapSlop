# Referências visuais de Pedome

Preencher buildings.yaml por osm_id (way OSM). A igreja e vinte candidatos foram selecionados por tamanho e proximidade dos pontos de captura, não por visibilidade confirmada. Campos null são desconhecidos; não inventar. Acrescentar notas_dono com observações; estas prevalecem sobre defaults procedurais e discrepâncias devem ser registadas. Medidas LiDAR não são substituídas silenciosamente.

Fotos próprias: photos/<osm_id>-<vista>-<data>.jpg (ex.: 149406360-sul-20261128.jpg). Só adicionar ficheiros autorizados para este repositório público; retirar EXIF sensível e anonimizar rostos/matrículas quando necessário. Guardar autor, data, licença ou autorização e referência em LICENSES.md. Não adicionar fotos de origem desconhecida.

Fontes externas permitidas: Mapillary, KartaView, Mapilio (confirmar CC BY-SA 4.0 de cada fonte/imagem), Wikimedia Commons (licença individual, verificar compatibilidade). Registar URL canónico, autor, licença, data de captura/acesso, alterações e ficheiros derivados. Texturas derivadas CC BY-SA 4.0 vão exclusivamente em textures-cc-by-sa/, sob a mesma licença e com créditos no ecrã do jogo. Não misturar com materiais MIT. Não descarregar, guardar ou processar imagens de Google Street View, Earth ou Maps.

## Mapillary
Criar conta, registar aplicação em https://www.mapillary.com/dashboard/developers e copiar Client Token. Em Settings > Secrets and variables > Actions > New repository secret criar MAPILLARY_TOKEN. Nunca colocar token no YAML, chat, Git, parâmetros visíveis ou logs. Após merge: `gh workflow run mapillary-coverage.yml --repo atsisqual/MapSlop --ref main`. Consulta apenas metadados e cobertura na bbox -8.395,41.4105,-8.383,41.4195; sem download de imagens. Se a API falhar, reportar desconhecido, não zero. A consulta não autoriza uso automático das imagens.
