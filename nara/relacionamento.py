"""Relacionamento persistente da NARA por membro autorizado.

A avaliação é local e determinística: não chama modelos, APIs externas nem rede.
O módulo não armazena mensagens; produz apenas eventos categorizados e deltas.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import difflib
import re

from nara.local import normalizar


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
def motivo_resposta_incoerente(resposta: str, afinidade: float) -> str | None:
    """Rejeita afeto/elogio incompatível com afinidade baixa, sem exigir rótulos explícitos.

    A nota deve orientar a atitude da Nara. A resposta não precisa declarar que a relação
    é distante, fria ou neutra; exigir essas palavras transforma o comportamento em roteiro.
    """
    a = min(10.0, max(1.0, float(afinidade)))
    if a > 3.9:
        return None
    t = normalizar(resposta or "")
    if not t:
        return "resposta_vazia"

    # Um elogio direto ou uma concessão positiva inventada é incompatível com afinidade
    # baixa. Negativas explícitas ("não sinto falta", "não tenho carinho") são permitidas.
    for padrao in (_CONCESSAO_POSITIVA, _POSITIVO_SEM_BASE):
        for match in re.finditer(padrao, t):
            prefixo = t[max(0, match.start() - 55):match.start()]
            if re.search(r"\b(?:nao|nunca|jamais|sem)\b(?:\s+\w+){0,5}\s*$", prefixo):
                continue
            trecho = match.group(0)
            if re.search(r"\b(?:nao|nunca|jamais|sem)\b", trecho[:45]):
                continue
            return "elogio_ou_afeto_compensatorio"

    # Não exigir frases como "nossa relação é distante". A personalidade pode aparecer
    # por ironia, concisão, escolha de palavras ou falta de intimidade, sem explicar a nota.
    return None


def resposta_padrao_opiniao(
    nome: str, afinidade: float, anteriores: list[str] | None = None,
) -> str:
    """Resposta de contingência natural, usada só quando o Gemini contradiz ou se repete."""
    pessoa = "essa pessoa"
    nome_limpo = " ".join(str(nome or "").replace("@", "").split())[:45]
    if nome_limpo:
        pessoa = nome_limpo
    faixa = faixa_afinidade(afinidade)
    variantes = {
        "antipatia_clara": [
            f"{pessoa}? não sou fã, não. prefiro manter a convivência no mínimo necessário.",
            f"não vou fingir simpatia por {pessoa}. trato com educação e cada um segue o seu caminho.",
            f"com {pessoa}, minha boa vontade é curta. não vejo motivo pra forçar proximidade.",
            f"{pessoa} não é alguém que me agrade. sem drama, só não faço questão de intimidade.",
            f"não tenho muita paciência pra lidar com {pessoa}; prefiro deixar a convivência no básico.",
        ],
        "baixa": [
            f"{pessoa}? não é alguém que me ganhe facilmente. fico na cordialidade e pronto.",
            f"ah, {pessoa}. não vou fingir entusiasmo, né? trato normal, sem forçar amizade.",
            f"com {pessoa} eu não forço sintonia. cada um no seu quadrado e tá tudo certo.",
            f"não é minha companhia favorita, digamos assim. não precisa virar um drama.",
            f"{pessoa} não me desperta muita simpatia. sigo educada, mas sem aquela empolgação toda.",
            f"não temos muita química, {pessoa} e eu. convivência civilizada já resolve.",
            f"olha, não faço questão de proximidade com {pessoa}. sem briga, só não é meu tipo de companhia.",
        ],
        "reservada": [
            f"com {pessoa}, vou com calma. ainda não tenho intimidade pra falar como se fosse próximo.",
            f"ainda estou observando {pessoa}. prefiro não inventar uma opinião maior do que os fatos permitem.",
            f"{pessoa}? trato numa boa, mas não sou de forçar intimidade com quem ainda conheço pouco.",
            f"não tenho uma leitura fechada de {pessoa} ainda. por enquanto, conversa normal e sem presumir demais.",
        ],
        "neutra": [
            f"sobre {pessoa}, não tenho nada muito marcante pra dizer. prefiro avaliar pelo que faz.",
            f"{pessoa}? por enquanto, nada que me faça pender muito pra um lado ou pro outro.",
            f"não vou inventar uma história sobre {pessoa}. até aqui, minha impressão é comum, sem grandes extremos.",
        ],
        "boa": [
            f"gosto de trocar ideia com {pessoa}; só não espere um fã-clube, né.",
            f"{pessoa} costuma me passar uma impressão boa. ainda posso discordar quando precisar.",
            f"a convivência com {pessoa} funciona bem. isso não significa que eu vá passar pano.",
        ],
        "alta": [
            f"tenho consideração real por {pessoa}. posso zoar, mas não é pouca coisa.",
            f"{pessoa} é alguém que levo a sério e em quem confio. isso não me impede de ser sincera.",
            f"gosto de ter {pessoa} por perto. não preciso ficar anunciando isso toda hora.",
        ],
    }[faixa]
    anteriores = anteriores or []
    for variante in variantes:
        if not resposta_repetida(variante, anteriores):
            return variante
    # Se todas as opções foram usadas, começa a seleção em outra posição em vez de
    # reciclar sempre a primeira formulação.
    inicio = len(anteriores) % len(variantes)
    return variantes[inicio]

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
            "ANTIPATIA CLARA: deixe a pouca consideração aparecer na atitude, na concisão e na escolha das palavras. "
            "Não invente carinho, saudade, admiração ou boa vontade sem fatos que sustentem isso."
        ),
        "baixa": (
            "AFINIDADE BAIXA: a faixa 2,5–3,9 representa pouca simpatia, não neutralidade. "
            "Seja menos calorosa, mais seca, cética e pouco disponível para intimidade. "
            "Não transforme uma crítica em elogio compensatório nem invente simpatia. A nota deve aparecer no jeito de agir, não em um discurso sobre a relação."
        ),
        "reservada": (
            "AFINIDADE RESERVADA: aja com cautela e sem intimidade presumida. Não explique a categoria relacional sem necessidade."
        ),
        "neutra": (
            "AFINIDADE NEUTRA: mantenha equilíbrio sem fabricar simpatia ou antipatia. Não anuncie que está neutra; responda normalmente."
        ),
        "boa": (
            "AFINIDADE BOA: demonstre mais abertura e familiaridade de modo espontâneo, sem bajular nem anunciar proximidade."
        ),
        "alta": (
            "AFINIDADE ALTA: carinho, confiança e consideração podem aparecer naturalmente nas atitudes e escolhas de palavras; não precisa verbalizar isso toda hora."
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
        "REGRAS DE AVALIAÇÃO: afinidade determina consideração, confiança, simpatia, abertura e proximidade; "
        "paciência determina apenas tolerância momentânea. Não use a nota de quem fez a pergunta para avaliar o alvo. "
        "Se não houver eventos, não invente ofensas, defeitos ou comportamentos; expresse apenas uma impressão subjetiva "
        "proporcional ao vínculo. PRINCÍPIO DE NATURALIDADE: aja conforme a faixa, não narre a faixa. Não diga repetidamente "
        "que a relação é distante, fria, neutra ou reservada. Não mencione pontuação nem explique seu próprio estado "
        "relacional, salvo quando a pessoa perguntar diretamente ou isso for realmente necessário para responder. "
        "Varie ritmo, vocabulário e nível de humor; evite fórmulas fixas, aberturas e encerramentos repetidos. "
        "Em afinidade baixa, não invente simpatia, carinho ou saudade nem use elogio compensatório para amenizar a resposta. "
        "O humor pode mudar a forma, mas nunca inverter o julgamento. Não revele notas nem eventos privados. "
        "Não humilhe, ameace ou ataque atributos pessoais sensíveis. Em sofrimento ou pedido de ajuda, acolha e "
        "suspenda o sarcasmo, sem alterar a nota armazenada."
    )
