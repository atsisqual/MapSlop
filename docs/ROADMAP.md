# Roadmap MapSlop (P0–P3)

Critérios propostos, não resultados de testes. Cada entrega deve ter PR, comandos reproduzíveis, relatórios persistentes e [STATUS](STATUS.md) atualizado. Ver [decisões](decisions/README.md).

## P0 — condução e base reproduzível (em curso)

Já demonstrado em Chromium: piloto com 179 vias, 527 edifícios, 67/67 testes, deslocação >2 m, HUD e multitoque emulado. [Evidência](research/evidence-20261127.md). Ainda plano; sem teste em telefone físico.

Critérios para fechar P0:
- Build piloto com OSM versionado e commits fixados; contagens idênticas, zero falhas upstream.
- Browser desktop/móvel: arranque, deslocação >2 m, direção, travão/reset, dois toques simultâneos e libertação; sem erros JS, shader ou recursos essenciais.
- Circulação pela direita: validar dois cruzamentos e uma via de sentido único com casos documentados.
- Pelo menos um Android físico: acelerar, virar, travar, ampliar mapa e reposicionar, 5 min sem bloqueio; registar modelo, browser e FPS.
- Build reproduzível, Pages acessível e créditos visíveis.

## P1 — reconstrução geográfica (por implementar)

- MDT 0,5 m: CRS e cobertura sem nodata já verificados no run 46053111254; comparar 100 pontos e corredores rodoviários. TIN <150k vértices e máximos ≤0,5 m; caso não cumpra, fallback 2 m (≤1 m nos 100 pontos). LOD distante avaliado por RMSE. Condução ≥100 m com declive/curva e contacto ≤0,5 m; ver [ADR 0010](decisions/0010-grelha-mdt.md).
- MDS−MDT por footprint: guardar método/amostras/altura/qualidade/fallback; inspecionar pelo menos 20 edifícios. Roofer LoD2 com LAZ/footprints; guardar sucessos e falhas por edifício.
- Ortofoto 25 cm: recorte georreferenciado, alinhamento com estradas/edifícios, tiles LOD, atribuição. Separar histórico do cenário atual.
- Vegetação LAZ classes 3–5 e COS2025: altura, cobertura, excluir corredores de circulação; rever amostra visual.
- Expandir para bbox de 8,4 km² após testes piloto, sectores e LOD. Meta proposta para telefone de referência: mediana ≥30 FPS num percurso de 5 min; declarar dispositivo, resolução, percentil baixo e memória.
- Não distribuir dados sem licenças e autorização aplicáveis.

## P2 — mundo jogável (por implementar)

- Trânsito/peões e prioridade: 20 agentes durante 5 min sem atravessar edifícios nem bloqueios permanentes; medir FPS.
- Três missões completas (entrega/táxi, por exemplo), com início, objetivo, falha, recompensa e persistência local testáveis.
- Exploração a pé, veículos e colisão consistente; testes de transição e reset. Aprovação visual/física P1 como pré-requisito. Sem copiar PortoSlop.

## P3 — experiência online (por implementar)

- ADR de arquitetura servidor, autoridade e segurança; Pages não hospeda servidor multiplayer.
- Dois clientes com sincronização de posição/estado, reconnect e testes de latência; medir divergência.
- Testar carga/custos, moderação/privacidade e compatibilidade móvel antes da publicação; orçamento a acordar, nenhum servidor contratado.

## Fora de âmbito imediato

LiDAR nacional completo, reprodução proprietária PortoSlop, publicação de releases rascunho sem autorização e migração subtree antes de ADR aceite. Prioridade: geografia e browser.
