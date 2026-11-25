# Narabot V20 — Arsenal de Relíquias

## Incluído
- Painel Arsenal dentro da área Deck e Coleção.
- Seletor das seis Relíquias disponíveis na V19.
- Prévia com nome, raridade, categoria e descrição.
- Persistência da pré-seleção via localStorage no navegador.
- Estado explícito de Relíquia preparada ou sem Relíquia.

## Limite desta entrega
A V20 implementa a interface e a pré-seleção local. A escolha ainda não é sincronizada entre dispositivos/contas e não é enviada automaticamente ao estado de uma partida. O motor V19 continua responsável por validar e consumir uma Relíquia quando a carta é jogada. A integração de loadout por conta e partida fica como próxima etapa técnica.

## Verificações
- `node --check site/app.js`: aprovado.
- Compilação sintática de todos os arquivos Python: aprovada.
