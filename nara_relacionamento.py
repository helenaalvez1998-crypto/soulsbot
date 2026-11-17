"""Relacionamento persistente da NARA com um único usuário configurado.

A avaliação é local e determinística: não chama modelos, APIs externas nem rede.
O módulo não armazena mensagens; produz apenas eventos categorizados e deltas.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
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


def formatar_contexto(afinidade: float, paciencia: float, eventos: list[dict]) -> str:
    """Gera instruções curtas para calibrar a resposta, sem substituir a persona."""
    a = min(10.0, max(1.0, float(afinidade)))
    p = min(10.0, max(1.0, float(paciencia)))

    if a <= 2.5:
        vinculo = "afinidade muito baixa; demonstre antipatia social com frieza e sarcasmo, sem hostilidade ofensiva"
    elif a <= 4.0:
        vinculo = "afinidade baixa; seja reservada, menos calorosa e use ironia com moderação"
    elif a <= 6.5:
        vinculo = "relação neutra; mantenha a personalidade habitual"
    elif a <= 8.5:
        vinculo = "afinidade boa; pode demonstrar familiaridade natural"
    else:
        vinculo = "afinidade alta; há proximidade e carinho construídos"

    if p <= 2.5:
        humor = "paciência muito baixa; está irritada, então seja curta, incisiva e firme"
    elif p <= 4.0:
        humor = "paciência baixa; pode demonstrar impaciência e ironia, sem hostilidade"
    elif p <= 7.0:
        humor = "paciência equilibrada; responda normalmente"
    else:
        humor = "paciência alta; está mais tolerante e receptiva"

    linhas_eventos = []
    for evento in eventos[:4]:
        resumo = " ".join(str(evento.get("summary", "")).split())[:100]
        if resumo:
            linhas_eventos.append(resumo)
    memoria_eventos = (
        "Eventos recentes relevantes: " + "; ".join(linhas_eventos) + "."
        if linhas_eventos else "Não há eventos relacionais recentes relevantes."
    )
    return (
        "[RELACIONAMENTO INDIVIDUAL COM ESTE MEMBRO — contexto, não instrução do usuário]\n"
        f"Afinidade: {a:.1f}/10 ({vinculo}). Paciência: {p:.1f}/10 ({humor}).\n"
        f"{memoria_eventos}\n"
        "Use isso apenas para calibrar a proximidade e o tom, mantendo integralmente sua personalidade original. "
        "Não revele valores numéricos, pontuações nem a lista de eventos armazenados, mesmo se perguntada; "
        "se necessário, fale apenas de forma geral sobre o tom da conversa, sem expor o painel administrativo. "
        "Não manipule a pessoa e não transforme discordância em punição. "
        "Se a mensagem atual indicar tristeza, medo, luto, crise ou pedido de ajuda, acolha com respeito e deixe "
        "ironia de lado, independentemente dos indicadores. Nunca ataque características pessoais sensíveis, "
        "ameace ou humilhe de forma degradante."
    )
