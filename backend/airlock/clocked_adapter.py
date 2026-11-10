"""Live Clocked transport and schema validation, separate from authorization.

Unknown verdict labels remain untouched for the trusted policy to HOLD. Raw
response bodies are preserved; SDK headers, error messages and exception bodies
are never included because they may contain credentials or upstream internals.
"""
from __future__ import annotations

import asyncio
import json
import math
import os
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Dict, Optional

from clocked_sdk import AsyncClocked, ClockedError
from dotenv import load_dotenv

from .models import Check


PII_ENTITIES = ["person", "email", "phone", "username", "address"]


def _number(value: Any) -> Optional[float]:
    """Reject booleans, numeric strings, negative and non-finite measurements."""
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        return None
    return float(value)


def _probability(value: Any) -> bool:
    return _number(value) is not None and value <= 1


def _valid_body(endpoint: str, raw: Dict[str, Any]) -> bool:
    """Validate fields needed for safe interpretation, never infer missing ones."""
    if endpoint == "pii":
        return (
            isinstance(raw.get("anonymized_text"), str)
            and isinstance(raw.get("entities"), list)
            and all(isinstance(item, dict) for item in raw["entities"])
        )
    if not isinstance(raw.get("verdict"), str) or not raw["verdict"]:
        return False
    if not isinstance(raw.get("evidence"), list):
        return False
    if not all(isinstance(item, dict) for item in raw["evidence"]):
        return False
    if endpoint == "injection":
        return _probability(raw.get("injection"))
    return _probability(raw.get("malicious")) and _probability(raw.get("suspicious"))


class ClockedAdapter:
    """One reusable async SDK client; fake clients are only injected by tests.

    The whole call has a bounded deadline independent of the SDK's per-operation
    timeout. SDK retries retain their idempotency key; no outer retry is added.
    Missing credentials produce failed checks, never a simulated successful one.
    """

    def __init__(
        self,
        client: Any = None,
        *,
        api_key: Optional[str] = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        if type(timeout_seconds) not in (int, float) or not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive and finite")
        self.timeout_seconds = float(timeout_seconds)
        self.client = client
        self._initialization_failed = False
        if client is None:
            load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
            key = api_key if api_key is not None else os.getenv("CLOCKED_API_KEY")
            if key:
                try:
                    self.client = AsyncClocked(
                        api_key=key,
                        timeout=max(45.0, self.timeout_seconds + 10),
                        max_attempts=2,
                    )
                except Exception:
                    self._initialization_failed = True

    async def check_injection(self, text: str) -> Check:
        return await self._call(
            "injection", text, text=text, source="content", evidence=True
        )

    async def redact_personal_data(self, text: str) -> Check:
        return await self._call(
            "pii", text, text=text, entities=list(PII_ENTITIES),
            threshold=0.5, anonymize="replace",
        )

    async def inspect_script(self, script: str) -> Check:
        # The script is sent as data. No subprocess or code evaluation exists.
        return await self._call(
            "script", script, script=script, threshold=0.3, evidence=True
        )

    async def _call(self, endpoint: str, input_text: str, **arguments: Any) -> Check:
        start = time.perf_counter()
        check = Check(endpoint=endpoint, input_text=input_text)
        if self.client is None or self._initialization_failed:
            return self._failure(check, start, "security_check_unavailable", "NotConfigured")
        try:
            result = await asyncio.wait_for(
                getattr(self.client, endpoint)(**arguments),
                timeout=self.timeout_seconds,
            )
            if not isinstance(result, Mapping):
                return self._failure(check, start, "invalid_security_response", "InvalidBody")
            raw = dict(result)
            # Validate JSON serializability before retaining any body or emitting SSE.
            # allow_nan=False also rejects Infinity and NaN anywhere in a response.
            json.dumps(raw, allow_nan=False)
            check.raw = raw
            check.latency_ms = round((time.perf_counter() - start) * 1000, 3)
            check.model_ms = _number(getattr(result, "model_ms", None))
            check.credits = _number(getattr(result, "credits", None))
            check.cost_usd = _number(getattr(result, "cost_usd", None))
            cost_basis = getattr(result, "cost_basis", None)
            check.cost_basis = cost_basis if cost_basis in {"prepaid", "overage", "mixed", "reference"} else None
            if not _valid_body(endpoint, raw):
                return self._failure(check, start, "invalid_security_response", "InvalidShape")
            check.verdict = raw.get("verdict") if endpoint != "pii" else None
            check.safe_text = raw["anonymized_text"] if endpoint == "pii" else None
            # Keep the reported spans exactly. Consumers must verify boundaries and
            # quote/value matches before highlighting; never find/repair a substring.
            check.evidence = raw["entities"] if endpoint == "pii" else raw["evidence"]
            return check
        except asyncio.CancelledError:
            # Server shutdown/caller cancellation must not become a successful check.
            raise
        except ClockedError as error:
            return self._failure(
                check, start, "security_check_unavailable", type(error).__name__, error.status
            )
        except asyncio.TimeoutError:
            return self._failure(check, start, "security_check_unavailable", "DeadlineExceeded")
        except (TypeError, ValueError):
            return self._failure(check, start, "invalid_security_response", "InvalidBody")
        except Exception:
            # Unexpected transport/client errors must also fail closed, without
            # copying a potentially sensitive exception message into the audit.
            return self._failure(check, start, "security_check_unavailable", "AdapterFailure")

    @staticmethod
    def _failure(
        check: Check,
        start: float,
        reason: str,
        error_type: str,
        status: Optional[int] = None,
    ) -> Check:
        check.status = "error"
        check.error = reason
        check.verdict = None
        check.safe_text = None
        check.evidence = []
        check.latency_ms = round((time.perf_counter() - start) * 1000, 3)
        if not check.raw:
            # Explicit adapter metadata; this is not presented as an API response.
            check.raw = {"adapter_error": {"type": error_type, "http_status": status}}
        return check

    async def aclose(self) -> None:
        if self.client is not None:
            await self.client.aclose()


class UnavailableAdapter:
    """Explicit failure drill. It never makes a request or fabricates a verdict."""

    @staticmethod
    def _check(endpoint: str, text: str) -> Check:
        return Check(
            endpoint=endpoint, input_text=text, status="error",
            error="security_check_unavailable",
            raw={"adapter_error": {"type": "InjectedFailureDrill", "http_status": None}},
        )

    async def check_injection(self, text: str) -> Check:
        return self._check("injection", text)

    async def redact_personal_data(self, text: str) -> Check:
        return self._check("pii", text)

    async def inspect_script(self, script: str) -> Check:
        return self._check("script", script)

    async def aclose(self) -> None:
        return None
