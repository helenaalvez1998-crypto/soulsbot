# Caçador de Troféus — primeira etapa

Esta versão adiciona a fundação do sistema ao Soulsbot:

- Botão **Caçador de Troféus** no painel existente do Coliseu.
- Comando `/cacador` como atalho.
- Catálogo separado do inventário cosmético da loja.
- Progresso individual por usuário.
- Navegação por jogo, categoria, itens e troféus.
- Nomes exibidos como `Nome em português (Original em inglês)`.
- Solicitação de jogos ausentes pelo próprio jogador, diretamente no Discord.\n- Fila administrativa para acompanhar solicitações.\n- Importação administrativa de catálogos JSON para revisão.
- Publicação administrativa após validação básica.

## Comandos administrativos

- `/catalogo_importar arquivo:<arquivo.json>`: importa para revisão; não publica automaticamente.
- `/catalogo_publicar slug:<slug>`: publica se houver pelo menos um item e um troféu.

## Formato de importação

Veja `catalogo_exemplo.json`. O arquivo é apenas um exemplo de estrutura: seus dados são fictícios e marcados como não verificados. Não publique esse exemplo como catálogo real.

## Limites desta etapa

Esta entrega registra solicitações de jogos ausentes, mas **não** implementa ainda a pesquisa autônoma na web nem conectores de fontes externas. A camada de importação e o modelo de dados estão preparados para receber os conectores autorizados na próxima etapa. Também não inclui um catálogo real completo de Dark Souls III.

## Atualização

Faça backup do SQLite antes de atualizar. As novas tabelas são criadas automaticamente na inicialização e não alteram as tabelas antigas.


## Identificação e pesquisa automática de jogos

O fluxo usa a chave `GEMINI_API_KEY` já usada pela Nara e o Google Search grounding do Gemini.
Configure também `GEMINI_MODEL` com um modelo Gemini que suporte Google Search grounding.

### Fluxo do membro
1. Execute `/jogo_buscar nome:<texto>`. Pode informar abreviações, título traduzido ou nome com erro.
2. O agente pesquisa correspondências e retorna títulos oficiais candidatos, ano, estúdio, escopo e confiança estimada.
3. Se houver mais de um candidato, selecione o jogo correto. A entrada original nunca é gravada como título canônico.
4. Confirme. A IA pesquisa fontes e tenta montar itens, troféus e relações.
5. O catálogo entra em `review`; não aparece no painel dos jogadores até revisão e publicação administrativa.

### Fluxo administrativo
1. `/catalogo_fila` consulta solicitações recebidas pelo botão do Caçador.
2. `/catalogo_auditar slug:<slug>` mostra cobertura, fontes, domínios e validação.
3. Abra as fontes e revise nomes, localizações, requisitos, DLC, NG+ e cobertura.
4. `/catalogo_validar slug:<slug>` é uma declaração explícita de que um administrador revisou manualmente todos os registros.
5. `/catalogo_auditar` novamente; a publicação exige itens e troféus, fontes em todos os registros, pelo menos dois domínios e validação manual.
6. `/catalogo_publicar slug:<slug>` publica o catálogo.

### Garantias e limites
- A IA identifica candidatos; não assume que o texto digitado é o nome oficial.
- Títulos canônicos e aliases ficam separados e persistidos.
- A pesquisa usa Google Search grounding. O sistema aceita como fontes somente URLs que o Gemini devolveu nos dados de grounding; fontes citadas em texto pelo modelo, mas não retornadas no grounding, não são aceitas.
- Dados gerados começam com `verified=0`. Nenhum catálogo é publicado automaticamente.
- A validação administrativa é uma declaração humana, não uma auditoria automática infalível.
- Não existe API universal que forneça todos os troféus, armas, magias e localizações de todos os jogos. A cobertura depende das fontes disponíveis. `coverage_notes` registra lacunas declaradas pelo pesquisador.
- Não há garantia de completude nem de precisão perfeita. Revise os dados antes de marcar como verificados.
- A geração de catálogos pode consumir chamadas Gemini e pesquisas Google; verifique preços/limites da sua conta.
