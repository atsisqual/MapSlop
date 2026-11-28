# ADR 0019 — Laboratório local GLB e 3D Tiles

Estado: protótipo implementado, execução pendente.

O dono aceita maior peso para realismo. A investigação de earth-3d inspirou streaming hierárquico, mas o acesso a dados proprietários não é demonstrado nem autorizado pelos seus fornecedores. O PR #41 contém a investigação e regras locais; este ensaio usa exclusivamente DGT/OSM já inventariados. Não copiar dados Google/Apple nem usar capturas externas.

Escolher igreja OSM 149406360, gerar envelope de telhado a partir de retornos reais classe 6, grelha 0,5 m e textura RGB 25 cm da ortofoto aprovada. Paredes são estimadas até ao TIN; sem inferir janelas, campanário detalhado ou materiais reais. Não confundir envelope 2,5D com fotogrametria completa. Gate de cobertura, distância, RMSE de holdout e continuidade; conservar fonte original. Testar o mesmo GLB em GLTFLoader e 3DTilesRendererJS (Apache-2.0) com Three.js pinado. O tileset é um único bloco Z-up, GLB Y-up e transformação de grupo inversa; verificar bounds 5 cm. Isto prova ingestão, não streaming em cidade grande. Manter a física, colisões e versão Pages intocadas; eventual integração é PR próprio depois da validação A/B e da igreja. O perfil local poderá dispensar orçamento de armazenamento público, mas medir memória GPU, CPU e fps real. Fixture de CI sintética, real manual e drafts só com derivados DGT autorizados.

## Ver localmente

Após obter candidato aprovado de draft privado (ou gerar fixture), criar diretório em outputs/, nunca em site Pages. Copiar church.glb, church-report.json, tileset.json e verificar SHA256SUMS antes de usar.

```sh
bash tools/stage-local-3d.sh outputs/local-church
python -m http.server 8080 --bind 127.0.0.1 --directory outputs/local-church
```

Abrir http://127.0.0.1:8080/?mode=glb e http://127.0.0.1:8080/?mode=tiles. Ferramentas descarregadas são software; viewer não consulta serviços de mapas. O ambiente de validação bloqueará pedidos externos, com capturas e report. O lock gerado permite repetir a versão efetivamente resolvida; ainda não foi fixado no Git.

## Revisão V2

Dono aprovou V1 real (run 46138928840, RMSE 0,43179 m), mas pediu planos, detalhes e integração. Implementação: roof_plane_fit.py (eixos footprint, detetar torre por aglomerado de retornos altos; modelos de águas contínuas, interseção de planos exata), facade_details.py (config YAML com defaults, não medições), install-local-church.py (troca visual única num runtime verificado). Geometria de colisão original preservada por design, mesmo que cobertura física para helicóptero não coincida com topo visual. Evidência do jogo antes/depois e 104 m de condução, amostras de colisores junto ao edifício, GLB e TilesRendererJS; guardar patch privado após gates. V2 ainda não validada em dados reais. Não confundir com pipeline fotogramétrica completa.
