# Nara — economia de quota, respostas locais e proteção de imagens

## Objetivo

O bot funciona primeiro sem serviços externos. Para tarefas que exigem IA, usa dois projetos Gemini: principal e reserva; a busca web do Caçador usa Tavily Free. A única IA externa é Gemini; a busca web usa Tavily Free.

1. **FAQ local:** respostas prontas, sem rede e sem tokens.
2. **SQLite local:** perfil, XP, saldo, platinas, zerados, runs, inventário e rankings.
3. **Caçador de Troféus:** `/jogo_buscar` procura catálogo/alias local primeiro; se não resolver, usa Gemini principal e depois o segundo projeto Gemini em caso de quota/indisponibilidade.
4. **Pesquisa conversacional desligada por padrão:** `NARA_CHAT_IA_ENABLED=false` mantém o chat sem chamadas externas.
5. **Fallback local:** pergunta desconhecida não vira chamada automática de IA.

## Respostas locais cobertas

- Cumprimentos, despedidas, agradecimentos, conversa curta, piadas e motivação.
- Identidade da Nara, capacidades, ajuda e comandos.
- Canais e forma de chamar a Nara.
- Registro de platina, jogo zerado e run; comprovantes.
- Uso do Caçador, regras, privacidade, XP, patentes, Denários, loja, Coliseu e Santuário.
- YouTube, ofertas, registros, rankings e recompensas.
- Consultas SQLite pessoais: perfil, nível, XP, saldo, platinas aprovadas, zerados, runs e inventário.
- Rankings públicos.
- Prints/imagens: a Nara explica que não os analisa.

Se uma frase não corresponder a uma resposta local conhecida, a Nara não inventa resposta nem consulta um modelo automaticamente.

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
| `Como usar o Caçador?` | Local | Explica `/jogo_buscar`, confirmação e revisão. |
| `Pesquise os troféus de God of War` | Catálogo | Encaminha para `/jogo_buscar`; primeiro usa aliases locais. |
| `Você consegue ler este print?` | Recusa local | Informa que não abre nem analisa imagens. |
| Mensagem comum entre membros | Ignorar | Não chama IA quando a Nara não foi mencionada. |

Os exemplos numéricos de perfil são consultados no banco real; nenhum valor fictício é apresentado como dado real.

## Limites e economia

- `NARA_CHAT_IA_ENABLED=false`: padrão e recomendado; chat não chama API.
- `OFFERS_SHOW_DESCRIPTION=false`: evita tradução externa de descrições.
- `/jogo_buscar`: limite persistente de três identificações por usuário a cada dez minutos.
- Se o catálogo já existe localmente, não há chamada Gemini.
- A pesquisa só começa após confirmação do jogo e sempre fica em revisão.
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
