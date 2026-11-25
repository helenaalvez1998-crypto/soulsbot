# Instalação — revisão de efeitos por raridade

1. Faça backup da pasta `data/`, do banco de dados usado na sua instalação e do arquivo `.env`.
2. Desligue o bot.
3. Extraia este ZIP sobre a pasta atual do projeto, substituindo os arquivos.
4. Preserve o `.env` e o banco de dados da instalação atual; este pacote não exige apagar nem recriar dados.
5. Inicie o bot normalmente.

## O que mudou

- A raridade agora aumenta a potência dos efeitos numéricos, com orçamento limitado por ativação.
- Efeitos especiais de clima, compra, invocação, escudo, movimento, recuperação e estados negativos também recebem melhorias específicas por raridade.
- Os limites de alvo exibidos pela interface acompanham os limites validados pelo motor.
- Poder-base e custo não são alterados por esta regra; as faixas de poder por raridade continuam independentes.

## Validação

Testes automatizados do motor: 21 aprovados.
