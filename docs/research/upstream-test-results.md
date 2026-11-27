# Upstream validation — 2026-11-27

Executed locally against the three ZIP archives supplied by the project owner, unchanged, using Node.js v22.16.0. These are actual automated tests, not estimates or browser playtests.

| Archive | Passed | Failed | Total |
| --- | ---: | ---: | ---: |
| slop-nairobi-main.zip | 67 | 0 | 67 |
| slop-taipei-main.zip | 9 | 0 | 9 |
| london-loop-main.zip | 66 | 45 | 111 |
| Total | 142 | 45 | 187 |

Command: node --test tests/*.test.cjs tests/*.test.mjs (each archive separately).

## Nairobi
The suite verifies proportional steering, acceleration, braking, reverse steering, momentum on collisions, grip, bounded slip, handbrake, frame-rate consistency, slopes, gravity off ledges, and chase cameras above hills and avoiding buildings. Geographic build uses supplied OSM extracts and Copernicus elevation; separate vehicle-physics, colliders, terrain and road-network modules. This is the preferred baseline for the first driving prototype, pending integration tests and license/asset review. Note that Kenya drives on the left; adapt the lane graph, car seating/cameras, markings and roundabout circulation for Portugal. The generated frame already uses metres, x east and z south. The build currently hardcodes Nairobi origin and other city-specific values; the map adaptation must parameterize them. The README declares MIT; the supplied Nairobi ZIP has no standalone LICENSE file at its root. Confirm upstream license and preserve copyright notices before copying code.

## Taipei
All nine tests pass; primarily geographic data/configuration tests, not directly comparable with Nairobi's broader driving tests. Right-hand traffic makes it a useful reference for lane geometry and road conventions.

## London
66 pass and 45 fail. Several failures relate to obsolete NYC test assumptions, missing geo-frame import stubs, missing city-config.js, old traffic implementation assertions and Overpass test fixture setup. These are not proof that gameplay is broken; they indicate the inherited suite is not fully synchronized. London-specific tests do verify traffic stopping behind the player, shared road junctions, bus routes and roundabout circulation without overlap. Keep as a reference for future missions, transport, traffic and economy.

## Not yet validated
No interactive browser playtest, rendering FPS, Pedome map import or upstream integration performed. Nairobi and Taipei depend on external Three.js CDN modules at runtime. The three projects have differing test scope, so raw pass counts are not direct quality scores. The baseline choice is based on the user's priority of free driving and the relevance of Nairobi's tests, not the counts alone.

Next milestone: adapt geographic pipeline to actual Pedome OSM/terrain data, configure right-hand traffic, reproduce the tests and add a browser smoke test before calling MapSlop playable.
