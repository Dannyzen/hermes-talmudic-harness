"""Talmudic AI harness user plugin for Hermes Agent."""

from __future__ import annotations

import logging
from typing import Any

from .harness import (
    build_talmudic_harness_prompt_guidance,
    normalize_harness_config,
)
from .tool import TALMUDIC_HARNESS_SCHEMA, talmudic_harness

logger = logging.getLogger(__name__)


def _load_harness_section() -> dict:
    try:
        from hermes_cli.config import load_config

        cfg = load_config() or {}
        section = cfg.get("talmudic_harness") if isinstance(cfg, dict) else None
        return normalize_harness_config(section if isinstance(section, dict) else {})
    except Exception as exc:  # pragma: no cover - fail-soft config
        logger.debug("talmudic-harness config load failed: %s", exc)
        return normalize_harness_config({})


def _on_pre_llm_call(**kwargs: Any) -> dict | None:
    """Inject harness guidance into ephemeral user context (cache-safe).

    Unlike the former core system_prompt hook, this never mutates the stable
    system prefix. Empty when disabled or guidance off.
    """
    try:
        harness_cfg = _load_harness_section()
        guidance = build_talmudic_harness_prompt_guidance(harness_cfg)
        if not guidance:
            return None
        return {"context": guidance}
    except Exception as exc:  # pragma: no cover - fail-soft hook
        logger.debug("talmudic-harness pre_llm_call failed: %s", exc)
        return None


def register(ctx) -> None:
    """Register the talmudic_harness tool and optional prompt guidance hook."""
    ctx.register_tool(
        name="talmudic_harness",
        toolset="talmudic_harness",
        schema=TALMUDIC_HARNESS_SCHEMA,
        handler=talmudic_harness,
        check_fn=lambda: True,
        requires_env=[],
        description=TALMUDIC_HARNESS_SCHEMA["description"],
        emoji="📜",
    )
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
    logger.info("talmudic-harness plugin registered tool+pre_llm_call hook")
