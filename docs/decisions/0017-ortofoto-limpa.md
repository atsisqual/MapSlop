# ADR 0017 — Limpeza da ortofoto com máscara métrica

Estado: implementação privada, validação pendente.

A fotografia DGT contém objetos também representados em 3D. Não alterar o TIN, árvores ou edifícios aprovados; conservar os tiles originais e cores de telhado já amostradas. Gerar máscara LiDAR classes 3–6 e footprints do runtime em grelha 0,5 m com margem de 0,5 m. Proteger corredores rodoviários; apenas candidatos compactos elevados de classe 1 em vias/estacionamento podem ser removidos como possíveis veículos. A classe não prova o objeto: reportar contagens e dimensões, comparar visualmente, sem inventar deteção total.

Reconstruir por vizinho não mascarado da mesma categoria pavimentado/outro, suavizar dentro da máscara. Isto sintetiza chão invisível, não recupera uma fotografia real. Em mata densa os doadores podem estar distantes; reportar distâncias, revisar visualmente. Trabalhar mosaico completo antes dos tiles para evitar cortes na fronteira, manter 25 cm/1 m/2 m e gutter; tiles sem máscara são copiados byte a byte. Verificar diferença fora da máscara após WebP e manter limites de transferência. Não usar fontes Google nem imagens externas. DGT CC BY 4.0, transformação documentada.

Alternativas rejeitadas: pintar todo o mapa de verde/cinzento, usar classe 1 como classificação certa de veículos, limpar cada tile isolado, alterar geometria para esconder artefactos ou publicar sem comparação. Evidência privada em draft, máscaras e mosaicos, seis capturas de jogo e seis de chão isolado nos mesmos pontos, replay 104 m. PR específico para publicação após validação e revisão, só substituir tiles do runtime aprovado.

## Revisão V2 — 2026-11-28

O dono rejeitou visualmente a V1 (run 46136414988) apesar dos gates técnicos. Substituir método de vizinho mais próximo por OpenCV Telea em componentes limitadas de objetos; não remover copas/edifícios. Detetor de objetos brancos por brilho/contraste/forma na zona da igreja é proxy, precisa de confirmação visual. Máscaras protegidas e pixels não mascarados preservados exatamente após descodificação WebP lossless. Medir variância local 9x9 fora da máscara dilatada, sem permitir regressão. Mantém física e câmaras fixas. Limite 1 MiB/tile e 32 MB totais para aceitar lossless (proposta, não medida). Nenhum merge sem aprovação visual.
