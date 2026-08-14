"""Structured JSON logging and CloudWatch Embedded Metric Format helpers."""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

_logger = logging.getLogger("wiki")
_logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())


def log(event: str, *, level: int = logging.INFO, **fields: Any) -> None:
    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "level": logging.getLevelName(level),
        "event": event,
        **fields,
    }
    _logger.log(level, json.dumps(payload, ensure_ascii=False, default=str))


def metric(
    name: str,
    value: float,
    *,
    unit: str = "Count",
    service: str,
    **fields: Any,
) -> None:
    payload = {
        "_aws": {
            "Timestamp": int(datetime.now(UTC).timestamp() * 1_000),
            "CloudWatchMetrics": [
                {
                    "Namespace": "IntelligentCorporateWiki",
                    "Dimensions": [["Service"]],
                    "Metrics": [{"Name": name, "Unit": unit}],
                }
            ],
        },
        "Service": service,
        name: value,
        **fields,
    }
    _logger.info(json.dumps(payload, ensure_ascii=False, default=str))
