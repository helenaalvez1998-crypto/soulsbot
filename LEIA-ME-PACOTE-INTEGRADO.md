# SoulsBot — pacote integrado das etapas 1 a 6

Este pacote reúne a base completa do SoulsBot usada na etapa 6, com as alterações acumuladas das etapas 2 a 6 e os documentos de auditoria/entrega das etapas 1 a 6.

## Conteúdo
- Etapa 1: auditoria da experiência dos painéis.
- Etapa 2: navegação e experiência da Nara.
- Etapa 3: painel administrativo.
- Etapa 4: subpainéis dos membros.
- Etapa 5: refinamento dos subpainéis administrativos.
- Etapa 6: cartas Primordiais e integração correspondente do Coliseu.

## Instalação
1. Faça backup integral do projeto atual e do banco SQLite utilizado pelo bot.
2. Extraia o conteúdo desta pasta sobre uma cópia do projeto ou em uma pasta nova.
3. Preserve seu arquivo `.env` e as credenciais já configuradas; este pacote não inclui `.env`.
4. Preserve o banco de produção. O arquivo local `data/jogos.db` foi deliberadamente excluído para evitar substituir dados reais. Se o projeto precisar dele para inicialização limpa, deixe o próprio bot recriá-lo conforme sua configuração ou restaure uma cópia apropriada.
5. Confira as variáveis de ambiente e permissões do Discord, especialmente as configurações do canal privado do Ateliê/Coliseu, antes de iniciar.
6. Instale/atualize as dependências conforme `requirements.txt` e execute o bot.

## Validação
A suíte de testes de UX e Primordiais disponível nesta base foi executada: **41 testes passaram**.
Isso não equivale a um teste de integração no Discord ou no FadeHost. Faça a validação em ambiente de homologação antes de substituir a versão em produção.

## Observação sobre etapas
Os arquivos de código foram consolidados na versão mais recente da base da etapa 6. Portanto, arquivos que aparecem em etapas anteriores podem ter evoluído nas etapas posteriores; não se deve substituir a base integrada aplicando os ZIPs antigos por cima.
