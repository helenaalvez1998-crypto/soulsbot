# Instalação — Narabot V75

1. Faça backup da pasta atual e do banco de dados.
2. Extraia `narabot_expansao_12_cartas_v75.zip`.
3. Substitua os arquivos do projeto pelos arquivos da pasta `narabot_v52_work` do pacote.
4. Preserve seu `.env`, credenciais, arquivos de configuração locais e banco de dados.
5. Reinicie o bot e o servidor web.
6. Atualize o site com `Ctrl + F5`.

## O que muda
- Entram 12 cartas novas no catálogo e no pool de pacotes: quatro por facção.
- As cartas ficam disponíveis por obtenção normal; não são concedidas automaticamente aos inventários existentes.
- O Ateliê passa a reconhecer 12 cenas de arte específicas para essas cartas.
- A versão de cache das artes passa para 28.

## Banco de dados
Não há migração necessária. Nenhum inventário, deck, carta já obtida ou arte aplicada é apagado.

## Observação sobre as ilustrações
As cenas e direções de arte individuais estão cadastradas para geração no Ateliê. O pacote não contém 12 imagens finais geradas; as ilustrações precisam ser geradas/aplicadas pelo fluxo de arte do Narabot ou enviadas pelo administrador.
