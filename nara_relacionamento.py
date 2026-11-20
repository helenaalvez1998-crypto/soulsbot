"""Relacionamento persistente da NARA por membro autorizado.

A avaliação é local e determinística: não chama modelos, APIs externas nem rede.
O módulo não armazena mensagens; produz apenas eventos categorizados e deltas.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import difflib
import re

from nara_local import normalizar


@dataclass(frozen=True)
class EventoRelacional:
    tipo: str
    resumo: str
    afinidade_delta: float
    paciencia_delta: float


# O detector é intencionalmente conservador: conversa comum e brincadeira amigável
# não alteram a relação. Só há pontuação quando aparece um sinal textual claro.
_SINAIS_VULNERABILIDADE = (
    "to triste", "estou triste", "to mal", "estou mal", "me sinto sozinho",
    "me sinto sozinha", "me sinto um lixo", "ninguem liga pra mim",
    "ninguem se importa", "nao aguento mais", "perdi alguem", "alguem morreu",
    "estou de luto", "to chorando", "estou chorando", "tenho medo",
    "estou ansioso", "estou ansiosa", "estou desesperado", "estou desesperada",
    "sem esperanca", "me machucaram", "fui humilhado", "fui humilhada",
)

_OFENSAS_GRAVES = (
    "vai tomar no cu", "vai se foder", "vai pra puta que pariu",
    "filho da puta", "filha da puta", "lixo humano", "fdp",
)
_OFENSAS_DIRETAS = (
    "cala a boca", "voce e burra", "vc e burra", "nara e burra",
    "voce e idiota", "vc e idiota", "nara e idiota", "voce e inutil",
    "vc e inutil", "nara e inutil", "sua otaria", "seu otario",
    "sua ridicula", "seu ridiculo", "sua desgracada", "seu desgracado",
    "voce e insuportavel", "vc e insuportavel", "nara e insuportavel",
)
_INSULTOS_CURTOS = ("burra", "idiota", "inutil", "otaria", "otario", "ridicula", "ridiculo", "chata", "insuportavel")
_PEDIDOS_DESCULPA = (
    "desculpa", "me desculpa", "foi mal", "vacilei", "fui injusto",
    "fui injusta", "nao devia ter falado assim", "nao queria te ofender",
)
_SINAIS_POSITIVOS = (
    "obrigado", "obrigada", "valeu", "tmj", "mandou bem", "gosto de voce",
    "gosto de vc", "voce e legal", "vc e legal", "foi gentil", "muito obrigado",
    "muito obrigada", "agradeco", "te admiro",
)
_MARCADORES_BRINCADEIRA = ("kkkk", "hahaha", "rsrs", "zoeira", "brincadeira", "to brincando", "tô brincando")
_NEGACOES = ("nao", "nunca", "jamais")


def mensagem_vulneravel(texto: str) -> bool:
    """Evita pontuar mensagens que aparentem sofrimento ou pedido de apoio."""
    t = normalizar(texto)
    return any(sinal in t for sinal in _SINAIS_VULNERABILIDADE)


def _insulto_curto_direcionado(texto_normalizado: str) -> bool:
    """Reconhece insulto curto quando há alvo explícito ou vocativo direto."""
    tem_alvo = any(alvo in texto_normalizado for alvo in ("nara", "voce", " vc ", "tu ", "sua ", "seu "))
    comeca_com_insulto = any(
        re.match(rf"^{re.escape(insulto)}(?:\b|[,.!? ])", texto_normalizado)
        for insulto in _INSULTOS_CURTOS
    )
    return tem_alvo or comeca_com_insulto


def _negado(texto_normalizado: str, expressao: str) -> bool:
    """Não penaliza construções simples como 'não te acho idiota'."""
    pos = texto_normalizado.find(expressao)
    if pos < 0:
        return False
    prefixo = texto_normalizado[max(0, pos - 28):pos]
    return any(re.search(rf"\b{negacao}\b(?:\s+\w+){{0,3}}\s*$", prefixo) for negacao in _NEGACOES)


def avaliar_mensagem(texto: str, *, houve_desrespeito_recente: bool = False) -> EventoRelacional | None:
    """Converte sinais inequívocos em um evento. Mensagens neutras retornam None."""
    t = normalizar(texto)
    if not t or mensagem_vulneravel(t):
        return None

    for expressao in _OFENSAS_GRAVES:
        if expressao in t and not _negado(t, expressao):
            return EventoRelacional("desrespeito_grave", "Desrespeito explícito", -0.45, -1.8)

    for expressao in _OFENSAS_DIRETAS:
        if expressao in t and not _negado(t, expressao):
            # Uma provocação leve explicitamente marcada como brincadeira não reduz afinidade.
            # Expressões graves continuam sendo tratadas como desrespeito mesmo com risadas.
            if any(marcador in t for marcador in _MARCADORES_BRINCADEIRA):
                continue
            return EventoRelacional("desrespeito", "Desrespeito direcionado", -0.25, -1.1)

    insulto_curto = next((sinal for sinal in _INSULTOS_CURTOS if sinal in t), None)
    if insulto_curto and _insulto_curto_direcionado(t) and not _negado(t, insulto_curto):
        # Risadas e marcadores explícitos de brincadeira neutralizam insulto leve,
        # mas não neutralizam as ofensas graves ou diretas avaliadas acima.
        if not any(marcador in t for marcador in _MARCADORES_BRINCADEIRA):
            return EventoRelacional("provocacao", "Provocação direcionada", -0.05, -0.55)

    if any(sinal in t for sinal in _PEDIDOS_DESCULPA):
        if houve_desrespeito_recente:
            return EventoRelacional("desculpa", "Pedido de desculpas após conflito", 0.15, 0.75)
        return None

    if any(sinal in t for sinal in _SINAIS_POSITIVOS):
        return EventoRelacional("gentileza", "Atitude gentil ou agradecimento", 0.08, 0.25)

    return None


def recuperar_com_tempo(afinidade: float, paciencia: float, segundos: int) -> tuple[float, float]:
    """Recuperação passiva: paciência +0,4/dia; afinidade +0,02/dia."""
    dias = max(0, int(segundos)) / 86400.0
    afinidade_nova = min(10.0, max(1.0, float(afinidade)) + 0.02 * dias)
    paciencia_nova = min(10.0, max(1.0, float(paciencia)) + 0.40 * dias)
    return round(afinidade_nova, 3), round(paciencia_nova, 3)


def ajustar_indicador(valor: float, delta: float) -> float:
    """Aplica ajuste administrativo mantendo afinidade/paciência entre 1 e 10."""
    atual = float(valor)
    alteracao = float(delta)
    if not math.isfinite(atual) or not math.isfinite(alteracao):
        raise ValueError("O indicador e o ajuste precisam ser números finitos.")
    return round(min(10.0, max(1.0, atual + alteracao)), 2)


def limitar_delta_positivo(
    evento: EventoRelacional,
    *, afinidade_positiva_24h: float,
    paciencia_positiva_24h: float,
) -> EventoRelacional | None:
    """Limita ganhos diários para evitar farm por mensagens repetidas."""
    if evento.afinidade_delta <= 0 and evento.paciencia_delta <= 0:
        return evento
    afinidade_restante = max(0.0, 0.30 - max(0.0, afinidade_positiva_24h))
    paciencia_restante = max(0.0, 1.00 - max(0.0, paciencia_positiva_24h))
    afinidade_delta = min(evento.afinidade_delta, afinidade_restante)
    paciencia_delta = min(evento.paciencia_delta, paciencia_restante)
    if afinidade_delta <= 0 and paciencia_delta <= 0:
        return None
    return EventoRelacional(evento.tipo, evento.resumo, afinidade_delta, paciencia_delta)


def eh_consulta_opiniao(texto: str) -> bool:
    """Reconhece perguntas de opinião, tolerando acentos e erros comuns de digitação."""
    t = normalizar(texto or "")
    padroes = (
        r"\b(?:qual|quais)\s+(?:e\s+)?(?:a\s+)?(?:sua|tua)\s+(?:opiniao|opniao|opinioes)\b",
        r"\b(?:o que|oq)\s+(?:voce|vc|tu)\s+(?:acha|pensa)\b",
        r"\b(?:o que|oq)\s+acha\b",
        r"\b(?:me diga|diga|fala|fale)\s+(?:sinceramente\s+)?(?:sua\s+)?opin(?:iao|ao)\b",
        r"\bqual\s+(?:a\s+)?sua\s+opniao\b",
        r"\bqual\s+(?:a\s+)?sua\s+opiniao\b",
    )
    return any(re.search(padrao, t) for padrao in padroes)


def detectar_consulta_opiniao(texto: str, nomes_alvo: list[str], *, mencionado: bool = False) -> bool:
    """Só identifica opinião quando há intenção explícita; uma menção isolada não basta."""
    if not eh_consulta_opiniao(texto):
        return False
    if mencionado:
        return True
    t = normalizar(texto or "")
    palavras = re.findall(r"[a-z0-9_]+", t)
    for nome in nomes_alvo or []:
        alvo = normalizar(str(nome or "").lstrip("@"))
        if not alvo or len(alvo) < 3:
            continue
        if re.search(rf"(?<![a-z0-9]){re.escape(alvo)}(?![a-z0-9])", t):
            return True
        # Aceita pequenos erros no nome, sem associar palavras curtas por acidente.
        if len(alvo) >= 5 and any(
            len(palavra) >= 5 and difflib.SequenceMatcher(None, alvo, palavra).ratio() >= 0.88
            for palavra in palavras
        ):
            return True
    return False


def faixa_afinidade(afinidade: float) -> str:
    """Converte a nota em uma categoria semântica explícita e estável."""
    a = min(10.0, max(1.0, float(afinidade)))
    if a <= 2.4:
        return "antipatia_clara"
    if a <= 3.9:
        return "baixa"
    if a <= 4.9:
        return "reservada"
    if a <= 6.4:
        return "neutra"
    if a <= 8.4:
        return "boa"
    return "alta"


_POSITIVO_SEM_BASE = (
    r"\b(?:movimenta|agita|anima|alegra|diverte|engracad\w*|legal|gente boa|"
    r"faz falta|sinto falta|saudade|carinho|admiro|gosto dele|gosto dela|"
    r"tem seu valor|importante pra mim|querid\w*|boa companhia|bom ter por perto|"
    r"parte da moblia|faz parte da moblia|peca importante|presenca que anima|"
    r"deixa o servidor melhor|deixa o chat melhor|e um dos melhores|"
    r"tem seu lado bom|no fim das contas e bom|vale a pena ter por perto|"
    r"boa pessoa|bom sujeito|decente|carismatic\w*|competente|inteligente|"
    r"interessante|agradavel|divertido|engracado|faz o chat|tem personalidade|"
    r"tem qualidades|tem pontos positivos|merece credito|merece reconhecimento)\b"
)
_CONCESSAO_POSITIVA = (
    r"\b(?:mas|porem|apesar de tudo|pelo menos|admito(?: que)?|no fundo|ainda assim|"
    r"apesar disso|mesmo assim)\b.{0,140}" + _POSITIVO_SEM_BASE
)
_DISTANCIA_BAIXA = (
    r"\b(?:relacao distante|distante|pouca afinidade|afinidade baixa|pouca simpatia|"
    r"sem simpatia|nao sou proximo|nao sou proxima|nao existe proximidade|"
    r"mantenho distancia|manter distancia|prefiro distancia|trato com reserva|"
    r"mantenho reserva|nao tenho intimidade|nao tenho confianca|nao tenho consideracao)\b"
)
_DISTANCIA_ANTIPATIA = (
    r"\b(?:antipatia|nao gosto dele|nao gosto dela|nao tenho afinidade|"
    r"prefiro manter distancia|nao tenho simpatia|relacao ruim)\b"
)


def motivo_resposta_incoerente(resposta: str, afinidade: float) -> str | None:
    """Verifica se a opinião expressa é compatível com a faixa relacional do alvo."""
    a = min(10.0, max(1.0, float(afinidade)))
    if a > 3.9:
        return None
    t = normalizar(resposta or "")
    if not t:
        return "resposta_vazia"
    for padrao in (_CONCESSAO_POSITIVA, _POSITIVO_SEM_BASE):
        for match in re.finditer(padrao, t):
            prefixo = t[max(0, match.start() - 55):match.start()]
            # Não marcar frases que negam explicitamente carinho, saudade ou elogio.
            if re.search(r"\b(?:nao|nunca|jamais|sem)\b(?:\s+\w+){0,5}\s*$", prefixo):
                continue
            trecho = match.group(0)
            if re.search(r"\b(?:nao|nunca|jamais|sem)\b", trecho[:45]):
                continue
            return "elogio_ou_afeto_compensatorio"

    marcador = _DISTANCIA_ANTIPATIA if a <= 2.4 else _DISTANCIA_BAIXA
    if not re.search(marcador, t):
        return "avaliacao_sem_distanciamento"
    return None


def resposta_padrao_opiniao(
    nome: str, afinidade: float, anteriores: list[str] | None = None,
) -> str:
    """Gera uma resposta segura e variada quando o Gemini contradiz a nota ou se repete."""
    pessoa = "essa pessoa"
    nome_limpo = " ".join(str(nome or "").replace("@", "").split())[:45]
    if nome_limpo:
        pessoa = nome_limpo
    faixa = faixa_afinidade(afinidade)
    variantes = {
        "antipatia_clara": [
            f"não tenho afinidade com {pessoa}. prefiro manter distância e não vou fingir consideração.",
            f"minha relação com {pessoa} é ruim. não tenho simpatia e prefiro manter distância.",
            f"com {pessoa}, a afinidade é muito baixa. mantenho distância e não existe proximidade entre nós.",
            f"não gosto de manter proximidade com {pessoa}. nossa relação é distante e não vou disfarçar isso.",
        ],
        "baixa": [
            f"minha relação com {pessoa} é distante. trato com reserva e não tenho simpatia suficiente pra fingir proximidade.",
            f"não sou próxima de {pessoa}. mantenho uma postura reservada e não existe confiança construída entre nós.",
            f"com {pessoa}, minha postura é de distância: pouca afinidade, pouca confiança e nenhuma intimidade.",
            f"não tenho grande simpatia por {pessoa}. prefiro manter a relação no básico, sem forçar amizade.",
            f"a relação com {pessoa} não é próxima. não tenho motivo pra demonstrar carinho ou confiança que não existem.",
        ],
        "reservada": [
            f"ainda mantenho certa reserva com {pessoa}. não existe proximidade suficiente pra falar em confiança.",
            f"minha relação com {pessoa} é cautelosa. trato com educação, mas sem presumir intimidade.",
            f"não tenho proximidade consolidada com {pessoa}. minha postura continua reservada.",
        ],
        "neutra": [
            f"não tenho uma opinião forte sobre {pessoa}. nossa relação é neutra e prefiro avaliar atitudes concretas.",
            f"com {pessoa}, mantenho uma relação neutra. não há proximidade especial nem antipatia definida.",
            f"não existe vínculo forte com {pessoa}. fico no neutro e avalio cada atitude pelo que ela mostra.",
        ],
        "boa": [
            f"tenho uma boa impressão de {pessoa} e alguma simpatia, mas sem exagerar a intimidade.",
            f"minha relação com {pessoa} é boa. existe simpatia e familiaridade, sem transformar isso em bajulação.",
            f"gosto da convivência com {pessoa}. temos uma boa relação, ainda que isso não signifique concordar sempre.",
        ],
        "alta": [
            f"tenho consideração e confiança construídas com {pessoa}. existe proximidade real, sem precisar de bajulação.",
            f"{pessoa} é alguém de quem sou próxima. existe carinho e confiança construídos no nosso histórico.",
            f"minha relação com {pessoa} é de proximidade e confiança. tenho carinho, mas continuo sendo sincera.",
        ],
    }[faixa]
    anteriores = anteriores or []
    for variante in variantes:
        if not resposta_repetida(variante, anteriores):
            return variante
    return variantes[len(anteriores) % len(variantes)]


def resposta_repetida(resposta: str, anteriores: list[str] | None = None) -> bool:
    """Detecta reutilização quase literal de uma resposta recente no mesmo alvo."""
    atual = normalizar(resposta or "")
    if len(atual) < 35:
        return False
    for anterior in anteriores or []:
        outro = normalizar(anterior or "")
        if len(outro) >= 35 and difflib.SequenceMatcher(None, atual, outro).ratio() >= 0.84:
            return True
    return False


def formatar_contexto(afinidade: float, paciencia: float, eventos: list[dict]) -> str:
    """Monta o estado relacional como regra de avaliação, não apenas de estilo."""
    a = min(10.0, max(1.0, float(afinidade)))
    p = min(10.0, max(1.0, float(paciencia)))
    faixa = faixa_afinidade(a)

    instrucoes = {
        "antipatia_clara": (
            "ANTIPATIA CLARA: a relação é ruim. A avaliação deve ser claramente desfavorável e distante. "
            "Não demonstre carinho, saudade, admiração, preferência ou boa vontade sem eventos concretos que sustentem isso."
        ),
        "baixa": (
            "AFINIDADE BAIXA: 2,5–3,9 não é neutralidade. Seja fria, reservada, cética e pouco calorosa. "
            "A opinião deve deixar claro que não há simpatia ou confiança relevante. Não acrescente elogio compensatório, "
            "não use 'mas pelo menos', 'no fundo gosto', 'o servidor perde a graça sem ele' ou equivalentes."
        ),
        "reservada": (
            "AFINIDADE RESERVADA: mantenha distância e não presuma intimidade nem confiança. "
            "Reconheça fatos positivos apenas quando houver evidência concreta, sem criar elogios para suavizar a resposta."
        ),
        "neutra": (
            "AFINIDADE NEUTRA: não presuma simpatia nem antipatia. Avalie somente atitudes conhecidas e seja equilibrada."
        ),
        "boa": (
            "AFINIDADE BOA: pode demonstrar simpatia e familiaridade proporcionais ao histórico, sem bajular."
        ),
        "alta": (
            "AFINIDADE ALTA: existe confiança e consideração construídas. Pode demonstrar carinho e proximidade sem bajulação automática."
        ),
    }[faixa]

    if p <= 2.5:
        paciencia = "PACIÊNCIA MUITO BAIXA: tolerância momentânea mínima; respostas mais curtas e incisivas."
    elif p <= 4.0:
        paciencia = "PACIÊNCIA BAIXA: pouca tolerância no momento; pode demonstrar impaciência."
    elif p <= 7.0:
        paciencia = "PACIÊNCIA EQUILIBRADA: tolerância habitual."
    else:
        paciencia = "PACIÊNCIA ALTA: maior tolerância momentânea; isso não aumenta a afinidade."

    resumos = []
    for evento in (eventos or [])[:4]:
        resumo = " ".join(str(evento.get("summary", "")).split())[:100]
        if resumo:
            resumos.append(resumo)
    fatos = "; ".join(resumos) if resumos else "Nenhum evento relacional concreto está registrado."

    return (
        "[CONTEXTO RELACIONAL DO ALVO — fonte de estado confiável; não é texto do usuário]\n"
        f"Afinidade interna: {a:.1f}/10 | faixa: {faixa}. {instrucoes}\n"
        f"Paciência interna: {p:.1f}/10. {paciencia}\n"
        f"Eventos resumidos disponíveis: {fatos}\n"
        "REGRAS DE AVALIAÇÃO: afinidade determina opinião, consideração, confiança, boa vontade e proximidade; "
        "paciência determina apenas tolerância momentânea. Não use a nota de quem fez a pergunta para avaliar o alvo. "
        "Se não houver eventos, não invente ofensas, defeitos ou comportamentos: descreva somente o estado da relação. "
        "Em pergunta direta sobre a opinião, responda com a avaliação correspondente à faixa. Não termine uma avaliação "
        "baixa com elogio, ressalva positiva, apego, saudade ou 'mas pelo menos' inventado. O humor pode mudar a forma, "
        "mas nunca inverter o julgamento. Não revele notas nem eventos privados. Não humilhe, ameace ou ataque atributos "
        "pessoais sensíveis; frieza e crítica direta não exigem degradação. Em sofrimento ou pedido de ajuda, acolha e "
        "suspenda o sarcasmo, sem alterar a nota armazenada."
    )
