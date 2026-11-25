# Instalação — Laboratório de Transmutação V35

1. Faça backup do banco SQLite e da versão atualmente instalada.
2. Extraia o pacote mantendo a estrutura de pastas.
3. Atualize `site_hub.py` e a pasta `site/` junto com o restante do projeto.
4. Confirme que os módulos V28–V34 e as tabelas/migrações correspondentes estão presentes.
5. Reinicie o serviço do bot/site.
6. Acesse `/transmutacao` com uma sessão autenticada.
7. Verifique `GET /api/gwent/transmutacao`, a prévia e o fluxo de confirmação em ambiente de homologação antes de produção.

A V35 não contém migração nova de banco. Não execute testes de sacrifício em produção: falhas legítimas consomem os recursos comprometidos.
