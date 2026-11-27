# Pedome P0 — first real data build (2026-11-27)

The user supplied an OSM XML export with bounds S/W/N/E 41.405/-8.405/41.435/-8.375, 27,838 nodes, 3,694 ways and 126 relations. The converter tools/osm-xml-to-json.py reconstructs geometry using node IDs, strips edit-user metadata and selects elements overlapping the pilot bounds (bounding boxes, not exact clipping). 1,208 elements selected: 200 highway ways and 527 building ways; no missing way nodes or skipped incomplete relevant relations reported.

Offline build commands:
```sh
python tools/osm-xml-to-json.py "map.osm (1).xml" pedome-osm.json
python tools/prepare-pedome.py /path/to/slop-nairobi-main ./pedome --osm-json pedome-osm.json --flat
python -m http.server 8080 --directory ./pedome
```

Confirmed report: real data, flat terrain, pilot bounds 41.4105,-8.395,41.4195,-8.383; 179 rendered road records, 527 building records (511 estimated heights), 113 road graph nodes, 134 links. 67/67 automated tests passed; street geometry 789 directed edges and 12,171 asphalt triangles. Some roads extend beyond the rectangular selection because full geometries are retained.

A private experimental ZIP was generated and delivered in chat, with a Python localhost launcher and local Three.js vendor from the user-supplied London Loop archive (187dev; exact compatibility with Nairobi's pinned CDN version not established). Browser test attempted, blocked by local Chromium administrative policy. No interactive driving, visual fidelity, real elevations or performance confirmed. This commit documents results and does not publish the ZIP, source XML, or the generated map. OSM data ODbL 1.0. Further work: browser startup validation, right-hand traffic and signage, terrain DEM and expanded geographic bounds.
