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
PROMPT_MINIMO = (
    "Você é Nara, IA do servidor NARA: inteligente, espontânea, levemente debochada, sem ser hostil. "
    "Responda em português brasileiro, em 1 a 4 frases, sem inventar fatos. Para troféus/platinas de jogos "
    "a pesquisa automática de guias de jogos está temporariamente desativada. Você não vê imagens nem executa ações nesta conversa."
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


def carregar_prompt() -> str:
    """Carrega a identidade canônica e, em seguida, o escopo já existente desta rota.

    Os arquivos são preservados e não há uma segunda personalidade gerada no código.
    """
    try:
        identidade_completa = PROMPT_IDENTIDADE_PATH.read_text(encoding="utf-8").strip()
        identidade = extrair_identidade(identidade_completa)
        regras_rota = PROMPT_PATH.read_text(encoding="utf-8").strip()
        if identidade and regras_rota:
            return identidade + "\n\n--- ESCOPO DESTA ROTA: CONVERSA TEXTUAL ---\n" + regras_rota
        return identidade or regras_rota or PROMPT_MINIMO
    except (OSError, UnicodeError):
        # Preserva o comportamento de contingência já existente se algum arquivo falhar.
        try:
            texto = PROMPT_PATH.read_text(encoding="utf-8").strip()
            return texto or PROMPT_MINIMO
        except (OSError, UnicodeError):
            return PROMPT_MINIMO


def montar_pedido(autor: str, texto: str, contexto_nara: str = "") -> str:
    """Pedido único e curto. Nome e texto vão como dados; nada de perfil, saldo ou histórico."""
    texto = " ".join((texto or "").split())[:MAX_ENTRADA]
    autor = " ".join((autor or "membro").split())[:40]
    partes = []
    ctx = " ".join((contexto_nara or "").split())[:MAX_CONTEXTO]
    if ctx:
        partes.append(f"[Sua mensagem anterior, para contexto: {ctx}]")
    partes.append(f"[{autor} diz]: {texto}")
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


# Falas locais com personalidade para quando a IA não pode (ou não deve) responder.
FALAS_SEM_IA = (
    "Hoje eu já falei demais pelas contas do servidor e preciso poupar fôlego. Me pergunta de novo mais tarde, "
    "ou pergunta **meu perfil**, **meu saldo** ou **ajuda**, que isso eu resolvo na hora.",
    "Meu lado tagarela tirou uma folga forçada (limite da IA). O resto funciona: **ajuda**, **meu perfil**, "
    "**minhas platinas**, **como ganhar XP**. Tenta de novo daqui a pouco.",
    "Tô sem fôlego pra papo livre agora, não por falta de vontade. Volta já já — enquanto isso, "
    "**ajuda** mostra o que eu faço sem esforço.",
)
FALA_LIMITE_USUARIO = (
    "Você já gastou sua cota de papo comigo hoje, {nome}. Amanhã tem mais. "
    "As consultas de perfil, saldo e FAQ continuam liberadas."
)
FALA_COOLDOWN = "Calma, {nome}, uma pergunta por vez. Respiro e já respondo."


def fala_sem_ia() -> str:
    return random.choice(FALAS_SEM_IA)
