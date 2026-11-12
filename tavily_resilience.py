"""Circuit breaker do plano gratuito Tavily (sem fallback para cobrança).

HTTP 432/433 encerra as consultas até o primeiro dia do próximo mês UTC.
HTTP 429 aplica pausa curta. A aplicação nunca ativa Pay-as-you-go nem compra créditos.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from runtime_paths import get_state_path
from typing import Any, Callable, TypeVar

log = logging.getLogger("nara.tavily")
T = TypeVar("T")
_LOCK = threading.RLock()
_BLOCKED_UNTIL = 0.0
_BLOCK_KIND = ""
_BLOCK_REASON = ""
_STATE_LOADED = False


class TavilyUnavailableError(RuntimeError):
    def __init__(self, kind: str, retry_after_seconds: int, technical_message: str = ""):
        self.kind = kind
        self.retry_after_seconds = max(1, int(retry_after_seconds))
        self.technical_message = (technical_message or "Sem detalhes do serviço")[:1200]
        if kind == "quota":
            self.user_message = "A cota mensal gratuita de pesquisa foi usada. As pesquisas ficam pausadas até a renovação, sem cobrança automática."
            self.admin_message = "Tavily Free sem créditos (HTTP 432/433). Nenhum plano pago foi ativado."
        elif kind == "rate_limit":
            self.user_message = "A pesquisa gratuita está temporariamente limitada. Tente novamente em alguns instantes."
            self.admin_message = f"Tavily HTTP 429; pausa de {self.retry_after_seconds}s."
        elif kind == "auth":
            self.user_message = "A chave gratuita de pesquisa não foi aceita. A administração precisa conferir TAVILY_API_KEY."
            self.admin_message = "Tavily HTTP 401/403: chave inválida ou plano sem permissão."
        else:
            self.user_message = "O serviço gratuito de pesquisa está temporariamente indisponível. Tente novamente mais tarde."
            self.admin_message = f"Tavily indisponível ({kind}); pausa de {self.retry_after_seconds}s."
        super().__init__(self.user_message)


class TavilyHTTPError(RuntimeError):
    def __init__(self, status_code: int, body: str, retry_after: str | None = None):
        self.status_code = int(status_code)
        self.body = (body or "")[:2200]
        self.retry_after = retry_after
        super().__init__(f"Tavily HTTP {self.status_code}: {self.body}")


def _state_path() -> Path:
    return get_state_path("TAVILY_CIRCUIT_STATE_FILE", "tavily_circuit.json")


def _next_month_utc() -> float:
    now = datetime.now(timezone.utc)
    if now.month == 12:
        next_month = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        next_month = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
    return next_month.timestamp()


def _load_locked() -> None:
    global _STATE_LOADED, _BLOCKED_UNTIL, _BLOCK_KIND, _BLOCK_REASON
    if _STATE_LOADED:
        return
    _STATE_LOADED = True
    try:
        data = json.loads(_state_path().read_text(encoding="utf-8"))
        until = float(data.get("blocked_until", 0))
        if until > time.time():
            _BLOCKED_UNTIL = until
            _BLOCK_KIND = str(data.get("kind", "unavailable"))[:40]
            _BLOCK_REASON = str(data.get("reason", "Circuit restaurado"))[:500]
            log.warning("Circuit breaker Tavily restaurado: tipo=%s; restante=%ss", _BLOCK_KIND, int(until-time.time()))
        else:
            _state_path().unlink(missing_ok=True)
    except FileNotFoundError:
        pass
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        log.warning("Não foi possível ler o estado Tavily", exc_info=True)


def _save_locked() -> None:
    try:
        path = _state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"blocked_until": _BLOCKED_UNTIL,
                   "blocked_until_utc": datetime.fromtimestamp(_BLOCKED_UNTIL, timezone.utc).isoformat(),
                   "kind": _BLOCK_KIND, "reason": _BLOCK_REASON[:500]}
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)
    except OSError:
        log.warning("Não foi possível persistir o circuito Tavily", exc_info=True)


def _classify(exc: BaseException) -> tuple[str, int] | None:
    if isinstance(exc, TavilyHTTPError):
        status = exc.status_code
        body = exc.body.casefold()
        if status == 429:
            try:
                seconds = max(5, min(3600, int(float(exc.retry_after)))) if exc.retry_after else 60
            except (TypeError, ValueError):
                seconds = 60
            return "rate_limit", seconds
    else:
        status = getattr(exc, "status_code", None)
        body = str(exc).casefold()
        try:
            status = int(status) if status is not None else None
        except (TypeError, ValueError):
            status = None
    if status in (402, 432, 433) or any(word in body for word in ("insufficient balance", "plan limit exceeded", "credits exhausted", "out of credits")):

        return "quota", max(60, int(_next_month_utc() - time.time()))
    if status in (401, 403):
        return "auth", 3600
    if status == 429:
        return "rate_limit", 60
    if status in (408, 500, 502, 503, 504) or isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return "unavailable", 90
    return None


def _register(kind: str, seconds: int, reason: str) -> None:
    global _BLOCKED_UNTIL, _BLOCK_KIND, _BLOCK_REASON
    with _LOCK:
        _load_locked()
        until = time.time() + max(1, int(seconds))
        if until >= _BLOCKED_UNTIL:
            _BLOCK_KIND, _BLOCK_REASON = kind, reason[:500]
        _BLOCKED_UNTIL = max(_BLOCKED_UNTIL, until)
        _save_locked()
    log.warning("Circuit breaker Tavily ativado: tipo=%s, duração=%ss, motivo=%s", kind, seconds, reason[:220])


def check_tavily_available() -> None:
    global _BLOCKED_UNTIL, _BLOCK_KIND, _BLOCK_REASON
    with _LOCK:
        _load_locked()
        remaining = int(_BLOCKED_UNTIL - time.time())
        if remaining <= 0:
            if _BLOCKED_UNTIL:
                _BLOCKED_UNTIL, _BLOCK_KIND, _BLOCK_REASON = 0.0, "", ""
                _save_locked()
            return
        kind, reason = _BLOCK_KIND or "unavailable", _BLOCK_REASON
    raise TavilyUnavailableError(kind, remaining, reason)


def run_tavily_call(call: Callable[[], T]) -> T:
    check_tavily_available()
    try:
        return call()
    except TavilyUnavailableError:
        raise
    except Exception as exc:
        classified = _classify(exc)
        if classified is None:
            raise
        kind, seconds = classified
        _register(kind, seconds, str(exc))
        raise TavilyUnavailableError(kind, seconds, str(exc)) from exc


def tavily_status() -> dict[str, Any]:
    with _LOCK:
        _load_locked()
        remaining = max(0, int(_BLOCKED_UNTIL - time.time()))
        return {"blocked": remaining > 0, "kind": _BLOCK_KIND or None,
                "remaining_seconds": remaining, "reason": _BLOCK_REASON[:300] if remaining else None,
                "state_file": str(_state_path())}


def reset_tavily_circuit() -> None:
    global _BLOCKED_UNTIL, _BLOCK_KIND, _BLOCK_REASON
    with _LOCK:
        _BLOCKED_UNTIL, _BLOCK_KIND, _BLOCK_REASON = 0.0, "", ""
        _save_locked()


def _reset_for_tests() -> None:
    global _BLOCKED_UNTIL, _BLOCK_KIND, _BLOCK_REASON, _STATE_LOADED
    with _LOCK:
        _BLOCKED_UNTIL, _BLOCK_KIND, _BLOCK_REASON, _STATE_LOADED = 0.0, "", "", True
        try:
            _state_path().unlink(missing_ok=True)
        except OSError:
            pass
