# Otimização do carregamento e cache de cartas

## Diagnóstico confirmado no código anterior

- O arquivo PNG persistente era reutilizado apenas por existir: não havia verificação de integridade nem coordenação de threads no módulo de renderização. O teste de regressão reproduz a condição: oito requisições simultâneas à mesma carta executavam oito renderizações.
- A chave do cache de disco dependia somente de `VERSAO_ARTES` e do payload. Alterações em módulos/fontes/templates podiam continuar usando PNG antigo quando a versão manual não era incrementada.
- Os templates do Ateliê são recursos mutáveis em `DATA_DIR/cartas_templates`; a versão anterior do cache não refletia a substituição desses arquivos.
- A rota de imagem usava `max-age=1800` e `stale-while-revalidate=86400`, permitindo ao navegador reutilizar imagem por até 30 minutos e servir a versão antiga por mais 24 horas.
- Coleção e deck publicavam a mesma URL para todos os exemplares do mesmo modelo. O servidor escolhia o melhor exemplar, o que podia exibir poder/raridade/arte incompatíveis com o exemplar que o usuário selecionou.
- A cache em memória era limitada por quantidade de itens, não por bytes; imagens oficiais tinham cache separado e não compartilhavam o mesmo limite global.

## Alterações

- `VERSAO_ARTES` passa para `19`. A chave local e os ETags usam também fingerprint do código de renderização, catálogo, molduras, efeitos, templates Python e fontes empacotadas e versão do Pillow.
- A chave inclui a versão dos templates dinâmicos do Ateliê (metadados Discord e tamanho/data de modificação do template PNG). Substituir, cadastrar ou remover um template invalida o arquivo renderizado e o ETag HTTP sem exigir download de todas as cartas.
- O cache persistente em `DATA_DIR/cartas_cache` continua baseado em conteúdo + tamanho + versão visual. Não usa TTL: as imagens base são determinísticas e não precisam ser baixadas novamente por tempo. As entradas antigas não são servidas depois da mudança de chave.
- PNG persistente é validado por tipo, dimensões e `Image.verify()`. Arquivos truncados/corrompidos são removidos e renderizados novamente.
- A gravação usa arquivo temporário e `replace()` atômico para impedir que uma requisição leia um PNG parcialmente gravado.
- Locks por chave no módulo de arte impedem renderizações duplicadas do mesmo PNG entre threads.
- Coleção e deck incluem `exemplar_id` e versão da arte na URL. A rota valida que o exemplar pertence ao usuário e aplica raridade/poder daquele exemplar.
- As rotas de imagem usam ETag e `Cache-Control: private, no-cache, must-revalidate`; removido `stale-while-revalidate` para não servir imagens antigas silenciosamente.
- Cache LRU compartilhado para imagens-base e oficiais, limitado a 96 itens e 32 MiB. Renderizações Pillow ficam limitadas a três tarefas simultâneas.
- A fila tem espera máxima por lock/semafóro e renderização com deadline de 30 segundos. Sob pressão, a API devolve `503` com `Retry-After`, em vez de acumular trabalho sem limite.
- O cancelamento de uma requisição não libera a vaga do semáforo enquanto a thread do Pillow ainda está ativa; quando termina, o PNG válido ainda pode aquecer o cache.
- Arte oficial é validada pelo formato real, tamanho e dimensões; não se confia no MIME informado no banco/upload. Arte inválida retorna erro de validação ou usa a arte-base quando a composição falha.
- A interface repete duas vezes falhas transitórias com espera crescente e exibe um placeholder local se a imagem continuar indisponível.
- `site/index.html` versiona a referência do JavaScript (`/app.js?v=19`) para evitar que o navegador continue usando a lógica antiga.

## Validação executada

- `python -m unittest discover -v`: 8 testes aprovados, incluindo 8 cartas diferentes em paralelo.
- `python -m py_compile ...` e `python -m compileall -q .`: aprovados.
- `node --check site/app.js`: aprovado.
- Regressão concorrente: no código anterior, 8 requisições simultâneas à mesma carta executavam 8 renderizações; no código corrigido, as mesmas 8 chamadas executam 1 renderização e compartilham o PNG.
- Benchmark local com 12 cartas: renderização fria 7,25 s (604 ms/carta); cache aquecido 0,001 s no total (0,08 ms/carta). É comparação frio × aquecido do código corrigido, não um benchmark de latência antiga × nova.

## Observação operacional

Não há downloader de imagens externas no caminho das cartas-base: elas são desenhadas localmente com Pillow; artes comunitárias vêm de BLOB no SQLite. Portanto, falhas de URL/API de imagem externa não explicam o problema observado. A rede de fallback consiste em novas tentativas do navegador para erros HTTP transitórios.

Os logs recebidos mostram reinicializações do runtime e bloqueios do event loop, mas não incluem traceback de carta, OOM, SIGKILL ou motivo de saída do supervisor. Há avisos de event loop bloqueado de até 10,4 s e atraso de 42,2 s no Gateway; também existe um redeploy explícito pelo proprietário. Não é possível atribuir a causa dos reinícios ao carregador de cartas com essas evidências. A nova implementação isola falhas por requisição e limita recursos do subsistema de imagens, mas a causa de reinício do processo inteiro precisa do motivo de saída/memória do provedor para ser confirmada.

`VERSAO_ARTES` e `CARD_IMAGE_VERSION` em `site/app.js` devem continuar sincronizados para versionar as URLs. A fingerprint automática dos módulos e templates também invalida o conteúdo e ETags quando os recursos visuais mudam.
