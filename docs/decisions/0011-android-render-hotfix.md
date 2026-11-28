# 0011 — Hotfix gráfico Android sem republicar o terreno
- Data: 2026-11-28 · Estado: proposta

## Contexto
Build pública 255673d8bc58 apresenta ruído em taludes e zebra no chão num Android real, não nas capturas SwiftShader. Three.js fixado já define generateMipmaps=true, minFilter=LinearMipmapLinearFilter, magFilter=LinearFilter; o caminho comum Textures chama backend.generateMipmaps quando generateMipmaps e mipmapsAutoUpdate estão ativos, e WebGPUTextureUtils aloca níveis e copia HTMLImageElement (WebP descodificada pelo browser). Isto não comprova conteúdo correto dos níveis num driver Android.

## Alternativas
Recriar e republicar o runtime completo (risco de misturar correções não aprovadas); mudar de versão do motor ou forçar backend global (causa não comprovada); overlay isolado e A/B no dispositivo.

## Decisão
Overlay explícito no runtime verificado de Pages, preservar geometria e dados. Filtros explícitos, validar POT por manifesto e por textura carregada; reduzir anisotropia apenas Android a 1 (override para A/B); observar chamadas reais ao backend e níveis alocados WebGPU. TIN de colisão intacto, deslocação da malha visual orto -0,02 m: estrada já tem +0,03 m, caminhos +0,05 m; limitar far a 2500 m (fog a 1100). Não há shadowMap ativa na versão de origem; toggle diagnóstico sem misturar #45. Conservar seleção automática de backend e forçar WebGL2 opcionalmente. Branch não publica; gate de parâmetros e screenshots; teste Android físico obrigatório.

## Consequências
Anisotropia conservadora pode reduzir detalhe a ângulos rasantes. Offset visual introduz diferença de 2 cm para a colisão; sem mudança do TIN. Far limita vistas muito distantes, já cobertas por fog. SwiftShader e contagem de geração não demonstram pixels corretos em hardware. Sem aprovação do dono, não fazer merge. Se persistir, comparar orto off, pavimento off e backend; investigar mipmaps pré-computados/driver e shader de pavimento conforme evidência.
