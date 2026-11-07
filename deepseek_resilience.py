"""Circuit breaker independente para a API DeepSeek.

Classifica saldo insuficiente (402), rate limit (429), indisponibilidade (5xx)
e falhas de rede. Persiste o bloqueio para evitar repetir chamadas após reinícios.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TypeVar

log = logging.getLogger("soulsbot.deepseek")
T = TypeVar("T")


class DeepSeekUnavailableError(RuntimeError):
    def __init__(self, kind: str, retry_after_seconds: int, technical_message: str):
        self.kind = kind
        self.retry_after_seconds = max(1, int(retry_after_seconds))
        self.technical_message = (technical_message or "Sem detalhes do provedor")[:1200]
        if kind == "quota":
            self.user_message = "A quota/saldo do DeepSeek está indisponível. A Nara está alternando para o Gemini."
            self.admin_message = "DeepSeek retornou saldo insuficiente (HTTP 402). Confira créditos e faturamento."
        elif kind == "rate_limit":
            self.user_message = "O DeepSeek atingiu um limite temporário. A Nara está tentando o Gemini como reserva."
            self.admin_message = f"DeepSeek HTTP 429. Circuit breaker ativo por {self.retry_after_seconds}s."
        elif kind == "auth":
            self.user_message = "A chave do DeepSeek não foi aceita. A Nara está tentando o Gemini como reserva."
            self.admin_message = "DeepSeek HTTP 401: chave ausente, inválida ou revogada. Confira DEEPSEEK_API_KEY."
        else:
            self.user_message = "O DeepSeek está temporariamente indisponível. A Nara está tentando o Gemini como reserva."
            self.admin_message = f"DeepSeek indisponível ({kind}). Circuit breaker ativo por {self.retry_after_seconds}s."
        super().__init__(self.user_message)


class DeepSeekHTTPError(RuntimeError):
    def __init__(self, status_code: int, body: str):
        self.status_code = int(status_code)
        self.body = (body or "")[:2500]
        super().__init__(f"DeepSeek HTTP {self.status_code}: {self.body}")


_LOCK = threading.RLock()
_BLOCKED_UNTIL = 0.0
_BLOCK_KIND = ""
_BLOCK_REASON = ""
_STATE_LOADED = False


def _env_int(name: str, default: int, minimum: int = 1, maximum: int = 604800) -> int:
    try:
        return max(minimum, min(maximum, int(os.getenv(name, str(default)).strip())))
    except (TypeError, ValueError):
        return default


def _state_path() -> Path:
    return Path(os.getenv("DEEPSEEK_CIRCUIT_STATE_FILE", "data/deepseek_circuit.json").strip() or "data/deepseek_circuit.json")


def _load_locked() -> None:
    global _STATE_LOADED, _BLOCKED_UNTIL, _BLOCK_KIND, _BLOCK_REASON
    if _STATE_LOADED:
        return
    _STATE_LOADED = True
    path = _state_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        until = float(data.get("blocked_until", 0))
        if until > time.time():
            _BLOCKED_UNTIL = until
            _BLOCK_KIND = str(data.get("kind", "unavailable"))[:40]
            _BLOCK_REASON = str(data.get("reason", "Circuit restaurado"))[:500]
            log.warning("Circuit breaker DeepSeek restaurado: tipo=%s, restante=%ss", _BLOCK_KIND, int(until-time.time()))
        else:
            path.unlink(missing_ok=True)
    except FileNotFoundError:
        pass
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        log.warning("Não foi possível ler o circuito persistido do DeepSeek", exc_info=True)


def _save_locked() -> None:
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
        log.warning("Não foi possível persistir circuito DeepSeek; proteção permanece em memória", exc_info=True)


def check_deepseek_available() -> None:
    global _BLOCKED_UNTIL, _BLOCK_KIND, _BLOCK_REASON
    with _LOCK:
        _load_locked()
        remaining = int(_BLOCKED_UNTIL - time.time())
        if remaining <= 0:
            if _BLOCKED_UNTIL:
                _BLOCKED_UNTIL = 0.0
                _BLOCK_KIND = ""
                _BLOCK_REASON = ""
                _save_locked()
            return
        kind, reason = _BLOCK_KIND or "unavailable", _BLOCK_REASON or "Limite temporário"
    raise DeepSeekUnavailableError(kind, remaining, reason)


def _register(kind: str, seconds: int, reason: str) -> None:
    global _BLOCKED_UNTIL, _BLOCK_KIND, _BLOCK_REASON
    with _LOCK:
        _load_locked()
        until = time.time() + max(1, int(seconds))
        if until >= _BLOCKED_UNTIL:
            _BLOCK_KIND, _BLOCK_REASON = kind, reason[:500]
        _BLOCKED_UNTIL = max(_BLOCKED_UNTIL, until)
        _save_locked()
    log.error("Circuit breaker DeepSeek ativado: tipo=%s, duração=%ss, motivo=%s", kind, seconds, reason[:250])


def _classify(exc: BaseException) -> tuple[str, int] | None:
    if isinstance(exc, DeepSeekHTTPError):
        status, text = exc.status_code, exc.body.casefold()
    else:
        text = str(exc).casefold()
        status = None
        for attr in ("status_code", "code", "status"):
            try:
                value = getattr(exc, attr, None)
                if value is not None and 100 <= int(value) <= 599:
                    status = int(value)
                    break
            except (TypeError, ValueError):
                pass
        response = getattr(exc, "response", None)
        if response is not None:
            try:
                status = int(response.status_code)
                text = (getattr(response, "text", "") or text).casefold()
            except (TypeError, ValueError):
                pass
    if status == 402 or any(x in text for x in ("insufficient balance", "out of balance", "balance is insufficient")):
        return "quota", _env_int("DEEPSEEK_QUOTA_COOLDOWN_SECONDS", 21600, 60)
    if status in (401, 403):
        return "auth", _env_int("DEEPSEEK_AUTH_COOLDOWN_SECONDS", 3600, 60)
    if status == 404:
        return "configuration", _env_int("DEEPSEEK_AUTH_COOLDOWN_SECONDS", 3600, 60)
    if status == 429:
        return "rate_limit", _env_int("DEEPSEEK_RATE_LIMIT_COOLDOWN_SECONDS", 60, 5, 3600)
    if status in (408, 500, 502, 503, 504) or isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return "unavailable", _env_int("DEEPSEEK_UNAVAILABLE_COOLDOWN_SECONDS", 45, 5, 3600)
    # requests exceptions are recognized by class name to keep this module optional-dependency free.
    if type(exc).__name__ in {"Timeout", "ConnectionError", "ConnectTimeout", "ReadTimeout"}:
        return "unavailable", _env_int("DEEPSEEK_UNAVAILABLE_COOLDOWN_SECONDS", 45, 5, 3600)
    return None


def run_deepseek_call(call: Callable[[], T]) -> T:
    check_deepseek_available()
    try:
        return call()
    except DeepSeekUnavailableError:
        raise
    except Exception as exc:
        classified = _classify(exc)
        if classified is None:
            raise
        kind, seconds = classified
        _register(kind, seconds, str(exc))
        raise DeepSeekUnavailableError(kind, seconds, str(exc)) from exc


def deepseek_status() -> dict[str, Any]:
    with _LOCK:
        _load_locked()
        remaining = max(0, int(_BLOCKED_UNTIL - time.time()))
        return {
            "blocked": remaining > 0,
            "kind": _BLOCK_KIND or None,
            "remaining_seconds": remaining,
            "reason": _BLOCK_REASON[:300] if remaining else None,
            "state_file": str(_state_path()),
        }


def _reset_for_tests() -> None:
    global _BLOCKED_UNTIL, _BLOCK_KIND, _BLOCK_REASON, _STATE_LOADED
    with _LOCK:
        _BLOCKED_UNTIL, _BLOCK_KIND, _BLOCK_REASON = 0.0, "", ""
        _STATE_LOADED = True
        try:
            _state_path().unlink(missing_ok=True)
        except OSError:
            pass
