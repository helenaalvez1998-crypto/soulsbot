# Correção — limite de tamanho do prompt do Ateliê

## Problema

O botão **Gerar prompt de arte** colocava o prompt inteiro dentro da descrição de um embed do Discord. A API limita `embed.description` a 4.096 caracteres. Para cartas com prompts maiores, `edit_message` falhava com HTTP 400 / código 50035 e a interação não era concluída.

## Correção

- O embed agora contém apenas uma instrução curta e os dados resumidos da carta.
- O prompt integral é enviado como arquivo TXT em uma resposta privada (ephemeral).
- O nome do arquivo é sanitizado a partir do nome da carta.
- O prompt não é truncado: todas as diretrizes continuam disponíveis para o usuário.
- A view de envio da arte permanece no painel original.

## CheapShark

As linhas apresentadas de CheapShark são `INFO`, não erros. A coleta recebeu 300 registros brutos, filtrou e deduplicou para 70 ofertas válidas. O pipeline encontrou zero ofertas novas após comparar com as ofertas já registradas; portanto, publicou zero. Isso indica ausência de novidades nessa coleta, não falha da API.

## Validação

- `py_compile` de `cogs/cartas_coliseu.py`: aprovado.
- Verificação estática: a descrição do embed não recebe mais o prompt integral; o prompt é codificado em UTF-8 e enviado como `.txt`.
- Teste de interação real depende de executar o bot com `discord.py` e uma interação Discord válida.
