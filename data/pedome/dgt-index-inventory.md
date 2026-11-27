# DGT — inventário dos índices fornecidos (2026-11-27)

Os dez arquivos enviados contêm índices vetoriais GeoPackage, não pixels, altitudes ou nuvens de pontos. Inspecionados com Fiona e interseção geométrica em EPSG:3763; RAR extraído via libarchive.

Área piloto WGS84 S,W,N,E: 41.4105,-8.395,41.4195,-8.383. Área alargada: 41.405,-8.405,41.435,-8.375. Envelope piloto PT-TM06: -21897.040,193497.415,-20890.823,194499.938.

## Ortofotos
Todos os índices de 1995, 2004–2006 (duas versões), 2007, 2010, 2012, 2015, 2018, 2021 e 2025 intersectam a folha 084-4 no piloto; 084-2 adicional na área alargada. 2025: nome interno do raster `ortos2025_cog_25cm_rgbi_jpg_084-4_v01.tif` (e `084-2_v01.tif` com mesmo prefixo para a área alargada), apesar do nome do GeoPackage indicar 50cm. 2018: `ortos2018_cog_25cm_rgbi_jpg_084-4.tif`. 2021: `ortos2021_cog_25cm_rgbi_jpg_084-4.tif`. Preferir 2025, resolução de 25 cm confirmada na ficha oficial: https://snig.dgterritorio.gov.pt/rndg/srv/api/records/96d83932-f957-40d6-a2ea-3a25751c4b2d. Não presumir que o caminho interno Z: é URL de descarga.

## LiDAR
`LiDAR2024_2025_Secciona.gpkg`, camada tiles, 91 196 polígonos múltiplos, NAME/LOTE/DISPONIVEL. Quatro quadrículas piloto: 178494, 178495, 179494, 179495. Área alargada: 177493–177497, 178493–178497, 179493–179497 (15 quadrículas). Todas lote 1, DISPONIVEL='nao' no índice entregue. O estado pode estar desatualizado; não prova indisponibilidade atual do portal. Para margem adicional de terreno, obter área alargada se possível.

Prioridade: MDT 0,5 m ou 2 m GeoTIFF; MDS correspondente para estimar alturas por diferença; ortofoto 2025 para texturas. Portal https://cdd.dgterritorio.gov.pt/dgt-fe/catalogos/colecoes . DGT indica também plugin QGIS DGT CDD Downloader: https://github.com/qgispt/dgtcd_downer . Alternativa MDT nacional 10 m derivado dos dados DGT: https://www.fc.up.pt/pessoas/jagoncal/dtm-lidar-dgt/ (3,9 GB; não descarregado). Não foi obtido raster nem verificada licença de redistribuição de cada ficheiro. Índices originais continuam nos uploads; este inventário não é cópia dos binários.
