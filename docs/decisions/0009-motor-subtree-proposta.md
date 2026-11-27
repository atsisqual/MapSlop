# 0009 — Motor local por git subtree

- Data: 2026-11-27 · Estado: proposta

## Contexto

O motor atual é [Slop Nairobi](https://github.com/briankariuki/slop-nairobi) (MIT), commit `64b8599ae7dd7ba56ffbe68f19cc1423a9e7f903`, obtido em build e adaptado por [prepare-pedome.py](../../tools/prepare-pedome.py). A dependência de Three.js e os commits fixados continuam a fazer parte do ambiente reproduzível. As substituições textuais funcionam no commit de origem, mas tornam frágeis futuras alterações do motor e dificultam rever o código efetivamente executado.

## Alternativas

1. Manter o modelo atual (download de commit fixo + patch textual): menor dimensão do Git e nenhuma importação upstream; manutenção frágil e dependência da disponibilidade da origem.
2. Git submodule: separação explícita e revisão upstream simples; checkout e CI exigem gerir outro repositório e os patches locais precisam de uma origem própria.
3. Git subtree: código selecionado no Git de MapSlop, mudanças locais revistas normalmente e origem rastreável por commit; aumenta dimensão/histórico e exige gestão disciplinada de merges e de licenças.

## Decisão proposta

Adotar a opção 3 apenas após aprovação explícita do mantenedor e uma auditoria prévia dos ficheiros upstream. Este ADR não autoriza a execução da migração. A estrutura proposta é `engine/` para o código do motor, com configuração e pipeline de dados próprios fora desse diretório; outputs gerados continuam ignorados. A origem é Nairobi, não PortoSlop.

Exemplo de comando futuro, **não executado** e válido apenas se toda a árvore do commit puder ser importada sem violar as regras do projeto:

```sh
git subtree add --prefix engine https://github.com/briankariuki/slop-nairobi 64b8599ae7dd7ba56ffbe68f19cc1423a9e7f903 --squash
```

Antes de executar, inventariar toda a árvore upstream (código, dependências, assets, dados, tamanhos, direitos de redistribuição e atribuições). Preservar a licença MIT e avisos upstream. Não importar dados brutos, ficheiros >50 MB, assets sem direitos comprovados, segredos, código/dados PortoSlop ou toolchain GPL/AGPL para o runtime. Remover um ficheiro num commit posterior não o retira do histórico. Se a árvore completa não cumprir [AGENTS.md](../../AGENTS.md), não fazer o subtree direto: avaliar uma árvore upstream filtrada e auditada, com commit e manifesto reproduzível que documentem a origem, transformações e exclusões; submeter essa opção a aprovação antes de qualquer importação.

## Plano de migração futuro (por aprovar)

- Guardar a baseline do build atual, relatório de rede/edifícios, testes unitários e browser.
- Separar a origem, limites, referencial, circulação, alturas rurais, spawn e configuração da cidade dos patches textuais atuais. Rever adaptações de controladores, seleção de estrada de superfície, sentido/offset, teleporte, modelos vazios, landmarks, entrada Pedome, HUD e importmap Three.js.
- Manter conversão geográfica e recursos gerados fora do motor. Aplicar as adaptações como commits pequenos e revistos; preservar fixtures e os commits exatos do motor e Three.js.
- Atualizar Makefile, documentação, CI e Pages apenas num PR de migração posterior. Não mudar simultaneamente o conteúdo geográfico do piloto.
- Atualizações upstream futuras por commits fixados e PR com diff, inventário de licenças, resolução de conflitos e testes; sem atualização automática para HEAD.

## Consequências e critérios de aceitação

- Benefício esperado: motor inspecionável e alterações locais rastreáveis, menos patches por substituição textual. Custo: Git maior e manutenção da divergência upstream.
- Antes de integrar: verificar licenças, tamanhos e proveniência da árvore; confirmar outputs e atribuições, build fixture e mapa real, 67 testes do motor, paridade do piloto plano (179 vias, 527 edifícios, 113 nós, 134 ligações), condução desktop, dois dedos simultâneos e libertação dos comandos no Chromium, sem dependências runtime externas inesperadas.
- Comparar visualmente e por métricas os resultados antes/depois; guardar evidência durável. Não confundir teste de browser com desempenho de dispositivo móvel físico. Usar o CI existente e [baseline](../research/ci-evidence-20261127.md).
- Se a migração falhar, manter o build atual ou reverter o PR sem eliminar a proveniência.

**Estado presente:** nenhuma importação, comando subtree, alteração ao motor ou migração de workflow nesta tarefa. O build continua a usar o upstream fixado e os patches atuais. A proposta permanece pendente de decisão do mantenedor.
