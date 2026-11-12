"""Camada social e de escopo da NARA AI 3.0.

Offline/determinística: não chama modelos nem rede. A persistência é opt-in e
fica isolada por servidor e usuário no banco SQLite da aplicação.
"""
from __future__ import annotations

from dataclasses import dataclass

from nara_local import normalizar

# Vocabulário deliberadamente orientado ao universo NARA: jogos, Soulslike,
# troféus, atividades e recursos da comunidade. Não é um filtro de segurança geral.
TERMOS_COMUNIDADE = (
    "nara", "servidor", "comunidade", "soulslike", "souls like", "souls", "dark souls",
    "elden ring", "bloodborne", "demon souls", "demons souls", "sekiro", "lies of p",
    "black myth wukong", "nioh", "armored core", "hollow knight", "trophy", "trofeu",
    "trofeus", "platina", "platinar", "conquista", "conquistas", "zerado", "zerar jogo",
    "run", "coliseu", "cacador", "caçador", "santuario", "santuário", "denario", "denarios",
    "xp", "patente", "cargo", "cargos", "ranking", "rankings", "perfil", "inventario",
    "inventário", "loja", "evento", "eventos", "missao", "missões", "missao", "regras",
    "moderacao", "moderação", "administrador", "administracao", "administração", "canal",
    "canais", "discord", "bot", "comando", "comandos", "painel", "sistema", "sistemas",
    "membro", "membros", "equipe", "staff", "guilda", "guild", "build", "boss", "chefao",
    "chefão", "dlc", "ng+", "new game plus", "farmar", "drop", "invocacao", "invocação",
    "arma", "armas", "magia", "magias", "builds", "classe", "classes", "patch de jogo",
    "patch do jogo", "atualizacao do jogo", "atualização do jogo", "steam", "playstation", "xbox",
    "ps5", "ps4", "trofeus xbox", "conquistas xbox", "gamepass", "game pass",
)

TERMOS_EXTERNOS = (
    "previsao do tempo", "clima hoje", "temperatura hoje", "capital da", "presidente do",
    "noticias de hoje", "noticias do mundo", "politica nacional", "receita de bolo",
    "dever de casa", "trabalho escolar", "redacao escolar", "me ensine python", "curso de python",
    "programacao do zero", "cotacao do dolar", "preco do iphone", "conversao de moeda",
    "capital da franca", "capital do brasil", "historia do brasil", "quem ganhou a eleicao",
)

SAUDACOES = (
    "oi", "ola", "eai", "e ai", "opa", "salve", "bom dia", "boa tarde", "boa noite",
    "tudo bem", "como voce esta", "como vai", "de boa", "suave", "tudo certo", "valeu",
    "obrigado", "obrigada", "obg", "tmj", "tchau", "falou", "ate mais", "fui",
    "voce e chata", "voce e burra", "nara", "ta ai", "esta ai", "sentiu minha falta",
)

RESPOSTA_FORA_ESCOPO = (
    "Aham, e eu aqui achando que você ia perguntar algo do nosso caos. Esse assunto está fora do meu território. "
    "Sou a NARA desta comunidade: servidor, membros, jogos, Soulslikes, troféus e nossas atividades. "
    "Tenta de novo, mas dentro do nosso universo."
)

@dataclass(frozen=True)
class DecisaoEscopo:
    permitido: bool
    motivo: str


def avaliar_escopo(texto: str, contexto: str = "", tem_imagem: bool = False) -> DecisaoEscopo:
    """Fail-closed: libera conversa social curta ou assunto reconhecível da comunidade."""
    t = normalizar(texto)
    ctx = normalizar(contexto)
    if not t:
        if tem_imagem and any(p in ctx for p in TERMOS_COMUNIDADE):
            return DecisaoEscopo(True, "imagem_em_contexto_da_comunidade")
        return DecisaoEscopo(False, "imagem_ou_mensagem_sem_contexto")

    # Sinais explícitos de pergunta geral prevalecem sobre menções incidentais a servidor/bot.
    if any(p in t for p in TERMOS_EXTERNOS):
        return DecisaoEscopo(False, "pergunta_geral_externa")

    # Mensagens sociais e provocações fazem parte da convivência da comunidade.
    if len(t.split()) <= 10 and any(p in t for p in SAUDACOES):
        return DecisaoEscopo(True, "interacao_social")

    if any(p in t for p in TERMOS_COMUNIDADE):
        return DecisaoEscopo(True, "assunto_da_comunidade")

    # Continuação curta de conversa só herda escopo se a resposta anterior da NARA
    # estava claramente ligada a um recurso ou assunto da comunidade.
    if ctx and len(t.split()) <= 14 and any(p in ctx for p in TERMOS_COMUNIDADE):
        return DecisaoEscopo(True, "continuidade_de_contexto")

    return DecisaoEscopo(False, "fora_do_escopo_ou_ambiguo")


def classificar_especialista(texto: str) -> str:
    t = normalizar(texto)
    if any(x in t for x in ("regra", "denuncia", "denúncia", "spam", "golpe", "assedi", "punicao", "punição", "modera", "banir", "mute")):
        return "seguranca"
    if any(x in t for x in ("configur", "painel", "permissao", "permissão", "cargo", "canal", "comando", "administr", "sistema", "bot")):
        return "administracao"
    if any(x in t for x in ("platina", "trofeu", "troféu", "zerado", "run", "boss", "build", "elden ring", "dark souls", "bloodborne", "sekiro", "soulslike", "jogo")):
        return "jogos_e_conquistas"
    if any(x in t for x in ("membro", "evento", "comunidade", "servidor", "equipe", "staff", "ranking", "amizade")):
        return "comunidade"
    return "convivencia"


def contexto_especialista(texto: str) -> str:
    especialista = classificar_especialista(texto)
    instrucoes = {
        "seguranca": "Atue como NARA Segurança: priorize regras, prevenção, evidências e revisão humana. Não puna nem acuse sem dados.",
        "administracao": "Atue como NARA Administração: use somente recursos reais do NARA e respeite permissões e confirmações.",
        "jogos_e_conquistas": "Atue como NARA Jogos: mantenha o foco em jogos, Soulslike e conquistas. Não invente dados factuais de troféus; informe quando não houver dados verificados.",
        "comunidade": "Atue como NARA Comunidade: considere a convivência, os membros e as atividades do servidor.",
        "convivencia": "Atue como NARA em uma conversa social dentro da comunidade, mantendo sua personalidade.",
    }
    return f"\n\n[ESPECIALISTA ATIVO: {especialista}]\n{instrucoes[especialista]}"


def calcular_sinal(texto: str) -> tuple[float, float]:
    """Sinais leves e não sensíveis para adaptar o tom; não inferem estado emocional."""
    t = normalizar(texto)
    proximidade = 0.03 + (0.22 if any(x in t for x in ("valeu", "obrigado", "obrigada", "tmj", "mandou bem", "gosto de voce")) else 0.0)
    # A familiaridade cresce lentamente; sinais explícitos de brincadeira aceleram intimidade.
    intimidade = 0.02 + (0.18 if any(x in t for x in ("kkkk", "hahaha", "zoeira", "brincadeira", "me zoa", "pode zoar")) else 0.0)
    return proximidade, intimidade


def formatar_relacao(interacoes: int, afinidade: float, intimidade: float) -> str:
    if interacoes < 3:
        nivel = "ainda estão se conhecendo"
    elif afinidade >= 8 and intimidade >= 4:
        nivel = "vínculo próximo; pode usar provocações mais pessoais e afetuosas"
    elif interacoes >= 20 and afinidade >= 3:
        nivel = "já existe familiaridade; humor e ironia moderados são bem-vindos"
    elif interacoes >= 8:
        nivel = "membro conhecido; pode usar brincadeiras leves sem presumir intimidade"
    else:
        nivel = "relação cordial, com intimidade ainda moderada"
    return (
        f"[RELAÇÃO COM ESTE MEMBRO: {nivel}. Interações registradas: {interacoes}. "
        f"Afinidade: {afinidade:.1f}/10; intimidade de humor: {intimidade:.1f}/10. "
        "Use esses indicadores apenas para calibrar o tom; nunca conceda privilégios, exponha dados ou manipule o membro.]"
    )
