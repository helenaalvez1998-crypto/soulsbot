"""Roteador de até três projetos Gemini, sem dependência de outro fornecedor.

Mantém o histórico em MensagemAgente neutra, permitindo alternar do Gemini
principal para o reserva no meio de tool calls sem repetir ferramentas.
"""
from __future__ import annotations

import logging

from gemini_resilience import GeminiUnavailableError, gemini_status
from ia_gemini import GeminiAdaptador
from ia_nucleo import Adaptador, MensagemAgente, Registro, RespostaFerramenta

log = logging.getLogger("nara.ia.router")


class TodosProvedoresIndisponiveis(RuntimeError):
    def __init__(self, erros: list[tuple[str, BaseException]]):
        self.erros = erros
        self.user_message = (
            "Os até três projetos Gemini estão temporariamente indisponíveis. "
            "A Nara continua funcionando com respostas locais e consultas ao servidor."
        )
        self.admin_message = " | ".join(
            f"{provider}: {getattr(error, 'admin_message', str(error))}" for provider, error in erros
        )[:1600]
        super().__init__(self.user_message)


class RoteadorIA(Adaptador):
    def __init__(self, *, gemini_key: str = "", gemini_model: str = "gemini-3.5-flash-lite",
                 gemini_backup_key: str = "", gemini_backup_model: str = "gemini-3.5-flash-lite",
                 gemini_third_key: str = "", gemini_third_model: str = "gemini-3.5-flash-lite"):
        self.gemini_primary = None
        self.gemini_backup = None
        self.gemini_third = None
        self.init_errors: list[str] = []
        if gemini_key:
            try:
                self.gemini_primary = GeminiAdaptador(gemini_key, gemini_model, provider="primary")
            except Exception as exc:
                self.init_errors.append(f"Gemini principal: {type(exc).__name__}: {exc}")
                log.exception("Falha ao inicializar o projeto Gemini principal.")
        if gemini_backup_key:
            try:
                self.gemini_backup = GeminiAdaptador(gemini_backup_key, gemini_backup_model, provider="backup")
            except Exception as exc:
                self.init_errors.append(f"Gemini reserva: {type(exc).__name__}: {exc}")
                log.exception("Falha ao inicializar o projeto Gemini reserva.")
        if gemini_third_key:
            try:
                self.gemini_third = GeminiAdaptador(gemini_third_key, gemini_third_model, provider="tertiary")
            except Exception as exc:
                self.init_errors.append(f"Gemini terceira chave: {type(exc).__name__}: {exc}")
                log.exception("Falha ao inicializar a terceira configuração Gemini.")
        if self.gemini_primary is None and self.gemini_backup is None and self.gemini_third is None:
            detail = "; ".join(self.init_errors) or "nenhuma chave Gemini foi configurada"
            raise RuntimeError(f"Nenhum projeto Gemini pôde ser inicializado: {detail}")

    def close(self):
        for adapter in (self.gemini_primary, self.gemini_backup, self.gemini_third):
            if adapter:
                try:
                    adapter.close()
                except Exception:
                    log.exception("Falha ao fechar adaptador Gemini.")

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
        primary_generate = self.gemini_primary.criar_gerador(system, registro) if self.gemini_primary else None
        backup_generate = self.gemini_backup.criar_gerador(system, registro) if self.gemini_backup else None
        third_generate = self.gemini_third.criar_gerador(system, registro) if self.gemini_third else None
        falharam_neste_turno: set[str] = set()

        async def gerar(contents: list, usar_ferramentas: bool):
            ordem = (("primary", primary_generate), ("backup", backup_generate), ("tertiary", third_generate))
            erros: list[tuple[str, BaseException]] = []
            for nome, gerador in ordem:
                if gerador is None or nome in falharam_neste_turno:
                    continue
                try:
                    resposta = await gerador(contents, usar_ferramentas)
                    if erros:
                        log.warning("Failover Gemini: resposta concluída pelo projeto %s após falha do principal.", nome)
                    return resposta
                except (GeminiUnavailableError, TimeoutError) as exc:
                    erros.append((f"Gemini {nome}", exc))
                    falharam_neste_turno.add(nome)
                    log.warning("Projeto Gemini %s indisponível; tentando reserva. Motivo: %s", nome, str(exc)[:300])
            if erros:
                raise TodosProvedoresIndisponiveis(erros)
            raise RuntimeError("Nenhum projeto Gemini foi configurado ou restou disponível neste turno.")

        return gerar

    async def conversar(self, system: str, texto: str, max_tokens: int = 320, imagens=None) -> str:
        """Conversa curta sem ferramentas: principal primeiro, demais em caso de quota/indisponibilidade."""
        erros: list[tuple[str, BaseException]] = []
        for nome, adaptador in (("primary", self.gemini_primary), ("backup", self.gemini_backup), ("tertiary", getattr(self, "gemini_third", None))):
            if adaptador is None:
                continue
            try:
                resposta = (await adaptador.conversar(system, texto, max_tokens, imagens=imagens)
                        if imagens else await adaptador.conversar(system, texto, max_tokens))
                if erros:
                    log.warning("Conversa da Nara concluída pelo projeto %s após falha do principal.", nome)
                return resposta
            except (GeminiUnavailableError, TimeoutError) as exc:
                erros.append((f"Gemini {nome}", exc))
                log.warning("Conversa: projeto Gemini %s indisponível: %s", nome, str(exc)[:300])
        if erros:
            raise TodosProvedoresIndisponiveis(erros)
        raise RuntimeError("Nenhum projeto Gemini configurado para a conversa.")

    @staticmethod
    def status() -> dict:
        return {"gemini_primary": gemini_status("primary"), "gemini_backup": gemini_status("backup"), "gemini_third": gemini_status("tertiary")}
