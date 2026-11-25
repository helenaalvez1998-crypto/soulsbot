# Instalação — revisão de regras do Coliseu Elden Ring

1. Faça backup da pasta atual do bot, do banco de dados e do arquivo `.env`.
2. Desligue o bot e o servidor web.
3. Extraia o conteúdo deste pacote sobre a pasta atual do projeto `narabot-main`, substituindo os arquivos do código.
4. Não substitua seu `.env` nem seu banco de dados. Eles não fazem parte deste pacote.
5. Na raiz do projeto, execute:

   ```bash
   python -m unittest discover -s tests -v
   ```

6. Se os testes terminarem com `OK`, reinicie o bot e o servidor web.
7. Atualize o site com `Ctrl + F5` para carregar a interface revisada.

## O que muda nas partidas

- Unidades novas recebem uma fileira definida pelo papel tático da carta.
- O servidor recusa jogadas de unidades em fileiras diferentes da sua fileira indicada.
- Cartas especiais que reposicionam unidades continuam sendo exceções explícitas.
- A passiva de facção passa a conceder +1 à primeira unidade da facção jogada em cada rodada, igualmente para as três facções.
- Cartas com habilidade de identidade deixam de acumular uma habilidade genérica invisível.
- O cálculo de poder efetivo passa a considerar clima em pontuação e em verificações de alvos.
- Podridão Escarlate e Loucura têm efeitos secundários distintos na segunda marca.

## Compatibilidade

Os IDs das cartas foram preservados. O pacote não contém banco de dados, `.env` ou dados pessoais. Partidas já iniciadas mantêm o estado e as fileiras que estavam gravados no momento da criação; partidas novas usam a nova distribuição de fileiras.

## Validação executada

- 18 testes automatizados aprovados.
- `python -m py_compile bot.py sistemas/*.py` aprovado.
- `node --check site/app.js` aprovado.
