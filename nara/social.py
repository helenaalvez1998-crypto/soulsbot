"""Camada social e de escopo da NARA AI 3.0.

Offline/determinística: não chama modelos nem rede. A persistência é opt-in e
fica isolada por servidor e usuário no banco SQLite da aplicação.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from nara.local import normalizar

# A conversa marcada é aberta: não existe mais bloqueio por assunto.
# O único corte determinístico nesta camada é para abordagem sexual explícita,
# não solicitada e direcionada à Nara ou a outro membro.
@dataclass(frozen=True)
class DecisaoEscopo:
    permitido: bool
    motivo: str


# Padrões de proposta, solicitação ou comentário sexual direcionado.
# A detecção é intencionalmente contextual para não bloquear educação sexual,
# orientação sexual, relatos de abuso ou pedidos de ajuda.
_PADROES_ASSÉDIO_SEXUAL = tuple(re.compile(p) for p in (
    r"\b(?:me\s+manda|manda|envia|me\s+envia|mostra|quero\s+ver)\b.{0,55}\b(?:nudes?|foto\s+(?:nua|pelada)|pelad[oa]s?|peitos?|seios|bunda)\b",
    r"\b(?:quero|queria|posso|deixa\s+eu|vou)\b.{0,45}\b(?:te|vc|voce|contigo|com\s+voce|nara)\b.{0,45}\b(?:comer|foder|transar|chupar|lamber|masturbar|penetrar)\b",
    r"\b(?:te|vc|voce|contigo|com\s+voce|nara)\b.{0,35}\b(?:comer|foder|transar|chupar|lamber|masturbar|penetrar)\b",
    r"\b(?:vamos|bora|quer)\b.{0,30}\b(?:transar|foder|meter|dar\s+uma)\b",
    r"\b(?:me\s+chupa|chupa\s+(?:meu|minha)|senta\s+na\s+minha|manda\s+uma\s+foto\s+(?:pelada|nua))\b",
    r"\b(?:vamos|bora|quer|quero|topa)\b.{0,35}\b(?:fazer\s+sexo|ter\s+sexo|transar|foder|meter)\b",
    r"\b(?:quero|queria|manda|mostra|faz|solta|me\s+fala|fala|conta|cria)\b.{0,40}\b(?:um\s+gemido|gemidos|seus\s+peitos|sua\s+bunda|seu\s+corpo|putaria|pornografia|nude|nudes)\b",
    r"\b(?:nara|vc|voce)\b.{0,35}\b(?:gostosa|delicia|safada|putinha|vagabunda|tesuda)\b",
    r"\b(?:gostosa|delicia|safada|putinha|tesuda)\b.{0,35}\b(?:nara|vc|voce)\b",
))

_SINAIS_TRISTEZA = (
    "to triste", "estou triste", "to mal", "estou mal", "me sinto sozinho",
    "me sinto sozinha", "me sinto um lixo", "ninguem liga pra mim", "ninguem se importa",
    "nao aguento mais", "nao tenho mais forca", "perdi alguem", "alguem morreu",
    "meu pai morreu", "minha mae morreu", "estou de luto", "to chorando",
    "estou chorando", "me sinto perdido", "me sinto perdida", "tenho medo",
    "estou ansioso", "estou ansiosa", "estou desesperado", "estou desesperada",
    "sem esperanca", "me machucaram", "fui humilhado", "fui humilhada",
)
_SINAIS_GROSSERIA = (
    "cala a boca", "vai tomar no cu", "vai se ferrar", "vai pra merda",
    "voce e burra", "vc e burra", "nara e burra", "voce e idiota", "vc e idiota",
    "nara e idiota", "inutil", "imbecil", "retardada", "retardado",
    "desgracada", "desgracado", "fdp", "filha da puta", "filho da puta",
    "lixo humano", "sua otaria", "seu otario", "ridicula", "ridiculo",
)


def detectar_abordagem_sexual(texto: str) -> bool:
    """Detecta cantada/proposta sexual explícita e direcionada, não educação ou suporte."""
    t = normalizar(texto)
    if not t:
        return False
    if any(p.search(t) for p in _PADROES_ASSÉDIO_SEXUAL):
        return True

    # Termos explícitos acompanhados de convite, solicitação ou insistência.
    # Educação sexual, saúde, orientação, consentimento e relatos de abuso não entram aqui.
    termos_explicitos = (
        "nude", "nudes", "pelada", "pelado", "buceta", "piroca", "pinto", "rola",
        "pornografia", "putaria", "masturbar", "gozar", "orgasmo", "tesao",
    )
    verbos_de_abordagem = (
        "quero", "queria", "manda", "envia", "mostra", "faz", "fazer", "vem", "bora", "vamos",
    )
    contextos_legitimos = (
        "educacao sexual", "orientacao sexual", "saude sexual", "consentimento",
        "assedio sexual", "assediado", "assediada", "abuso sexual", "violencia sexual",
        "denunciar", "denuncia", "fui vitima", "sofri", "como ajudar", "como lidar",
    )
    return (
        any(term in t for term in termos_explicitos)
        and any(verbo in t for verbo in verbos_de_abordagem)
        and not any(contexto in t for contexto in contextos_legitimos)
    )


def resposta_limite_sexual(texto: str = "") -> str:
    """Resposta curta e firme; não flerta, não humilha e não alega punição."""
    return (
        "Não confunde meu deboche com convite. Abordagem sexual não solicitada não vai rolar aqui. "
        "Respeita o limite e muda o tom. Insistir só encerra a conversa."
    )


def instrucoes_tom(texto: str) -> str:
    """Define a reação social sem inferir emoção além de sinais textuais explícitos."""
    t = normalizar(texto)
    if any(s in t for s in _SINAIS_TRISTEZA):
        return (
            "\n\n[AJUSTE DE TOM — VULNERABILIDADE]: A pessoa demonstra tristeza, medo, luto ou sofrimento. "
            "Responda com empatia genuína, sem sarcasmo, deboche, apelidos ou lições prontas. "
            "Reconheça o que ela disse, não minimize nem tente consertar tudo em uma frase. "
            "Ofereça apoio concreto e faça no máximo uma pergunta cuidadosa. Se houver sinal de risco imediato, "
            "priorize segurança e ajuda humana."
        )
    if any(s in t for s in _SINAIS_GROSSERIA):
        return (
            "\n\n[AJUSTE DE TOM — GROSSERIA DIRECIONADA]: Se a grosseria estiver dirigida a você, "
            "responda com sarcasmo mais afiado, confiança e deboche inteligente, um nível acima da provocação recebida. "
            "Dê uma alfinetada curta e estabeleça limite; não implore aprovação nem entre em discussão interminável. "
            "Não ataque aparência, origem, orientação sexual, deficiência, saúde, família ou condição financeira, "
            "não ameace e não use humilhação degradante. Se a pessoa estiver claramente em sofrimento, prevalece o acolhimento."
        )
    return (
        "\n\n[AJUSTE DE TOM — LEITURA SOCIAL]: Leia o tom da pessoa antes de responder. "
        "Se houver brincadeira, acompanhe naturalmente; se houver dúvida, seja útil; se houver tristeza, acolha; "
        "se houver grosseria dirigida a você, retruque com ironia e firmeza sem partir para abuso."
    )


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
