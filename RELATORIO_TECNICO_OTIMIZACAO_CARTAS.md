# Relatório técnico — carregamento e cache das cartas

**Projeto analisado:** NARABOT / Gwent do Coliseu  
**Base de análise:** código recebido no arquivo ZIP e log operacional fornecido.  
**Resultado:** correções implementadas no projeto e testes locais executados; causa de reinicialização global não comprovada pelos logs.

## 1. Arquitetura encontrada

As cartas-base não são baixadas de URLs externas. `sistemas/arte_cartas.py` gera as imagens localmente com Pillow. A arte comunitária aprovada é um BLOB na tabela `cartas_atelie_submissoes`; os templates enviados pelo Ateliê ficam em `DATA_DIR/cartas_templates`. Os PNGs renderizados são persistidos em `DATA_DIR/cartas_cache`.

O cache de disco era content-addressed: SHA-256 de `VERSAO_ARTES` + JSON da carta + dimensão. Não havia TTL. Essa estratégia é adequada para imagens determinísticas, mas a versão manual era a única forma de invalidar o código visual. `render_carta` reutilizava qualquer arquivo existente sem verificar se era um PNG legível. O arquivo era escrito atomicamente, porém não havia lock no próprio módulo para coordenar threads concorrentes. A rota HTTP tinha um lock para o caminho da arte-base, mas o render da arte oficial não seguia a mesma política.

Além do disco, `bot.py` mantinha caches em memória separados: a arte-base tinha limite de 64 itens; a arte oficial, 300 itens. O limite era por quantidade, não pelo peso real em bytes.

## 2. Causas encontradas

### Imagens antigas

1. A rota da arte-base enviava `Cache-Control: private, max-age=1800, stale-while-revalidate=86400`. Portanto, o navegador podia manter a imagem por 30 minutos e ainda servir uma cópia stale por até 24 horas.
2. A chave do cache persistente dependia de `VERSAO_ARTES=18` e dos dados da carta. Mudanças nos módulos visuais, fontes ou templates dinâmicos do Ateliê não alteravam a chave automaticamente.
3. O ETag da arte-base não incluía a versão do renderizador nem a versão do template. Mesmo com revalidação HTTP, o servidor poderia confirmar com `304 Not Modified` uma imagem cujo visual já tinha mudado.
4. As URLs da coleção e do deck identificavam apenas o modelo da carta. Quando o usuário tinha vários exemplares com raridade/poder diferentes, o servidor selecionava o melhor exemplar da coleção, não o exemplar exato apresentado na interface.

### Imagens que falham ou demoram

1. O cache de disco confiava somente na existência do arquivo. PNG truncado ou inválido podia ser devolvido como se estivesse correto.
2. A camada de renderização não possuía single-flight/lock por arquivo. O caminho da arte-base tinha uma proteção na rota HTTP, mas o render da arte oficial não tinha o mesmo controle; chamadas concorrentes a outros pontos também podiam duplicar o trabalho.
3. A cache em memória não possuía limite de bytes e era separada entre imagens oficiais e básicas.
4. A rota de arte oficial servia o BLOB usando o MIME salvo no banco, sem validar o formato real dos bytes.
5. Não foi encontrado downloader de imagens externas no fluxo das cartas. Logo, URLs remotas inválidas ou indisponibilidade de API externa não são a explicação do carregamento de cartas-base.

## 3. Mudanças implementadas

### `sistemas/arte_cartas.py`

- Introduz `VERSAO_RENDERIZADOR`, fingerprint automático do código que desenha a carta, catálogo, molduras, efeitos, módulo de templates, fontes disponíveis e versão do Pillow.
- Inclui o fingerprint dinâmico dos arquivos/metadados do template do Ateliê na chave do cache. Substituição, cadastro ou remoção de template gera outra chave.
- Adiciona lock por caminho para sincronizar threads e evitar renderizações duplicadas.
- Verifica PNG persistido com Pillow (`format`, dimensões e `Image.verify()`). Arquivos corrompidos são removidos e regenerados.
- Centraliza a gravação temporária + `replace()` atômico; `render_pacote` também passa a publicar o PNG atomicamente.
- Adiciona `detectar_mime_imagem` e limites para bytes/dimensões/pixels de artes oficiais.
- `render_carta_bytes` rejeita conteúdo inválido em vez de tentar compor uma imagem corrompida.

### `sistemas/cartas.py`

- Incrementa `VERSAO_ARTES` de 18 para 19.

### `bot.py`

- URLs da coleção e do deck passam a carregar `exemplar_id` e a versão visual. A rota confirma que o exemplar pertence ao usuário e aplica a raridade/poder corretos.
- Substitui os caches separados por um LRU compartilhado, limitado a 96 imagens e 32 MiB.
- Limita a três renderizações Pillow simultâneas.
- Adiciona single-flight por chave, timeout de espera de 20 s pelo lock, 12 s pelo semáforo e deadline de 30 s para a renderização. Sob saturação, responde `503` com `Retry-After: 5`.
- Ao cancelar uma requisição HTTP, mantém a vaga do semáforo ocupada até a thread do Pillow terminar; um resultado PNG válido ainda pode ser colocado no cache.
- ETags agora incluem versão/fingerprint do renderizador, dados da carta e fingerprint do template dinâmico.
- Respostas de imagem passam a `Cache-Control: private, no-cache, must-revalidate`, retirando o período de stale de 24 horas.
- Arte oficial passa por validação dos bytes e usa o MIME detectado, não o campo MIME informado no banco.

### `site/app.js` e `site/index.html`

- URLs fallback recebem a versão da arte e identificam corretamente o ID do modelo quando o ID de interface contém `card_id::exemplar_id`.
- O HTML referencia `/app.js?v=19`, evitando que um bundle antigo do navegador mantenha a lógica anterior após a atualização.
- Imagens de carta com falhas transitórias tentam novamente após 700 ms e 1.600 ms; depois disso, exibem placeholder SVG local, sem quebrar o restante da tela.

### Testes e documentação

- `tests/test_cartas_cache.py` cobre invalidação por payload/versão/template, arte oficial inválida/válida, regeneração de cache corrompido, persistência após reinício simulado e concorrência.
- `tests/__init__.py` permite descoberta com `unittest discover`.
- `CHANGELOG_OTIMIZACAO_CACHE_CARTAS.md` documenta a implementação.

## 4. Cache: antes e depois

| Camada | Antes | Depois |
|---|---|---|
| Disco | `DATA_DIR/cartas_cache`, chave com versão manual + payload; retornava arquivo existente sem validar | Persistente; fingerprint de código/fontes/templates + payload/dimensão; valida PNG e regenera arquivo inválido |
| Templates do Ateliê | Arquivos dinâmicos não participavam da chave de imagem | Metadados e stat do template participam da chave e do ETag |
| Memória | Cache-base de 64 itens e cache oficial separado de 300 itens; sem limite global por bytes | Um LRU de até 96 itens e 32 MiB |
| Concorrência | Lock na rota de arte-base; arte oficial sem single-flight equivalente; renderer sem lock próprio | Lock por renderização, fila limitada e no máximo 3 renderizações simultâneas |
| Navegador | `max-age=1800` + `stale-while-revalidate=86400` | ETag + revalidação obrigatória (`no-cache, must-revalidate`) |
| Exemplar | URL identificava só o modelo; servidor usava melhor exemplar | URL informa o exemplar e o servidor valida propriedade e atributos |

Não foi adicionado TTL ao cache de disco. As imagens são determinísticas e content-addressed; TTL causaria regenerações periódicas sem melhorar a correção. Quando o conteúdo muda, o fingerprint muda. Entradas antigas com chaves antigas deixam de ser consultadas, mas não há garbage collector global de arquivos antigos nesta entrega.

## 5. Testes e medições

Executados no ambiente local do projeto:

- `python -m unittest discover -v`: **8 testes aprovados**.
- `python -m py_compile bot.py sistemas/arte_cartas.py sistemas/cartas.py sistemas/templates_cartas.py tests/test_cartas_cache.py`: aprovado.
- `python -m compileall -q .`: aprovado.
- `node --check site/app.js`: aprovado.

Teste concorrente comparando o código extraído do ZIP original e a implementação corrigida, com 8 chamadas simultâneas à mesma carta e renderer de teste com atraso de 80 ms:

- Original: **8 chamadas** a `_draw_card`.
- Corrigido: **1 chamada** a `_draw_card`.

Benchmark local com 12 cartas reais do catálogo, no código corrigido e em diretório de dados temporário:

- Cache frio: **7,25 s** no total (**604 ms/carta**).
- Cache aquecido: **aprox. 0,001 s** no total (**0,08 ms/carta**).
- Caminhos do cache frio e aquecido coincidiram.

O benchmark acima compara cache frio × aquecido da versão corrigida; não é apresentado como comparação integral de latência antiga × nova.

## 6. Reinicializações e limitações pendentes

O log fornecido contém inícios repetidos do runtime (`python bot.py`) aproximadamente às 10:10, 10:18, 10:21, 10:26, 10:28 e 10:37. Não há traceback Python, OOM, SIGKILL ou código de saída que identifique a causa. Também aparece um redeploy explicitamente solicitado pelo proprietário. Portanto, não é tecnicamente possível concluir que as cartas causaram esses reinícios.

O mesmo log registra bloqueios do event loop de até 10,4 s e atraso de 42,2 s no Gateway. Esses avisos indicam problema de responsividade e podem contribuir para perder heartbeats/acionar verificações do host, mas não identificam por si só a função causadora. Há bloqueios longos associados ao carregamento da Nara IA; a investigação de todas as rotinas síncronas do bot está fora do escopo das alterações do carregador de cartas.

A implementação reduz o risco originado pelo subsistema de imagens: erros ficam isolados à requisição, o Pillow roda fora do event loop, o uso simultâneo é limitado e as respostas excedentes recebem 503 controlado. Porém, para afirmar que os reinícios gerais foram resolvidos, ainda é necessário consultar no provedor o motivo de encerramento do processo, histórico de memória/RAM e eventos de watchdog.

Também não foi possível executar teste HTTP real do bot neste ambiente porque o interpretador local não possui `discord.py` instalado (`ModuleNotFoundError` ao importar `discord`). O log do host informa que `discord.py==2.7.1` estava instalado no runtime. A compilação sintática e os testes isolados passaram; o teste de integração final deve ser executado no ambiente do bot.
