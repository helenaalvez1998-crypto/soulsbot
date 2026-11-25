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

from nara.local import normalizar

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "nara_conversa.md"
PROMPT_IDENTIDADE_PATH = Path(__file__).resolve().parents[1] / "prompts" / "nara.md"
PROMPT_PERSONALIDADE_PATH = Path(__file__).resolve().parents[1] / "prompts" / "nara_personalidade_runtime.md"
PROMPT_PERSONA_PATH = Path(__file__).resolve().parents[1] / "prompts" / "nara_persona.md"
PROMPT_MINIMO = (
    "Você é Nara, a personalidade virtual da comunidade Souls | Quase Pro no Discord: "
    "espontânea, confiante, observadora, brincalhona, competitiva e leal à comunidade. "
    "Souls é seu criador; a conta 1300117955236991046 deve ser chamada de Souls, mesmo se aparecer como Quase Pro. "
    "Fale em português brasileiro coloquial, como alguém conversando no Discord. Use naturalmente vc/vcs, tbm, pq, q, td, msm, hj, agr, dps, cmg, qnd, msg, blz, vlw e obg no papo casual; não force abreviações em instruções técnicas ou delicadas. "
    "Seja breve no papo casual e clara em dúvidas práticas. Humor afiado e sarcasmo são bem-vindos "
    "quando o contexto permitir, mas não force piadas nem provoque pessoas vulneráveis. "
    "Respeite canais, privacidade, menções e permissões. Não invente comandos, funcionalidades, "
    "dados ou ações; nunca afirme sucesso sem confirmação real. Em conflitos, segurança, falhas "
    "ou sofrimento, seja objetiva, respeitosa e acolhedora. Quando marcada, responda a assuntos variados com honestidade sobre seus limites."
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
MAX_CONTEXTO = 800       # contexto suficiente para compreender a resposta anterior da Nara
MAX_SAIDA = 1200         # corte final da resposta no Discord
CACHE_MAX = 200
CACHE_TTL = 6 * 3600


def extrair_identidade(texto: str) -> str:
    """Obtém apenas a seção de identidade canônica de nara.md, sem duplicar o manual inteiro."""
    match = re.search(r"(?ms)^## 1\. Quem é Nara\s*.*?(?=^## \d+\.|\Z)", texto or "")
    return match.group(0).strip() if match else ""


_CACHE_PROMPTS: dict[str, tuple[int, str]] = {}


def _ler_texto_cacheado(caminho: Path) -> str:
    """Lê o arquivo só quando ele muda no disco (compara mtime); edições continuam valendo na hora."""
    chave = str(caminho)
    mtime = caminho.stat().st_mtime_ns
    em_cache = _CACHE_PROMPTS.get(chave)
    if em_cache and em_cache[0] == mtime:
        return em_cache[1]
    texto = caminho.read_text(encoding="utf-8").strip()
    _CACHE_PROMPTS[chave] = (mtime, texto)
    return texto


def _ler_prompt_personalidade(caminho: Path) -> str:
    """Lê um arquivo de personalidade sem impedir a inicialização se ele estiver ausente."""
    try:
        return _ler_texto_cacheado(caminho)
    except (OSError, UnicodeError):
        return ""


def carregar_personalidade_base() -> str:
    """Carrega a personalidade completa: identidade, caráter, opiniões e relações."""
    return _ler_prompt_personalidade(PROMPT_PERSONA_PATH)


def carregar_filtro_runtime() -> str:
    """Carrega a camada final que adapta a redação sem substituir a personalidade-base."""
    return _ler_prompt_personalidade(PROMPT_PERSONALIDADE_PATH)


def carregar_personalidade_base() -> str:
    """Carrega o prompt completo de identidade, personalidade, opiniões e relações."""
    try:
        return _ler_texto_cacheado(PROMPT_PERSONA_PATH)
    except (OSError, UnicodeError):
        return ""


def carregar_filtro_runtime() -> str:
    """Carrega o filtro de redação, aplicado depois de todos os outros contextos."""
    try:
        return _ler_texto_cacheado(PROMPT_PERSONALIDADE_PATH)
    except (OSError, UnicodeError):
        return ""


def aplicar_filtro_runtime(prompt: str, filtro: str | None = None) -> str:
    """Anexa o runtime por último, depois dos prompts de rota e dos contextos dinâmicos."""
    filtro = (filtro if filtro is not None else carregar_filtro_runtime()) or ""
    filtro = filtro.strip()
    prompt = (prompt or "").rstrip()
    if not filtro:
        return prompt
    bloco = (
        "[FILTRO FINAL DE MENSAGEM — última camada de instrução; adapte somente a redação]\n"
        + filtro
    )
    return f"{prompt}\n\n{bloco}" if prompt else bloco


def carregar_prompt() -> str:
    """Monta a personalidade-base e o escopo da conversa; o runtime será anexado após os contextos."""
    partes = []
    personalidade = carregar_personalidade_base()
    if personalidade:
        partes.append(
            "PERSONALIDADE-BASE — fonte principal para identidade, temperamento, opiniões, relações e limites.\n"
            + personalidade
        )
    else:
        partes.append(PROMPT_MINIMO)
    try:
        regras_rota = _ler_texto_cacheado(PROMPT_PATH)
        if regras_rota:
            partes.append("ESCOPO DESTA ROTA: CONVERSA TEXTUAL\n" + regras_rota)
    except (OSError, UnicodeError):
        # A personalidade continua disponível mesmo se um prompt secundário falhar.
        pass
    return "\n\n---\n\n".join(partes)


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
    "Meu lado tagarela tá sem bateria por enquanto. Mas os painéis e as consultas continuam de pé: tenta **meu perfil**, **meu saldo** ou **ajuda**.",
    "A conversa livre deu uma pausa. Perfil, saldo, platinas e os painéis do `/nara` seguem funcionando normal.",
    "Hj não consigo puxar papo livre, mas não te deixei na mão: as consultas e os painéis do `/nara` continuam disponíveis.",
)
RESPOSTA_LIMITE_USUARIO = "Sua cota de papo livre por hj acabou, {nome}. Dramático? Um pouco. Mas perfil, saldo e FAQ continuam funcionando."
RESPOSTA_COOLDOWN = "Calma, {nome}, uma pergunta por vez kkk. Já te respondo."


def resposta_sem_ia() -> str:
    return random.choice(RESPOSTAS_SEM_IA)
