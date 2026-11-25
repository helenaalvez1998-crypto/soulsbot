"""Núcleo do agente da Nara: a IA decide, o código garante.

Este módulo não depende do discord.py nem do SDK do Gemini, para poder ser testado isoladamente.

Princípios:
- A IA só escolhe QUAL ferramenta chamar e com QUAIS argumentos. Permissão, validação, limite e
  confirmação são verificados aqui, em código. O prompt nunca é a única barreira.
- Quem age é sempre o autor da mensagem (ctx.autor). Nenhuma ferramenta recebe "user_id do ator".
- Ferramentas têm um nível de risco (Risco). Ações que gastam algo do membro ou são difíceis de
  desfazer não rodam na hora: viram uma Pendente, confirmada por botão pelo próprio autor.
- Resultados de ferramentas voltam para a IA como DADOS, nunca como instruções.
"""
from __future__ import annotations

import asyncio
import enum
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

log = logging.getLogger("nara.ia.nucleo")

MAX_PASSOS = 6                 # voltas de "pensar → usar ferramenta" por mensagem
TIMEOUT_FERRAMENTA = 20        # segundos
MAX_RESULTADO_CHARS = 6000     # corte do que volta para a IA


class Risco(enum.Enum):
    LEITURA = "leitura"          # só consulta; roda direto
    PROPRIA = "propria"          # muda algo do próprio autor, grátis e reversível; roda direto
    CONFIRMAR = "confirmar"      # gasta recurso / sobrescreve dado do autor; exige botão do autor
    MODERACAO = "moderacao"      # só moderador; sempre exige botão do próprio moderador


class ErroFerramenta(Exception):
    """Erro esperado, com texto seguro para a IA (e o membro) lerem."""


@dataclass(frozen=True)
class Param:
    nome: str
    tipo: str                      # "string" | "integer" | "boolean"
    descricao: str
    obrigatorio: bool = True
    opcoes: tuple[str, ...] | None = None
    max_len: int = 200
    minimo: int | None = None
    maximo: int | None = None


@dataclass(frozen=True)
class Ferramenta:
    nome: str
    descricao: str
    risco: Risco
    params: tuple[Param, ...]
    executar: Callable[["Ctx", dict], Awaitable[Any]]
    # Só para CONFIRMAR/MODERACAO: valida pré-condições e devolve o texto que o membro verá no botão.
    preparar: Callable[["Ctx", dict], Awaitable[str]] | None = None


@dataclass
class Pendente:
    """Ação preparada pela IA que só acontece se o autor clicar em Confirmar."""
    ferramenta: str
    resumo: str
    args: dict
    autor_id: int
    exige_mod: bool
    executar: Callable[[], Awaitable[str]]


@dataclass
class Ctx:
    bot: Any
    guild: Any
    autor: Any
    canal: Any = None
    eh_mod: bool = False
    modo: str = "marcado"                      # "marcado" | "livre"
    mencionados: dict[int, Any] = field(default_factory=dict)
    pendentes: list[Pendente] = field(default_factory=list)
    atalhos: list[str] = field(default_factory=list)      # painéis que a IA quer oferecer como botão
    auditoria: Callable[[str, str], Awaitable[None]] | None = None
    _cache: dict[str, dict] = field(default_factory=dict)

    def resolver_membro(self, membro_id: int | None):
        """Sem id = o próprio autor. Com id = membro do servidor (ou ErroFerramenta)."""
        if membro_id in (None, 0, self.autor.id):
            return self.autor
        membro = self.mencionados.get(membro_id) or (self.guild.get_member(membro_id) if self.guild else None)
        if membro is None:
            raise ErroFerramenta("Membro não encontrado neste servidor. Use buscar_membro para achar o id.")
        return membro

    async def auditar(self, acao: str, detalhes: str):
        if self.auditoria:
            try:
                await self.auditoria(acao, detalhes)
            except Exception:  # auditoria nunca pode derrubar a ação
                log.exception("Falha ao gravar auditoria da IA")


# --------------------------------------------------------------------------- validação
def _coagir(p: Param, valor: Any) -> Any:
    if p.tipo == "integer":
        if isinstance(valor, bool):
            raise ErroFerramenta(f"'{p.nome}' deve ser um número inteiro.")
        if isinstance(valor, float) and valor.is_integer():
            valor = int(valor)
        elif isinstance(valor, str) and valor.strip().lstrip("-").isdigit():
            valor = int(valor.strip())
        if not isinstance(valor, int):
            raise ErroFerramenta(f"'{p.nome}' deve ser um número inteiro.")
        if p.minimo is not None and valor < p.minimo:
            raise ErroFerramenta(f"'{p.nome}' deve ser no mínimo {p.minimo}.")
        if p.maximo is not None and valor > p.maximo:
            raise ErroFerramenta(f"'{p.nome}' deve ser no máximo {p.maximo}.")
        return valor
    if p.tipo == "boolean":
        if isinstance(valor, bool):
            return valor
        raise ErroFerramenta(f"'{p.nome}' deve ser verdadeiro ou falso.")
    if not isinstance(valor, str):
        valor = str(valor)
    valor = valor.strip()
    if len(valor) > p.max_len:
        raise ErroFerramenta(f"'{p.nome}' passa de {p.max_len} caracteres.")
    if p.opcoes is not None and valor not in p.opcoes:
        raise ErroFerramenta(f"'{p.nome}' deve ser um destes: {', '.join(p.opcoes)}.")
    return valor


def validar_args(ferramenta: Ferramenta, bruto: dict) -> dict:
    """Aceita só parâmetros declarados; descarta o resto (a IA não inventa parâmetros)."""
    limpo: dict = {}
    for p in ferramenta.params:
        if p.nome not in bruto or bruto[p.nome] in (None, ""):
            if p.obrigatorio:
                raise ErroFerramenta(f"Falta o parâmetro obrigatório '{p.nome}'.")
            continue
        limpo[p.nome] = _coagir(p, bruto[p.nome])
    return limpo


def _normalizar(resultado: Any) -> dict:
    if isinstance(resultado, dict):
        saida = resultado
    elif isinstance(resultado, list):
        saida = {"itens": resultado}
    else:
        saida = {"resultado": str(resultado)}
    texto = json.dumps(saida, ensure_ascii=False, default=str)
    if len(texto) > MAX_RESULTADO_CHARS:
        return {"aviso": "Resultado cortado por tamanho.", "parcial": texto[:MAX_RESULTADO_CHARS]}
    return saida


# --------------------------------------------------------------------------- registro
class Registro:
    def __init__(self, ferramentas: list[Ferramenta]):
        self.ferramentas: dict[str, Ferramenta] = {f.nome: f for f in ferramentas}

    def __len__(self):
        return len(self.ferramentas)

    async def executar(self, nome: str, bruto: dict, ctx: Ctx) -> dict:
        f = self.ferramentas.get(nome)
        if f is None:
            return {"erro": f"A ferramenta '{nome}' não existe."}

        # Só ações (não consultas) ficam em cache: se a IA repetir a MESMA ação na mesma resposta, ela não roda duas
        # vezes. Consultas sempre releem o estado atual (ex.: listar a loja depois de equipar um item).
        chave = nome + json.dumps(bruto, sort_keys=True, default=str)
        if f.risco is not Risco.LEITURA and chave in ctx._cache:
            return ctx._cache[chave]

        try:
            args = validar_args(f, dict(bruto or {}))
            if f.risco is Risco.MODERACAO and not ctx.eh_mod:
                await ctx.auditar("ia_negado", f"{nome} sem permissão de moderação")
                return {"erro": "Sem permissão: esta ação é só da moderação."}

            if f.risco in (Risco.CONFIRMAR, Risco.MODERACAO):
                saida = await self._preparar(f, args, ctx)
            else:
                saida = _normalizar(await asyncio.wait_for(f.executar(ctx, args), TIMEOUT_FERRAMENTA))
                if f.risco is Risco.PROPRIA:
                    await ctx.auditar("ia_acao", f"{nome} {json.dumps(args, ensure_ascii=False)}")
        except ErroFerramenta as e:
            saida = {"erro": str(e)}
        except asyncio.TimeoutError:
            saida = {"erro": "A ferramenta demorou demais. Tente de novo."}
        except Exception:
            log.exception("Falha inesperada na ferramenta %s", nome)
            saida = {"erro": "Falha interna ao executar a ferramenta."}

        if f.risco is not Risco.LEITURA and "erro" not in saida:
            ctx._cache[chave] = saida
        return saida

    async def _preparar(self, f: Ferramenta, args: dict, ctx: Ctx) -> dict:
        if ctx.pendentes:
            raise ErroFerramenta(
                "Já existe uma ação aguardando confirmação nesta resposta. "
                "Peça ao membro para confirmar e prepare a próxima depois."
            )
        resumo = await f.preparar(ctx, args) if f.preparar else f.descricao

        async def rodar() -> str:
            resultado = _normalizar(await asyncio.wait_for(f.executar(ctx, args), TIMEOUT_FERRAMENTA))
            await ctx.auditar("ia_acao", f"{f.nome} {json.dumps(args, ensure_ascii=False)} (confirmada)")
            return str(resultado.get("resultado") or resultado.get("mensagem") or "Feito.")

        ctx.pendentes.append(Pendente(
            ferramenta=f.nome, resumo=resumo, args=args, autor_id=ctx.autor.id,
            exige_mod=f.risco is Risco.MODERACAO, executar=rodar,
        ))
        return {
            "status": "aguardando_confirmacao",
            "resumo": resumo,
            "instrucao": ("NADA foi feito ainda. Diga ao membro, em uma frase, o que vai acontecer e que "
                          "ele precisa tocar em Confirmar nos botões abaixo da sua resposta."),
        }


# --------------------------------------------------------------------------- laço do agente
@dataclass
class ChamadaAgente:
    id: str
    nome: str
    argumentos: dict


@dataclass
class RespostaFerramenta:
    id_chamada: str
    nome: str
    resultado: dict


@dataclass
class MensagemAgente:
    """Histórico neutro entre provedores; nunca contém anexos nem dados multimodais."""
    role: str
    texto: str = ""
    chamadas: list[ChamadaAgente] = field(default_factory=list)
    respostas_ferramentas: list[RespostaFerramenta] = field(default_factory=list)
    nativo: Any = None


class Adaptador:
    """Contrato neutro para adaptadores Gemini e para o roteador de failover entre projetos."""
    def conteudo_usuario(self, texto: str): ...
    def conteudo_funcoes(self, respostas: list): ...
    def parte_resposta(self, nome: str, resultado: dict, call_id: str | None = None): ...


def _texto(parts) -> str:
    return "".join(p.text for p in parts if getattr(p, "text", None) and not getattr(p, "thought", False)).strip()


async def rodar_agente(gerar: Callable[[list, bool], Awaitable[Any]], adaptador: Adaptador, pedido: str,
                       registro: Registro, ctx: Ctx, *, max_passos: int = MAX_PASSOS) -> str:
    """Conversa com o modelo até obter texto final; histórico neutro permite failover entre APIs."""
    contents = [adaptador.conteudo_usuario(pedido)]
    for _ in range(max_passos):
        resp = await gerar(contents, True)
        normalizar = getattr(adaptador, "normalizar_resposta", None)
        if callable(normalizar):
            mensagem = normalizar(resp)
            chamadas = list(getattr(mensagem, "chamadas", None) or [])
            if not chamadas:
                return str(getattr(mensagem, "texto", "") or "").strip()
            contents.append(mensagem)
            respostas = []
            for fc in chamadas:
                resultado = await registro.executar(fc.nome, dict(fc.argumentos or {}), ctx)
                respostas.append(adaptador.parte_resposta(fc.nome, resultado, call_id=fc.id))
            contents.append(adaptador.conteudo_funcoes(respostas))
            continue

        # Compatibilidade com adaptadores antigos usados por integrações/testes legados.
        candidatos = getattr(resp, "candidates", None) or []
        conteudo = getattr(candidatos[0], "content", None) if candidatos else None
        parts = list(getattr(conteudo, "parts", None) or [])
        chamadas_antigas = [p.function_call for p in parts if getattr(p, "function_call", None)]
        if not chamadas_antigas:
            return _texto(parts)
        contents.append(conteudo)
        respostas = []
        for fc in chamadas_antigas:
            resultado = await registro.executar(fc.name, dict(fc.args or {}), ctx)
            try:
                respostas.append(adaptador.parte_resposta(fc.name, resultado, call_id=getattr(fc, "id", None)))
            except TypeError:
                respostas.append(adaptador.parte_resposta(fc.name, resultado))
        contents.append(adaptador.conteudo_funcoes(respostas))

    resp = await gerar(contents, False)
    normalizar = getattr(adaptador, "normalizar_resposta", None)
    if callable(normalizar):
        return str(getattr(normalizar(resp), "texto", "") or "").strip()
    candidatos = getattr(resp, "candidates", None) or []
    conteudo = getattr(candidatos[0], "content", None) if candidatos else None
    return _texto(list(getattr(conteudo, "parts", None) or []))
