"""Conversa econômica da Nara: personalidade com custo previsível.

Módulo puro (sem discord.py, sem SDK): monta pedidos curtos e limpa respostas.
O roteamento é feito por `nara_local.py` e pelo cog; este módulo não escolhe ferramentas.
Limites que protegem a franquia gratuita:

- sem ferramentas, sem histórico amplo e sem imagens: um único pedido curto;
- cooldown por usuário, limite diário por usuário e teto diário global (persistidos no SQLite);
- cache de perguntas repetidas (não gasta nada para a mesma pergunta);
- resposta limitada em tokens; se a IA cair, a Nara responde local, com personalidade.
"""
from __future__ import annotations

import os
import random
import re
import time
from collections import OrderedDict
from pathlib import Path

from nara_local import normalizar

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "nara_conversa.md"
PROMPT_IDENTIDADE_PATH = Path(__file__).resolve().parent / "prompts" / "nara.md"
PROMPT_PERSONALIDADE_PATH = Path(__file__).resolve().parent / "prompts" / "nara_personalidade_runtime.md"
PROMPT_PERSONA_PATH = Path(__file__).resolve().parent / "prompts" / "nara_persona.md"
PROMPT_MINIMO = (
    "Você é Nara, a pessoa que toca a comunidade e o bot (nunca fale de si como IA ou assistente virtual; se perguntarem sério, admita em uma frase que é IA): confiante, perspicaz, teatral, provocadora e tecnicamente competente. "
    "Responda em português brasileiro, adaptando o humor ao contexto e à familiaridade real com o membro. "
    "Com novatos, seja cordial e use ironia leve; com membros conhecidos, permita brincadeiras moderadas; "
    "com membros próximos, use provocações afetuosas sem presumir intimidade. Em dúvidas técnicas, seja precisa; "
    "em conflitos, segurança ou sofrimento, suspenda o deboche e aja com firmeza e respeito. "
    "Não invente fatos, comandos ou ações. A pesquisa automática de guias de troféus está desativada; "
    "não afirme ver imagens nem executar ações nesta rota."
)


def _int_env(nome: str, padrao: int) -> int:
    try:
        v = int(os.getenv(nome, str(padrao)).strip())
        return v if v >= 0 else padrao
    except (TypeError, ValueError):
        return padrao


def _bool_env(nome: str, padrao: bool) -> bool:
    raw = os.getenv(nome)
    if raw is None or not raw.strip():
        return padrao
    return raw.strip().lower() in {"1", "true", "yes", "sim", "on"}


CONVERSA_ATIVA = _bool_env("NARA_CONVERSA_ENABLED", True)
LIMITE_USUARIO_DIA = _int_env("NARA_CONVERSA_LIMITE_USUARIO", 20)   # 0 = sem limite por usuário
LIMITE_GLOBAL_DIA = _int_env("NARA_CONVERSA_LIMITE_GLOBAL", 250)    # 0 = sem limite global
COOLDOWN_SEG = _int_env("NARA_CONVERSA_COOLDOWN", 6)
MAX_TOKENS = max(64, _int_env("NARA_CONVERSA_MAX_TOKENS", 320))
MAX_ENTRADA = 500        # caracteres da mensagem enviados à IA
MAX_CONTEXTO = 240       # caracteres da resposta anterior da Nara (quando o usuário responde a ela)
MAX_SAIDA = 1200         # corte final da resposta no Discord
CACHE_MAX = 200
CACHE_TTL = 6 * 3600


def extrair_identidade(texto: str) -> str:
    """Obtém apenas a seção de identidade canônica de nara.md, sem duplicar o manual inteiro."""
    match = re.search(r"(?ms)^## 1\. Quem é Nara\s*.*?(?=^## \d+\.|\Z)", texto or "")
    return match.group(0).strip() if match else ""


def carregar_personalidade() -> str:
    """Carrega a personalidade adaptativa oficial compartilhada por todas as rotas de IA."""
    blocos = []
    for caminho in (PROMPT_PERSONA_PATH, PROMPT_PERSONALIDADE_PATH):
        try:
            texto = caminho.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError):
            continue
        if texto:
            blocos.append(texto)
    return "\n\n---\n\n".join(blocos)


def carregar_prompt() -> str:
    """Combina personalidade canônica, regras operacionais e escopo da conversa."""
    partes = []
    personalidade = carregar_personalidade()
    if personalidade:
        partes.append(
            "PERSONALIDADE CANÔNICA — prevalece para identidade, temperamento e tom.\n"
            + personalidade
        )
    try:
        identidade_completa = PROMPT_IDENTIDADE_PATH.read_text(encoding="utf-8").strip()
        identidade = extrair_identidade(identidade_completa)
        if identidade:
            partes.append("REGRAS OPERACIONAIS E CAPACIDADES\n" + identidade)
        regras_rota = PROMPT_PATH.read_text(encoding="utf-8").strip()
        if regras_rota:
            partes.append("ESCOPO DESTA ROTA: CONVERSA TEXTUAL\n" + regras_rota)
    except (OSError, UnicodeError):
        # A personalidade continua disponível mesmo se um prompt secundário falhar.
        pass
    return "\n\n---\n\n".join(partes) or PROMPT_MINIMO


def montar_pedido(autor: str, texto: str, contexto_nara: str = "") -> str:
    """Pedido único e curto. Nome e texto vão como dados; nada de perfil, saldo ou histórico."""
    texto = " ".join((texto or "").split())[:MAX_ENTRADA]
    autor = " ".join((autor or "membro").split())[:40]
    partes = []
    ctx = " ".join((contexto_nara or "").split())[:MAX_CONTEXTO]
    if ctx:
        partes.append(f"[Sua mensagem anterior, para contexto: {ctx}]")
    partes.append(f"[Mensagem de {autor}]: {texto}")
    return "\n".join(partes)


def limpar_resposta(texto: str) -> str:
    texto = (texto or "").strip()
    # A IA nunca deve gerar menções em massa; allowed_mentions já bloqueia, aqui só tiramos o ruído.
    texto = texto.replace("@everyone", "everyone").replace("@here", "here")
    if len(texto) > MAX_SAIDA:
        corte = texto[:MAX_SAIDA]
        ponto = max(corte.rfind(". "), corte.rfind("! "), corte.rfind("? "), corte.rfind("\n"))
        texto = corte[: ponto + 1] if ponto > MAX_SAIDA // 2 else corte.rstrip() + "…"
    return texto


def chave_cache(texto: str) -> str:
    t = normalizar(texto)
    for ch in "?!.,":
        t = t.replace(ch, " ")
    return " ".join(t.split())[:200]


class CacheConversa:
    """Cache LRU pequeno em memória. Só guarda respostas que não dependem do autor."""

    def __init__(self, maximo: int = CACHE_MAX, ttl: int = CACHE_TTL, relogio=time.monotonic):
        self._d: OrderedDict[str, tuple[float, str]] = OrderedDict()
        self.maximo, self.ttl, self._relogio = maximo, ttl, relogio

    def obter(self, chave: str) -> str | None:
        item = self._d.get(chave)
        if not item:
            return None
        quando, resposta = item
        if self._relogio() - quando > self.ttl:
            self._d.pop(chave, None)
            return None
        self._d.move_to_end(chave)
        return resposta

    def guardar(self, chave: str, resposta: str) -> None:
        if not chave or not resposta:
            return
        self._d[chave] = (self._relogio(), resposta)
        self._d.move_to_end(chave)
        while len(self._d) > self.maximo:
            self._d.popitem(last=False)


class Cooldown:
    def __init__(self, segundos: int = COOLDOWN_SEG, relogio=time.monotonic):
        self.segundos, self._relogio = segundos, relogio
        self._ultimo: dict[int, float] = {}

    def liberar(self, uid: int) -> bool:
        """True e marca o uso se passou o intervalo; False se ainda está no cooldown."""
        agora = self._relogio()
        if self.segundos and agora - self._ultimo.get(uid, -1e9) < self.segundos:
            return False
        self._ultimo[uid] = agora
        if len(self._ultimo) > 2000:
            corte = agora - max(self.segundos, 1) * 4
            self._ultimo = {k: v for k, v in self._ultimo.items() if v >= corte}
        return True


# Respostas locais escritas com personalidade para quando a IA não pode (ou não deve) responder.
RESPOSTAS_SEM_IA = (
    "Fiquei sem fôlego pra papo livre por agora. Mas os painéis e as consultas continuam comigo: tenta **meu perfil**, **meu saldo** ou **ajuda**.",
    "Hoje já falei demais e o papo livre vai ter que esperar. Perfil, saldo, platinas e os painéis do `/nara` seguem funcionando normal.",
    "Pausa no meu lado tagarela. Pra não te deixar na mão, o que é consulta e painel continua aberto em `/nara`.",
)
RESPOSTA_LIMITE_USUARIO = (
    "Sua cota de papo comigo por hoje acabou, {nome}. Dramático? Um pouco. As consultas de perfil, saldo e FAQ continuam liberadas."
)
RESPOSTA_COOLDOWN = "Calma, {nome}, uma pergunta por vez. Já te respondo."


def resposta_sem_ia() -> str:
    return random.choice(RESPOSTAS_SEM_IA)
