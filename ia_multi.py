"""Roteador multi-provedor: DeepSeek principal, Gemini reserva.

O histórico usa MensagemAgente neutra, permitindo trocar de fornecedor no meio de
uma conversa com ferramentas sem alterar a personalidade ou as permissões.
"""
from __future__ import annotations

import logging
import os

from deepseek_resilience import DeepSeekUnavailableError, deepseek_status
from gemini_resilience import GeminiUnavailableError, gemini_status
from ia_deepseek import DeepSeekAdaptador
from ia_gemini import GeminiAdaptador
from ia_nucleo import Adaptador, MensagemAgente, Registro, RespostaFerramenta

log = logging.getLogger("soulsbot.ia.router")


class TodosProvedoresIndisponiveis(RuntimeError):
    def __init__(self, erros: list[tuple[str, BaseException]]):
        self.erros = erros
        self.user_message = (
            "Os provedores de IA estão temporariamente indisponíveis. A Nara continua funcionando "
            "com respostas locais e consultas ao servidor; tente a pesquisa novamente mais tarde."
        )
        self.admin_message = " | ".join(
            f"{provider}: {getattr(error, 'admin_message', str(error))}" for provider, error in erros
        )[:1600]
        super().__init__(self.user_message)


class RoteadorIA(Adaptador):
    def __init__(self, *, deepseek_key: str = "", deepseek_model: str = "deepseek-flash",
                 gemini_key: str = "", gemini_model: str = "gemini-3.8-flash"):
        self.provedor_principal = os.getenv("AI_PRIMARY_PROVIDER", "deepseek").strip().lower() or "deepseek"
        if self.provedor_principal not in {"deepseek", "gemini"}:
            log.warning("AI_PRIMARY_PROVIDER=%r inválido; usando deepseek.", self.provedor_principal)
            self.provedor_principal = "deepseek"
        self.deepseek = None
        self.gemini = None
        self.init_errors: list[str] = []
        if deepseek_key:
            try:
                self.deepseek = DeepSeekAdaptador(deepseek_key, deepseek_model)
            except Exception as exc:
                self.init_errors.append(f"DeepSeek: {type(exc).__name__}: {exc}")
                log.exception("Não foi possível inicializar DeepSeek; a reserva ainda será tentada.")
        if gemini_key:
            try:
                self.gemini = GeminiAdaptador(gemini_key, gemini_model)
            except Exception as exc:
                self.init_errors.append(f"Gemini: {type(exc).__name__}: {exc}")
                log.exception("Não foi possível inicializar Gemini; o provedor principal ainda será tentado.")
        if self.deepseek is None and self.gemini is None:
            detail = "; ".join(self.init_errors) or "nenhuma chave foi configurada"
            raise RuntimeError(f"Nenhum adaptador de IA pôde ser inicializado: {detail}")

    def close(self):
        for adapter in (self.deepseek, self.gemini):
            if adapter:
                try:
                    adapter.close()
                except Exception:
                    log.exception("Falha ao fechar adaptador %s", type(adapter).__name__)

    def conteudo_usuario(self, texto: str) -> MensagemAgente:
        return MensagemAgente(role="user", texto=str(texto))

    def conteudo_funcoes(self, respostas: list) -> MensagemAgente:
        return MensagemAgente(role="tool_results", respostas_ferramentas=list(respostas))

    def parte_resposta(self, nome: str, resultado: dict, call_id: str | None = None) -> RespostaFerramenta:
        return RespostaFerramenta(id_chamada=str(call_id or f"tool_{nome}"), nome=nome, resultado=resultado)

    def normalizar_resposta(self, resposta):
        if not isinstance(resposta, MensagemAgente):
            raise TypeError("O roteador recebeu uma resposta fora do formato neutro.")
        return resposta

    def criar_gerador(self, system: str, registro: Registro):
        deepseek_generate = self.deepseek.criar_gerador(system, registro) if self.deepseek else None
        gemini_generate = self.gemini.criar_gerador(system, registro) if self.gemini else None
        principal = self.provedor_principal
        falharam_neste_turno: set[str] = set()

        async def gerar(contents: list, usar_ferramentas: bool):
            ordem = (["deepseek", "gemini"] if principal == "deepseek" else ["gemini", "deepseek"])
            erros: list[tuple[str, BaseException]] = []
            for nome in ordem:
                gerador = deepseek_generate if nome == "deepseek" else gemini_generate
                if gerador is None or nome in falharam_neste_turno:
                    continue
                try:
                    resposta = await gerador(contents, usar_ferramentas)
                    if erros:
                        log.warning("Failover de IA: resposta concluída pelo provedor %s após falha em %s",
                                    nome, ", ".join(p for p, _ in erros))
                    return resposta
                except (DeepSeekUnavailableError, GeminiUnavailableError, TimeoutError) as exc:
                    erros.append((nome, exc))
                    falharam_neste_turno.add(nome)
                    log.warning("Provedor %s indisponível; tentando o próximo. Motivo: %s", nome, str(exc)[:300])
            if erros:
                raise TodosProvedoresIndisponiveis(erros)
            raise RuntimeError("Nenhum provedor de IA foi configurado ou restou disponível neste turno. Configure DEEPSEEK_API_KEY e/ou GEMINI_API_KEY.")

        return gerar

    @staticmethod
    def status() -> dict:
        return {"deepseek": deepseek_status(), "gemini": gemini_status()}
