# Nara — economia de quota, respostas locais e proteção de imagens

## Objetivo

A Nara deve continuar útil mesmo quando um dos provedores estiver sem quota; DeepSeek é principal e Gemini reserva. A regra de roteamento é:

1. **FAQ local:** respostas prontas, sem rede, sem modelo e sem custo de tokens.
2. **SQLite local:** perfil, XP, saldo, platinas, zerados, runs, inventário e rankings consultados diretamente no banco.
3. **Caçador de Troféus:** `/jogo_buscar` é o caminho para identificar jogos e pesquisar troféus, platinas, DLCs e colecionáveis de qualquer título. O comando procura aliases/catálogos locais primeiro; usa DeepSeek Search + Flash; se DeepSeek falhar por quota/saldo/limite/indisponibilidade, alterna para Gemini + Google Search grounding.
4. **Pesquisa conversacional desligada por padrão:** `NARA_CHAT_IA_ENABLED=false` impede que mensagens do chat acionem provedores de IA, inclusive perguntas de guia sobre Elden Ring. Isso é intencional para máxima economia.
5. **Fallback local:** pergunta desconhecida não vira chamada automática a nenhum provedor. A Nara explica o que consegue resolver e aponta o caminho correto.

## Respostas locais cobertas

A lista de intenções locais inclui:

- Cumprimentos, despedidas, agradecimentos, conversa curta, piadas e motivação.
- Identidade da Nara, capacidades, ajuda e comandos.
- Como chamar/marcar a Nara e em quais canais ela responde.
- Como registrar platina, jogo zerado e run; como enviar comprovantes.
- Como abrir o Caçador e pesquisar um catálogo.
- Regras, privacidade, patentes, XP, recompensas, Denários e loja.
- Coliseu, Santuário, rankings, avisos do YouTube e ofertas.
- Consultas pessoais no SQLite: perfil, nível, XP, saldo, platinas aprovadas, zerados, runs e inventário.
- Rankings públicos de XP, platinas e jogos zerados.
- Perguntas sobre prints/imagens: a Nara explica que não os analisa.
- Perguntas sobre remoção de zerados, aprovação de platinas/runs, momento de recompensa e consulta de perfil de outros membros.

Se uma frase não corresponder a uma resposta local conhecida, a Nara não inventa uma resposta e não consulta automaticamente um modelo.

## Simulações de conversa

As respostas abaixo são exemplos de roteamento e texto esperado. Valores de perfil/saldo são obtidos do banco real no servidor; os dados numéricos dos exemplos são fictícios.

| Mensagem do membro | Rota | Resposta/simulação |
|---|---|---|
| `Oi, Nara!` | Local | “Oi, [membro]. Meus circuitos estão em ordem. E os seus?” |
| `Bom dia` | Local | Cumprimento contextual pelo horário de Brasília, sem IA. |
| `Quem é você?` | Local | “Sou a Nara, assistente do Soulsbot...” |
| `Quais comandos tem?` | Local | Mostra `/coliseu`, `/nivel`, `/ranking-xp`, `/cacador`, `/jogo_buscar` e `/loja`. |
| `Quanto eu tenho de Denários?` | SQLite | Consulta somente o saldo do autor; ex.: “Seu saldo é 135 Denários.” |
| `Qual é meu nível?` | SQLite | Consulta XP, nível, patente, progresso e totais do próprio membro. |
| `Quantas platinas eu tenho?` | SQLite | Lista contagem e até 10 platinas aprovadas do autor. |
| `Quais jogos eu zerei?` | SQLite | Lista registros de zerados do autor. |
| `Quantas runs aprovadas tenho?` | SQLite | Conta runs aprovadas do autor. |
| `O que tenho no inventário?` | SQLite | Lista cosméticos próprios e informa se estão equipados ou guardados. |
| `Quem tem mais XP?` | SQLite | Consulta ranking público, sem consultar saldos privados. |
| `Como ganhar XP?` | Local/config | Lê os parâmetros de XP configurados no código, sem chamar Gemini. |
| `Como consigo Denários?` | Local/config | Informa recompensas configuradas para platinas/zerados e aponta `/loja`. |
| `Como registrar uma platina?` | Local | Explica o caminho `/coliseu` → Platinas → formulário → revisão. |
| `Como mando o comprovante da run?` | Local | Explica o formulário de Runs; a Nara não avalia a imagem. |
| `Como usar o Caçador?` | Local | Explica `/jogo_buscar`, confirmação de título e revisão do catálogo. |
| `Como registrar um jogo zerado?` | Local | Orienta `/zerados`; não usa IA nem envia comprovante para modelo. |
| `Como registrar uma run?` | Local | Orienta `/coliseu` → Runs e explica a revisão da moderação. |
| `Como remover um zerado duplicado?` | Local | Orienta `/remover_zerado`; não modifica o banco pelo chat. |
| `Quando recebo os Denários da platina?` | Local | Explica que a platina depende de aprovação e consulta as regras do servidor. |
| `Pesquise todos os troféus de God of War 2018` | Catálogo | Indica `/jogo_buscar`; o chat não gasta Gemini numa ferramenta de busca limitada a Elden Ring. |
| `Como conseguir todos os troféus de Lies of P?` | Catálogo | Indica `/jogo_buscar`; a pesquisa completa usa o fluxo grounding do Caçador. |
| `Como derrotar Malenia em Elden Ring?` | Local/sem Gemini | A pesquisa conversacional está desligada por padrão para preservar quota; a Nara explica que não fará chamada externa. |
| `Como derrotar o chefe final de Lies of P?` | Sem Gemini | Não inventa. Orienta a usar uma pesquisa apropriada ou o catálogo para troféus. |
| `Como remover um jogo zerado?` | Local | Explica o comando `/remover_zerado`.
| `Minha platina está pendente, quem aprova?` | Local | Explica a fila de revisão humana.
| `Onde vejo minhas runs?` | Local | Orienta `/coliseu` → Runs.
| `Como vejo o perfil de outro membro?` | Local | Orienta o menu de membros do Coliseu e reforça a privacidade de saldo/inventário.
| `Elden Ring é muito bom` | Fallback local | Não confunde menção a jogo com solicitação de pesquisa. |
| `Você consegue ler este print?` | Local/recusa | “Não. A Nara não abre nem analisa prints nesta conversa...” |
| `@Nara` + imagem sem texto | Recusa de imagem | Orienta a usar o formulário de comprovante apropriado. |
| `@Nara oi` + imagem | Local | Responde ao texto “oi”; o anexo não é aberto nem enviado. |
| Mensagem comum entre membros | Ignorar | Fora de canal livre, sem menção/resposta à Nara, não gera chamada. |

## Limites e economia

- `NARA_CHAT_IA_ENABLED=false`: padrão e recomendado. Impede chamadas externas pela conversa da Nara; DeepSeek/Gemini ficam reservados ao Caçador de Troféus.
- `NARA_CHAT_IA_ENABLED=true`: habilita pesquisa conversacional opcional sobre Elden Ring, com consumo de quota.
- `IA_LIMITE_DIARIO=3`: se a pesquisa conversacional for habilitada, limita a três pesquisas por membro/dia.
- `IA_LIMITE_DIARIO=0`: desativa o limite local por membro. Não recomendado.
- `COOLDOWN_SEG=8`: intervalo mínimo entre pesquisas conversacionais no chat por usuário.
- `/jogo_buscar`: mantém limite persistente próprio de três identificações por usuário a cada dez minutos.
- Se um jogo/alias já existe no catálogo, `/jogo_buscar` abre o catálogo existente sem chamar provedores externos.
- A pesquisa de catálogos só continua depois que o usuário confirma o candidato. O resultado entra em revisão; não há publicação automática.
- O circuit breaker global em `gemini_resilience.py` continua pausando chamadas em caso de quota/rate limit.
- `IA_CANAIS_LIVRES` recebe IDs de canais separados por vírgula. Neles a Nara responde apenas intenções locais reconhecidas; mensagens aleatórias não são enviadas a nenhum provedor externo.

**Importante para instalação existente:** o arquivo `.env` não é substituído durante a atualização. Confira `NARA_CHAT_IA_ENABLED=false` no `.env` e nas variáveis do painel da hospedagem. Se não existir, o padrão do código é `false`. Se quiser habilitar pesquisa conversacional por sua conta, altere explicitamente para `true`; nesse caso mantenha `IA_LIMITE_DIARIO=3`.

## Bloqueio de prints, imagens e arquivos

- A Nara de conversa recebe exclusivamente `message.clean_content` (texto digitado).
- `ia_nucleo.py` não aceita argumento de imagens no agente.
- `ia_gemini.py` constrói a mensagem do usuário com `Part(text=...)`; não usa `Part.from_bytes`.
- Anexos visuais são identificados apenas por MIME/nome para mostrar uma orientação; o código não lê os bytes do arquivo. A Nara não chama `read()`, `save()`, download ou OCR.
- As ferramentas de abrir páginas aceitam somente `text/html`, `application/xhtml+xml` e `text/plain`. Imagens, PDFs, vídeos e arquivos binários são recusados antes da leitura do corpo.
- O comprovante anexado nos formulários de Platinas/Runs/Zerados pertence ao fluxo específico de registro e revisão humana. Esses anexos não são encaminhados ao modelo da Nara.

## O que ainda usa IA externa

1. `/jogo_buscar`, quando o título não encontra correspondência no catálogo local: DeepSeek Search + Flash, com Gemini grounding como reserva automática.
2. Pesquisa detalhada do catálogo após a confirmação do candidato; usa o mesmo failover.
3. Pesquisa conversacional de Elden Ring somente se `NARA_CHAT_IA_ENABLED=true` (desligada por padrão), com DeepSeek principal e Gemini reserva.
4. Tradução de descrição de oferta apenas se `OFFERS_SHOW_DESCRIPTION=true`; mantém DeepSeek principal e Gemini reserva; mantenha `false` para máxima economia.

Com `NARA_CHAT_IA_ENABLED=false` e `OFFERS_SHOW_DESCRIPTION=false`, as APIs são usadas pelo `/jogo_buscar` somente quando catálogo/alias local não atende. O DeepSeek é tentado primeiro. Em erro classificado, o Gemini assume automaticamente. Cada fornecedor mantém saldo e quota próprios; circuit breakers independentes preservam a retomada automática após o período de pausa.

## Testes de regressão desta camada

```bash
pytest -q
python -m unittest discover -s tests -v
```

Os testes simulam mensagens básicas, perguntas sobre perfil, consultas privadas, rankings, remoção de zerados, aprovação/recompensa, pesquisas de catálogo, pesquisa conversacional bloqueada por padrão, anexos de imagem e tentativas de leitura de tipos binários.
