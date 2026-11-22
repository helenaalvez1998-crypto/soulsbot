# Plano de reformulação integral do SoulsBot

## Compromisso de escopo

A reformulação preserva as funções existentes, os dois comandos principais da Nara e os sistemas que já foram implementados. O objetivo é melhorar a experiência e a organização, não reconstruir o bot nem remover recursos para simplificar menus.

## Etapa 1 — Auditoria

Concluída: inventário dos painéis, ações, comandos, rotas duplicadas, pontos sem retorno e separação de permissões. A auditoria de referência foi feita sobre a versão completa enviada anteriormente; cada patch continua precisando ser comparado à versão que estiver em produção no FadeHost.

## Etapa 2 — Central /nara

Em implementação nesta entrega:
- mostrar a jornada pessoal e o deck atual logo na entrada;
- mostrar quantidade de cartas, custo e poder-base do deck;
- manter acesso direto a Meu deck, Perfil e Santuário;
- adicionar Fechar painel nas telas principais e nos subpainéis controlados pelo roteador da Nara;
- preservar a mensagem quando a sessão expirar, desativando os botões e explicando como reabrir `/nara`;
- garantir o retorno da tela de guia e de categorias à tela anterior;
- manter as ações de negócio nos módulos originais.

Próximo refinamento: percorrer os painéis delegados (Nara IA, Santuário, Catálogo e Comunidade) e padronizar os retornos dentro de cada módulo, sem alterar seus comandos ou regras internas.

## Etapa 3 — Painel /adm

- reorganizar categorias sem retirar nenhuma ação;
- agrupar diagnóstico, auditoria e estado operacional;
- distinguir ações de moderador e administrador;
- reduzir caminhos duplicados mantendo atalhos úteis;
- padronizar confirmação de ações destrutivas e financeiras;
- indicar estado e próximo passo de configurações.

## Etapa 4 — Subpainéis dos membros

- Platinas, Zerados, Runs, Meus Registros e avaliações;
- Coliseu, deck, coleção, pacotes, forja, desafios, rivalidades e missões;
- Ateliê de cartas, geração de prompt, upload, aprovação e visualização;
- Comunidade, contribuições, Arquivo de Mundos, catálogo Ports & Mods;
- Santuário, Loja, Perfil, progressão, rankings, notificações e ajuda.

Padrão comum: voltar, fechar/cancelar, paginação clara, confirmação antes de gastos, erros acionáveis, preservação de estado e proteção de interações por usuário.

## Etapa 5 — Subpainéis administrativos

- moderação e central de aprovações;
- membros, cargos e XP;
- jogos, catálogos e publicações;
- economia, loja e Coliseu;
- Ateliê e biblioteca de artes;
- canais, permissões, configurações, auditoria e diagnóstico.

Todas as ações atuais devem permanecer disponíveis e protegidas pelas mesmas permissões ou por regras mais restritivas.

## Etapa 6 — Completar a experiência de cartas e Coliseu

### Já implementado nos patches anteriores
- quatro raridades básicas, tipos e habilidades;
- cartas por conquistas de zerado e platina;
- decks, pacotes, Almas, forja, duelos, apostas, revanche e histórico;
- seleção de adversários online;
- missões semanais e progressão leve;
- artes próprias geradas com composição padronizada;
- Ateliê com prompt, submissão e aprovação via biblioteca Discord.

### Ainda planejado, não considerar instalado até receber um patch próprio
- raridade Primordial, limitada a cinco cartas únicas no servidor, com emissão transacional e proteção contra duplicação, forja, consumo e aposta;
- pacotes temáticos por jogo, respeitando as cartas exclusivas de zerado/platina;
- exibição da arte personalizada nos embeds e imagens públicas dos duelos;
- melhorias finais de navegação entre detalhe da carta, coleção, deck, Ateliê e Nara;
- definir regra de posse/visualização da arte personalizada quando uma carta muda de proprietário (se transferência de cartas for aprovada futuramente).

A raridade Primordial deve ser balanceada por identidade, história e exclusividade, não por poder bruto que garanta vitória. A chance proposta de 0,1% só pode ser ativada enquanto houver exemplares disponíveis, com bloqueio atômico no banco para impedir que duas pessoas recebam a mesma carta.

## Etapa 7 — Regressão e entrega

- mapa de função existente → novo caminho de acesso;
- testes dos dois comandos principais e de cada categoria;
- testes das permissões e isolamento dos painéis privados;
- testes de retorno, fechar, timeout e recuperação de estado;
- migração de banco em cópia de teste;
- compilação e testes automatizados;
- entrega incremental com arquivos alterados, resumo e instruções de instalação.

## Regras permanentes

1. Nenhuma função importante será removida.
2. Não substituir o banco de produção por banco de teste.
3. Nenhuma credencial ou `.env` real será incluído nos ZIPs.
4. Nenhum patch será declarado testado no Discord/FadeHost sem teste real nesse ambiente.
5. Recursos futuros serão identificados como planejados, e não apresentados como implementados.
