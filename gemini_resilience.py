"""Resiliência compartilhada para todas as chamadas do Gemini.

Classifica 429/503, aplica circuit breaker global do processo e persiste o bloqueio
em data/gemini_circuit.json para não voltar a martelar a API após um restart.
Não faz uma segunda política de retry: o SDK oficial já faz retries para falhas
transitórias. Aqui tratamos o erro final que escapou do SDK.
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TypeVar

log = logging.getLogger("soulsbot.gemini")
T = TypeVar("T")


class GeminiUnavailableError(RuntimeError):
    """Falha conhecida de quota, rate limit ou indisponibilidade do Gemini."""

    def __init__(self, kind: str, retry_after_seconds: int, technical_message: str):
        self.kind = kind
        self.retry_after_seconds = max(1, int(retry_after_seconds))
        self.technical_message = (technical_message or "Falha sem detalhes retornados pelo SDK")[:1200]
        if kind == "quota":
            user_message = (
                "A IA do Google atingiu a quota disponível. As funções que dependem do Gemini foram "
                "pausadas para evitar novas chamadas recusadas. A administração precisa verificar "
                "o uso, os limites e o faturamento do projeto Gemini."
            )
            admin_message = (
                "Quota Gemini esgotada ou limite de faturamento atingido. Verifique o projeto, "
                "os limites de geração e de Google Search grounding, os créditos e o billing. "
                f"O bot ficará em pausa por até {self.retry_after_seconds // 60 or 1} minuto(s) antes de uma nova tentativa."
            )
        elif kind == "rate_limit":
            minutes = max(1, (self.retry_after_seconds + 59) // 60)
            user_message = (
                "O Gemini está limitando temporariamente as solicitações. Aguarde aproximadamente "
                f"{minutes} minuto(s) e tente novamente."
            )
            admin_message = f"Rate limit Gemini (429). Circuit breaker ativo por {self.retry_after_seconds}s."
        else:
            user_message = "O serviço Gemini está temporariamente indisponível. Tente novamente mais tarde."
            admin_message = f"Gemini indisponível temporariamente. Circuit breaker ativo por {self.retry_after_seconds}s."
        self.user_message = user_message
        self.admin_message = admin_message
        super().__init__(user_message)

    def __str__(self) -> str:
        return self.user_message


_LOCK = threading.RLock()
_BLOCKED_UNTIL = 0.0  # timestamp Unix, não monotonic, para permitir persistência
_BLOCK_KIND = ""
_BLOCK_REASON = ""
_STATE_LOADED = False


def _int_env(name: str, default: int, minimum: int = 1, maximum: int = 86400) -> int:
    try:
        value = int(os.getenv(name, str(default)).strip())
        return min(maximum, max(minimum, value))
    except (TypeError, ValueError):
        log.warning("Configuração %s inválida; usando %s.", name, default)
        return default


def _state_path() -> Path:
    configured = os.getenv("GEMINI_CIRCUIT_STATE_FILE", "data/gemini_circuit.json").strip()
    return Path(configured or "data/gemini_circuit.json")


def _load_state_locked() -> None:
    global _STATE_LOADED, _BLOCKED_UNTIL, _BLOCK_KIND, _BLOCK_REASON
    if _STATE_LOADED:
        return
    _STATE_LOADED = True
    path = _state_path()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        blocked_until = float(payload.get("blocked_until", 0))
        if blocked_until > time.time():
            _BLOCKED_UNTIL = blocked_until
            _BLOCK_KIND = str(payload.get("kind", "unavailable"))[:40]
            _BLOCK_REASON = str(payload.get("reason", "Bloqueio persistido"))[:500]
            log.warning("Circuit breaker Gemini restaurado: tipo=%s, restante=%ss.",
                        _BLOCK_KIND, max(1, int(_BLOCKED_UNTIL - time.time())))
        elif path.exists():
            path.unlink(missing_ok=True)
    except FileNotFoundError:
        return
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        log.warning("Não foi possível ler o estado persistido do Gemini; usando estado em memória.", exc_info=True)


def _save_state_locked() -> None:
    path = _state_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "blocked_until": _BLOCKED_UNTIL,
            "blocked_until_utc": datetime.fromtimestamp(_BLOCKED_UNTIL, timezone.utc).isoformat(),
            "kind": _BLOCK_KIND,
            "reason": _BLOCK_REASON[:500],
        }
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)
    except OSError:
        # Alguns hosts usam filesystem somente leitura. O circuit breaker em memória continua ativo.
        log.warning("Não foi possível persistir o circuit breaker Gemini; o bloqueio ficará em memória.",
                    exc_info=True)


def _extract_text(exc: BaseException) -> str:
    parts = [str(exc)]
    for attr in ("message", "details", "body", "response"):
        value = getattr(exc, attr, None)
        if value is not None:
            try:
                parts.append(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str))
            except Exception:
                parts.append(str(value))
    return " ".join(parts)[:10000]


def _status_code(exc: BaseException, text: str) -> int | None:
    for attr in ("code", "status_code", "status"):
        value = getattr(exc, attr, None)
        try:
            if value is not None:
                code = int(value)
                if 100 <= code <= 599:
                    return code
        except (TypeError, ValueError):
            pass
    match = re.search(r"\b(?:HTTP(?:/\d(?:\.\d)?)?\s*)?(408|429|500|502|503|504)\b", text, re.I)
    return int(match.group(1)) if match else None


def _retry_after_seconds(exc: BaseException, text: str) -> int | None:
    # Alguns payloads do Google incluem retryDelay: "12s"; headers podem não
    # ficar expostos no erro do SDK, por isso também analisamos a mensagem.
    match = re.search(r"retryDelay\s*[\"']?\s*:\s*[\"'](\d+(?:\.\d+)?)s", text, re.I)
    if not match:
        match = re.search(r"retry\s+after\s+(\d+(?:\.\d+)?)\s+seconds?", text, re.I)
    if match:
        return min(3600, max(1, int(float(match.group(1)) + 0.999)))
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if headers:
        try:
            value = headers.get("Retry-After")
            if value:
                return min(3600, max(1, int(float(value) + 0.999)))
        except (TypeError, ValueError):
            pass
    return None


def classify_gemini_error(exc: BaseException) -> tuple[str, int] | None:
    """Retorna (tipo, segundos) apenas para erros recuperáveis/limitadores conhecidos."""
    text = _extract_text(exc)
    status = _status_code(exc, text)
    if status not in (408, 429, 500, 502, 503, 504) and "RESOURCE_EXHAUSTED" not in text.upper():
        return None

    lowered = text.casefold()
    if status == 429 or "resource_exhausted" in lowered:
        quota_signals = (
            "you exceeded your current quota", "check your plan and billing",
            "quota exceeded", "daily quota", "quota per day", "requests per day",
            "billing", "insufficient credits", "prepay", "spend cap",
            "per_day", "requestsperday", "quota_limit", "free_tier",
        )
        is_hard_quota = any(signal in lowered for signal in quota_signals)
        retry = _retry_after_seconds(exc, text)
        if is_hard_quota:
            return "quota", _int_env("GEMINI_QUOTA_COOLDOWN_SECONDS", 21600, 60, 604800)
        return "rate_limit", retry or _int_env("GEMINI_RATE_LIMIT_COOLDOWN_SECONDS", 60, 5, 3600)

    if status in (408, 500, 502, 503, 504):
        retry = _retry_after_seconds(exc, text)
        return "unavailable", retry or _int_env("GEMINI_UNAVAILABLE_COOLDOWN_SECONDS", 45, 5, 3600)
    return None


def _register_block(kind: str, seconds: int, reason: str) -> None:
    global _BLOCKED_UNTIL, _BLOCK_KIND, _BLOCK_REASON
    with _LOCK:
        _load_state_locked()
        proposed = time.time() + max(1, seconds)
        # Nunca encurta um bloqueio já vigente nem troca sua classificação por uma
        # falha simultânea que tenha prazo menor.
        if proposed >= _BLOCKED_UNTIL:
            _BLOCK_KIND = kind
            _BLOCK_REASON = reason[:500]
        _BLOCKED_UNTIL = max(_BLOCKED_UNTIL, proposed)
        _save_state_locked()
    log.error("Circuit breaker Gemini ativado: tipo=%s, duração=%ss, motivo=%s",
              kind, seconds, reason[:300])


def check_gemini_available() -> None:
    global _BLOCKED_UNTIL, _BLOCK_KIND, _BLOCK_REASON
    with _LOCK:
        _load_state_locked()
        remaining = int(_BLOCKED_UNTIL - time.time())
        if remaining > 0:
            kind = _BLOCK_KIND or "unavailable"
            reason = _BLOCK_REASON or "limite temporário"
        else:
            if _BLOCKED_UNTIL:
                _BLOCKED_UNTIL = 0.0
                _BLOCK_KIND = ""
                _BLOCK_REASON = ""
                _save_state_locked()
            return
    raise GeminiUnavailableError(kind, remaining, reason)


def run_gemini_call(call: Callable[[], T]) -> T:
    """Executa uma chamada síncrona ao SDK com circuit breaker global."""
    check_gemini_available()
    try:
        result = call()
    except GeminiUnavailableError:
        raise
    except Exception as exc:
        classified = classify_gemini_error(exc)
        if classified is None:
            raise
        kind, cooldown = classified
        _register_block(kind, cooldown, _extract_text(exc))
        raise GeminiUnavailableError(kind, cooldown, _extract_text(exc)) from exc
    else:
        # Não limpa aqui: outra chamada concorrente pode ter aberto o circuito
        # depois do nosso check inicial. O check seguinte limpa bloqueios expirados.
        return result


def clear_gemini_circuit() -> None:
    """Limpa bloqueio após uma chamada bem-sucedida (ou por ferramenta administrativa/testes)."""
    global _BLOCKED_UNTIL, _BLOCK_KIND, _BLOCK_REASON
    with _LOCK:
        _load_state_locked()
        _BLOCKED_UNTIL = 0.0
        _BLOCK_KIND = ""
        _BLOCK_REASON = ""
        try:
            _state_path().unlink(missing_ok=True)
        except OSError:
            log.debug("Não foi possível remover o estado persistido do circuit breaker.", exc_info=True)


def gemini_status() -> dict[str, Any]:
    with _LOCK:
        _load_state_locked()
        remaining = max(0, int(_BLOCKED_UNTIL - time.time()))
        return {
            "blocked": remaining > 0,
            "kind": _BLOCK_KIND or None,
            "remaining_seconds": remaining,
            "reason": _BLOCK_REASON[:300] if remaining else None,
            "state_file": str(_state_path()),
        }


def _reset_for_tests() -> None:
    """Reset interno para testes unitários; não usar em produção."""
    global _BLOCKED_UNTIL, _BLOCK_KIND, _BLOCK_REASON, _STATE_LOADED
    with _LOCK:
        _BLOCKED_UNTIL = 0.0
        _BLOCK_KIND = ""
        _BLOCK_REASON = ""
        _STATE_LOADED = True
        try:
            _state_path().unlink(missing_ok=True)
        except OSError:
            pass
