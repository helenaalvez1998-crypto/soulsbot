# Estrutura técnica do Soulsbot

O projeto mantém os módulos de domínio no diretório raiz para preservar os imports existentes. A separação é por responsabilidade, sem mover arquivos e quebrar os imports do `bot.py`.

```text
Soulsbot/
├── bot.py                    # ponto de entrada e carregamento dos cogs
├── config.py                 # configuração, env e constantes
├── database.py               # persistência SQLite, schema e transações
├── admin_config.py           # configuração administrativa por servidor
├── cogs/                     # módulos Discord: comandos, eventos e views
│   ├── admin.py
│   ├── cargos.py
│   ├── colizeu.py
│   ├── loja.py
│   ├── nara_ia.py
│   ├── ofertas.py
│   ├── perfil.py
│   ├── platinas.py
│   ├── progressao.py
│   ├── ranking.py
│   ├── santuario.py
│   ├── soulslike.py
│   ├── trofeus.py
│   ├── youtube.py
│   └── zerados.py
├── nara_local.py              # respostas locais, roteamento econômico e bloqueio de imagens
├── ia_nucleo.py               # agente: política, validação e riscos
├── ia_ferramentas.py          # ferramentas que o agente pode invocar
├── ia_gemini.py               # adaptador do SDK Gemini para a Nara
├── gemini_resilience.py       # circuit breakers independentes dos dois projetos Gemini
├── tavily_resilience.py       # limite mensal gratuito e circuit breaker da busca web
├── ia_provedores.py            # busca Tavily Free + failover entre dois Gemini
├── ia_confirmacao.py         # views/botões de confirmação de ações
├── catalogo_ia.py             # identificação de jogos e validação de fontes
├── trofeus_service.py         # regras e consultas do Caçador de Troféus
├── conquistas.py / levels.py  # conquistas, XP e patentes
├── loja.py / utils.py / ui.py # utilitários compartilhados
├── prompts/                  # prompts editáveis da Nara
│   ├── nara.md               # personalidade/referência geral
│   └── nara_pesquisa.md      # prompt curto para pesquisa conversacional opcional (desligada por padrão)
├── tests/                    # testes unitários e de regressão
├── data/                     # banco, estado do circuit breaker e dados locais
├── env.example               # modelo seguro de variáveis de ambiente
└── requirements.txt          # dependências Python
```

## Camadas

1. **Discord (`cogs/`)**: comandos, modais, botões, permissões e respostas.
2. **Domínio (`*_service.py`, `ia_nucleo.py`)**: regras de negócio, validação, economia e progressão.
3. **Infraestrutura (`database.py`, `config.py`, `gemini_resilience.py`, `tavily_resilience.py`)**: persistência, configuração, limites e chamadas externas.
4. **IA (`nara_local.py`, `catalogo_ia.py`, `ia_gemini.py`, `ia_ferramentas.py`, `prompts/`)**: respostas locais, pesquisa baseada em fontes recuperadas e ações controladas.
5. **Qualidade (`tests/`)**: regressões, transações, concorrência, parsing e simulações de falhas externas.

## Arquivos locais que não devem ser substituídos

- `.env`: credenciais e IDs do seu servidor.
- `data/colizeu.db`: banco SQLite com membros, progresso, saldo, platinas, runs e catálogos.
- `data/gemini_circuit.json`: bloqueio temporário persistido após falha de quota/rate limit.

O ZIP de distribuição não contém esses arquivos locais. Na atualização, extraia o código por cima da instalação mantendo `.env` e `data/`.
