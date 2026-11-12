# Nara — economia de quota, respostas locais e proteção de imagens

## Objetivo

O bot funciona primeiro sem serviços externos. Para tarefas que exigem IA, usa dois projetos Gemini: principal e reserva. A única IA externa é Gemini; a busca web usa Tavily Free.

1. **FAQ local:** respostas prontas, sem rede e sem tokens.
2. **SQLite local:** perfil, XP, saldo, platinas, zerados, runs, inventário e rankings.
4. **Conversa econômica (personalidade da Nara):** o que o FAQ/SQLite não resolve, quando alguém marca a Nara, vira UMA chamada curta ao Gemini: prompt pequeno (`prompts/nara_conversa.md`), sem ferramentas, sem histórico, sem imagens, resposta limitada a `NARA_CONVERSA_MAX_TOKENS`.
5. **Pesquisa com ferramentas (wiki Elden Ring):** continua desligada por padrão (`NARA_CHAT_IA_ENABLED=false`).
6. **Se a IA cair ou o limite acabar:** a Nara responde local, com personalidade, e o FAQ/SQLite seguem normais.

### Limites da conversa (protegem a franquia gratuita)

| Variável | Padrão | Efeito |
|---|---|---|
| `NARA_CONVERSA_ENABLED` | `true` | `false` volta ao modo 100% local |
| `NARA_CONVERSA_LIMITE_USUARIO` | `20` | respostas de IA por pessoa/dia |
| `NARA_CONVERSA_LIMITE_GLOBAL` | `250` | respostas de IA por dia no servidor todo |
| `NARA_CONVERSA_COOLDOWN` | `6` | segundos entre perguntas da mesma pessoa |
| `NARA_CONVERSA_MAX_TOKENS` | `320` | tamanho máximo da resposta |

Perguntas repetidas saem do cache (custo zero) e só respostas bem-sucedidas contam no limite. Ajuste os números conforme a quota real do seu projeto Gemini; `/gemini_status` mostra se algum projeto está pausado.

## Respostas locais cobertas

- Cumprimentos, despedidas, agradecimentos, conversa curta, piadas e motivação.
- Identidade da Nara, capacidades, ajuda e comandos.
- Canais e forma de chamar a Nara.
- Registro de platina, jogo zerado e run; comprovantes.
- Regras, privacidade, XP, patentes, Denários, loja, Coliseu e Santuário.
- YouTube, ofertas, registros, rankings e recompensas.
- Consultas SQLite pessoais: perfil, nível, XP, saldo, platinas aprovadas, zerados, runs e inventário.
- Rankings públicos.
- Prints/imagens: a Nara explica que não os analisa.

Se uma frase não corresponder a uma resposta local conhecida e a Nara foi marcada, ela conversa pela IA dentro dos limites acima.

## Simulações de conversa

| Mensagem | Rota | Resposta/ação simulada |
|---|---|---|
| `Oi, Nara!` | Local | Cumprimento com personalidade. |
| `Quem é você?` | Local | Apresentação da Nara. |
| `Quais comandos tem?` | Local | Mostra comandos de ajuda. |
| `Quanto eu tenho de Denários?` | SQLite | Consulta saldo privado do autor. |
| `Qual é meu nível?` | SQLite | Consulta XP e patente do autor. |
| `Quantas platinas eu tenho?` | SQLite | Consulta registros aprovados do autor. |
| `Quem tem mais XP?` | SQLite | Consulta ranking público. |
| `Como registrar uma platina?` | Local | Explica formulário e revisão humana. |
| `Você consegue ler este print?` | Recusa local | Informa que não abre nem analisa imagens. |
| Mensagem comum entre membros | Ignorar | Não chama IA quando a Nara não foi mencionada. |

Os exemplos numéricos de perfil são consultados no banco real; nenhum valor fictício é apresentado como dado real.

## Limites e economia

- `NARA_CHAT_IA_ENABLED=false`: padrão e recomendado; chat não chama API.
- `OFFERS_SHOW_DESCRIPTION=false`: evita tradução externa de descrições.
- Os dois projetos Gemini possuem circuit breakers persistentes separados.
- `/gemini_status` mostra se principal/reserva estão pausados localmente.

**Importante sobre as quotas:** limites Gemini são aplicados por projeto, não por chave. Duas chaves do mesmo projeto compartilham a quota. Configure a reserva com um projeto Google separado. Isso fornece isolamento operacional, mas não garante que o Google atribua duas franquias gratuitas nem deve ser usado para contornar limites da plataforma. Não vincule billing se não quiser pagar; ao exceder a quota gratuita, a chamada falha e o bot não tenta cobrança por conta própria.

## Bloqueio de prints, imagens e arquivos

- A conversa da Nara recebe somente texto digitado.
- O agente e `ia_gemini.py` não possuem fluxo multimodal para anexos.
- Imagens são identificadas apenas por MIME/extensão; o código não baixa bytes nem faz OCR.
- Leitura de páginas recusa imagens, PDFs, vídeos e binários.
- Comprovantes nos formulários próprios continuam disponíveis para revisão humana; não são enviados à IA.

## Testes

```bash
pytest -q
python -m unittest discover -s tests -v
```

Os testes simulam mensagens, consultas SQLite, perguntas de catálogo, quota do primeiro projeto, failover para o segundo e falha dos dois projetos.
