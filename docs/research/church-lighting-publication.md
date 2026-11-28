# Publicação da igreja + iluminação corrigidas

Preparação separada dos branches #42/#45 para evitar sobrepor trabalho concorrente. NÃO existe lock aprovado nem alteração a Pages neste branch. Não publicar até ao resultado real conjunto e revisão das capturas. A autorização do dono (28/11) abrange a geometria e aberturas V3; correções de fachada/cobertura/sombras devem ser validadas.

## Resultados verificados

- 46156457337: geometria V1 selecionada, RMSE 0.4317902658049367m, topo 20.881288115940958m, 14 gates in-game PASS, zero colisões. Draft geodata-dgt-local-church-46156457337-1. GLB após otimização: adc7fe62ac33ec4dd0021c5cc1e85666d81b6432c9c8b2e9c2b0cc2f2f1209b1. Não é o V4 corrigido.
- 46156459734: 12 gates PASS, 104.145m, zero colisões, mediana 871.1→937.8ms. Draft geodata-pedome-lighting-46156459734-1. Não usa igreja V4 nem sombras de copas.

## Sequência

1. Correr #42 corrigido, confirmar V1/aberturas, material/UV/sRGB e capturas.
2. Correr #45 sobre o patch exato da igreja corrigida (baseline e candidate com igreja idêntica). Confirmar SHA do GLB e do shell da igreja antes da instalação. Medir sombras de copas reais, capturas zoom acne, mata e igreja; não aprovar visualmente por flags. Guardar hashes de ambos inputs no recibo da execução.
3. Fixar os hashes dos relatórios, archives e quatro ficheiros finais num lock revisto pelo dono. Usar script verify-church-lighting-release.py em cópia do runtime aprovado #36. Não executar scripts a partir de tar não verificado. Todos os ficheiros finais têm allowlist.
4. Integrar #42 e #45 com resolução de conflitos nos launchers/STATUS; não publicar ainda. Só depois, PR de publicação com lock real e alteração a pages.yml que descarrega drafts exatos via --repo, verifica manifest, chama verifier, inclui models/church.glb explicitamente no site, créditos CC0 e DGT, smoke com igreja + iluminação e verifica hash público do GLB. Nenhum raw LiDAR/ortofoto original, relatório privado ou arquivo integral público. Preflight no PR, merge autorizado quando gates reais passarem.

## Lock (schema 1; não gerar com valores fictícios)

owner_reviewed: true só quando revisão das capturas e autorização correspondem aos bytes selecionados. church: tag, assets (SHA256 de church-report.json, church-in-game-report.json, viewer-report.json, church-runtime-patch.tar.gz). lighting: tag, assets (SHA256 de lighting-report.json, lighting-visual-diagnostics.json, lighting-runtime-patch.tar.gz), input_church_model_sha256 e input_church_shell_sha256 do recibo real. runtime_sha256: mapa dos 4 caminhos e hashes finais. Verificador recusa relatório de iluminação sem igreja idêntica à candidata aprovada. Não assume que um PASS de dois testes separados seja PASS conjunto.
