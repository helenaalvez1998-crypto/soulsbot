# Templates padrão do SoulsBot Coliseum

Estes cinco PNGs são os templates completos padrão para cartas com arte personalizada. Cada arquivo mede 840 × 1240 px, usa RGBA, tem a janela da ilustração transparente em `(56, 256) → (784, 846)` e mantém todos os demais pixels opacos.

Os arquivos são defaults do pacote. Uploads administrativos são guardados separadamente em `DATA_DIR/cartas_templates/` e têm precedência sobre estes defaults quando passam pela validação. Um upload legado inválido é ignorado e o arquivo padrão volta a ser usado. As coordenadas dos textos são fixas no guia oficial; arquivos JSON antigos de layout não são aplicados. Um upload antigo com janela desalinhada ou transparência fora do limite é rejeitado e o default incluso é usado automaticamente.
