"""Circuit breakers independentes para dois projetos Gemini.

As quotas são isoladas por projeto Google, não por chave. Use chaves de projetos
separados para que o segundo projeto funcione como reserva operacional. Cada
projeto tem estado persistido próprio; nenhuma chamada paga é iniciada pelo bot
além das funcionalidades habilitadas no projeto Google.
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TypeVar

log = logging.getLogger("soulsbot.gemini")
T = TypeVar("T")


class GeminiUnavailableError(RuntimeError):
    """Quota, rate limit ou indisponibilidade de uma das contas/projetos Gemini."""

    def __init__(self, kind: str, retry_after_seconds: int, technical_message: str,
                 provider: str = "primary"):
        self.kind = kind
        self.provider = provider if provider in {"primary", "backup"} else "primary"
        self.retry_after_seconds = max(1, int(retry_after_seconds))
        self.technical_message = (technical_message or "Falha sem detalhes retornados pelo SDK")[:1200]
        provider_label = "Gemini principal" if self.provider == "primary" else "Gemini reserva"
        if kind == "quota":
            user_message = (
                f"A quota disponível do {provider_label} foi atingida. O Soulsbot pausou esse projeto "
                "e tentou usar o outro projeto Gemini, quando configurado."
            )
            admin_message = (
                f"Quota esgotada ou limite de billing no {provider_label}. Confira o projeto Google, "
                "os limites e a disponibilidade gratuita do modelo Gemini. "
                f"Circuito pausado por até {self.retry_after_seconds // 60 or 1} minuto(s)."
            )
        elif kind == "rate_limit":
            minutes = max(1, (self.retry_after_seconds + 59) // 60)
            user_message = f"O {provider_label} está limitando temporariamente as solicitações."
            admin_message = f"Rate limit no {provider_label}. Circuito pausado por {self.retry_after_seconds}s."
        elif kind == "auth":
            user_message = f"A chave ou a permissão do {provider_label} não foi aceita; a Nara tentará o outro projeto."
            admin_message = f"Credencial/permissão inválida no {provider_label} (401/403). Confira a chave, o projeto e o acesso ao modelo."
        else:
            user_message = f"O {provider_label} está temporariamente indisponível."
            admin_message = f"Indisponibilidade no {provider_label}. Circuito pausado por {self.retry_after_seconds}s."
        self.user_message = user_message
        self.admin_message = admin_message
        super().__init__(user_message)

    def __str__(self) -> str:
        return self.user_message


@dataclass
class _Circuit:
    blocked_until: float = 0.0
    kind: str = ""
    reason: str = ""
    loaded: bool = False


_LOCK = threading.RLock()
_CIRCUITS = {"primary": _Circuit(), "backup": _Circuit()}


def _provider(provider: str) -> str:
    value = str(provider or "primary").strip().lower()
    if value not in _CIRCUITS:
        raise ValueError("Provedor Gemini inválido; use 'primary' ou 'backup'.")
    return value


def _prefix(provider: str) -> str:
    return "GEMINI_BACKUP" if provider == "backup" else "GEMINI"


def _int_env(name: str, default: int, minimum: int = 1, maximum: int = 604800) -> int:
    try:
        value = int(os.getenv(name, str(default)).strip())
        return min(maximum, max(minimum, value))
    except (TypeError, ValueError):
        log.warning("Configuração %s inválida; usando %s.", name, default)
        return default


def _state_path(provider: str = "primary") -> Path:
    provider = _provider(provider)
    if provider == "backup":
        raw = os.getenv("GEMINI_BACKUP_CIRCUIT_STATE_FILE", "data/gemini_backup_circuit.json")
        return Path(raw.strip() or "data/gemini_backup_circuit.json")
    raw = os.getenv("GEMINI_CIRCUIT_STATE_FILE", "data/gemini_circuit.json")
    return Path(raw.strip() or "data/gemini_circuit.json")


def _load_locked(provider: str) -> None:
    state = _CIRCUITS[provider]
    if state.loaded:
        return
    state.loaded = True
    path = _state_path(provider)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        blocked_until = float(payload.get("blocked_until", 0))
        if blocked_until > time.time():
            state.blocked_until = blocked_until
            state.kind = str(payload.get("kind", "unavailable"))[:40]
            state.reason = str(payload.get("reason", "Bloqueio persistido"))[:500]
            log.warning("Circuit breaker Gemini %s restaurado: tipo=%s, restante=%ss.",
                        provider, state.kind, max(1, int(state.blocked_until - time.time())))
        else:
            path.unlink(missing_ok=True)
    except FileNotFoundError:
        return
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        log.warning("Não foi possível ler o circuito Gemini %s; usando memória.", provider, exc_info=True)


def _save_locked(provider: str) -> None:
    state = _CIRCUITS[provider]
    path = _state_path(provider)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "provider": provider,
            "blocked_until": state.blocked_until,
            "blocked_until_utc": datetime.fromtimestamp(state.blocked_until, timezone.utc).isoformat()
                if state.blocked_until else None,
            "kind": state.kind,
            "reason": state.reason[:500],
        }
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)
    except OSError:
        log.warning("Não foi possível persistir o circuito Gemini %s.", provider, exc_info=True)


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
        try:
            value = getattr(exc, attr, None)
            if value is not None and 100 <= int(value) <= 599:
                return int(value)
        except (TypeError, ValueError):
            pass
    match = re.search(r"\b(?:HTTP(?:/\d(?:\.\d)?)?\s*)?(401|403|408|429|500|502|503|504)\b", text, re.I)
    return int(match.group(1)) if match else None


def _retry_after(exc: BaseException, text: str) -> int | None:
    match = re.search(r"retryDelay\s*[\"']?\s*:\s*[\"'](\d+(?:\.\d+)?)s", text, re.I)
    if not match:
        match = re.search(r"retry\s+after\s+(\d+(?:\.\d+)?)\s+seconds?", text, re.I)
    if match:
        return min(3600, max(1, int(float(match.group(1)) + 0.999)))
    headers = getattr(getattr(exc, "response", None), "headers", None)
    try:
        value = headers.get("Retry-After") if headers else None
        return min(3600, max(1, int(float(value) + 0.999))) if value else None
    except (TypeError, ValueError):
        return None


def classify_gemini_error(exc: BaseException, provider: str = "primary") -> tuple[str, int] | None:
    provider = _provider(provider)
    prefix = _prefix(provider)
    text = _extract_text(exc)
    status = _status_code(exc, text)
    if status in (401, 403):
        return "auth", _int_env(f"{prefix}_AUTH_COOLDOWN_SECONDS", 3600, 60, 86400)
    if status not in (408, 429, 500, 502, 503, 504) and "RESOURCE_EXHAUSTED" not in text.upper():
        return None
    lowered = text.casefold()
    if status == 429 or "resource_exhausted" in lowered:
        quota_signals = (
            "you exceeded your current quota", "check your plan and billing", "quota exceeded",
            "daily quota", "quota per day", "requests per day", "billing", "insufficient credits",
            "prepay", "spend cap", "per_day", "requestsperday", "quota_limit", "free_tier",
        )
        if any(signal in lowered for signal in quota_signals):
            return "quota", _int_env(f"{prefix}_QUOTA_COOLDOWN_SECONDS", 21600, 60)
        return "rate_limit", _retry_after(exc, text) or _int_env(f"{prefix}_RATE_LIMIT_COOLDOWN_SECONDS", 60, 5, 3600)
    if status in (408, 500, 502, 503, 504):
        return "unavailable", _retry_after(exc, text) or _int_env(f"{prefix}_UNAVAILABLE_COOLDOWN_SECONDS", 45, 5, 3600)
    return None


def _register_block(provider: str, kind: str, seconds: int, reason: str) -> None:
    with _LOCK:
        _load_locked(provider)
        state = _CIRCUITS[provider]
        proposed = time.time() + max(1, seconds)
        if proposed >= state.blocked_until:
            state.kind = kind
            state.reason = reason[:500]
        state.blocked_until = max(state.blocked_until, proposed)
        _save_locked(provider)
    log.error("Circuit breaker Gemini %s ativado: tipo=%s, duração=%ss, motivo=%s",
              provider, kind, seconds, reason[:300])


def check_gemini_available(provider: str = "primary") -> None:
    provider = _provider(provider)
    with _LOCK:
        _load_locked(provider)
        state = _CIRCUITS[provider]
        remaining = int(state.blocked_until - time.time())
        if remaining > 0:
            kind, reason = state.kind or "unavailable", state.reason or "limite temporário"
        else:
            if state.blocked_until:
                state.blocked_until, state.kind, state.reason = 0.0, "", ""
                _save_locked(provider)
            return
    raise GeminiUnavailableError(kind, remaining, reason, provider=provider)


def run_gemini_call(call: Callable[[], T], provider: str = "primary") -> T:
    provider = _provider(provider)
    check_gemini_available(provider)
    try:
        return call()
    except GeminiUnavailableError:
        raise
    except Exception as exc:
        classified = classify_gemini_error(exc, provider)
        if classified is None:
            raise
        kind, cooldown = classified
        reason = _extract_text(exc)
        _register_block(provider, kind, cooldown, reason)
        raise GeminiUnavailableError(kind, cooldown, reason, provider=provider) from exc


def clear_gemini_circuit(provider: str = "primary") -> None:
    provider = _provider(provider)
    with _LOCK:
        _load_locked(provider)
        state = _CIRCUITS[provider]
        state.blocked_until, state.kind, state.reason = 0.0, "", ""
        try:
            _state_path(provider).unlink(missing_ok=True)
        except OSError:
            log.debug("Não foi possível remover o circuito Gemini %s.", provider, exc_info=True)


def gemini_status(provider: str = "primary") -> dict[str, Any]:
    provider = _provider(provider)
    with _LOCK:
        _load_locked(provider)
        state = _CIRCUITS[provider]
        remaining = max(0, int(state.blocked_until - time.time()))
        return {
            "provider": provider,
            "blocked": remaining > 0,
            "kind": state.kind or None,
            "remaining_seconds": remaining,
            "reason": state.reason[:300] if remaining else None,
            "state_file": str(_state_path(provider)),
        }


def all_gemini_status() -> dict[str, dict[str, Any]]:
    return {name: gemini_status(name) for name in ("primary", "backup")}


def _reset_for_tests() -> None:
    with _LOCK:
        for state in _CIRCUITS.values():
            state.blocked_until, state.kind, state.reason, state.loaded = 0.0, "", "", False
