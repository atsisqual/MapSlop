# Extended mechanics research — 2026-11-27

This supplements reuse-audit.md. The baseline decision is not final. Compare Nairobi, Taipei/Wuhan and London Loop before selecting an upstream.

## London Loop — priority candidate
https://github.com/nelsonchris1/london-loop (MIT; https://nelsonchris1.github.io/london-loop/).
Based on Slop New York, but includes arbitrary road layouts and roundabouts, pedestrians, road traffic, signals, GPS routing, taxi jobs with passenger pickup/dropoff and fares, bus driver jobs on 16 routes, bicycle, helicopter and a boat, profiles and persistence, offline fallback, WebGL2 fallback. UK traffic is left-handed; Pedome needs right-handed lanes and markings. Backend Supabase credentials/data must not be reused; isolate backend or configure a new one. Do not mistake its online persistence for live multiplayer.
Relevant file paths identified from README: js/london-world.js (terrain/bridge/water queries), js/london-vehicles.js, js/controllers.js, js/road-network.js, js/traffic-sim.js, js/traffic.js, js/road-paint.js, js/pedestrians.js, js/rideldn.js, js/backend.js. See SPEC.md and INTEGRATION.md for module contracts. Data build uses tools/osm-pbf-extract.mjs and tools/build-london-geodata.mjs. Compare complexity of replacing London-specific assets against Nairobi's Overpass-based pipeline.

## Taipei
https://github.com/shwang1979/slop-taipei (MIT).
Approximately 27k OSM road segments, 45k building footprints, lane counts, elevated roads and ramps, regional terrain, lane markings, pedestrian signals, real storefront names, traffic, pedestrian navigation, scooter and helicopter. Tools fetch-osm.sh and npm run build (clipper-lib polygon operations). Right-hand traffic makes it an especially relevant comparator; Wuhan explicitly credits Taipei's runtime and adds ride-hailing.
 
## Boats and aircraft
- https://github.com/markldn/sail-simulator (MIT): Three.js + Rapier buoyancy, wave interaction and sail dynamics. Potential reference for watercraft if London Loop's simpler boat is insufficient. Not a drop-in dependency.
- https://github.com/webgl-games/flight-sim (MIT declared): browser aircraft, takeoff/landing challenges, Three.js, Web Audio. Evaluate assets and actual flight controller before reuse.
- https://github.com/wreed4/ai-flight-simulator (MIT declared): secondary aircraft candidate.
- https://github.com/TheAlexPG/storm-fishers: license changed; current code must not be treated as MIT. Exclude unless an exact earlier MIT snapshot and all asset permissions are verified.

## Recommended sequence
Run clean upstream builds with no edits; compare controls, data regeneration for same Pedome bbox, road side, collision behavior, frame performance and amount of London/Taipei-specific code. Select a single baseline before importing multiple engines. London Loop is the broadest functional match found in this pass; Nairobi is likely the smaller geographic adaptation, while Taipei/Wuhan is a right-hand traffic candidate. None has been executed in this audit.

The original PortoSlop has not been reverse engineered; its public repository and license remain unconfirmed. Do not copy proprietary client bundles or backend credentials.
