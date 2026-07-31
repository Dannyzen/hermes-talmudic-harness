"""Hermes tool wrapper for the Talmudic AI harness (user plugin)."""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict

from hermes_cli.config import load_config
from hermes_constants import get_hermes_home

from .harness import (
    build_amoraic_refinement,
    build_chavrusa_brief,
    build_eduyot_entry,
    build_teaching_friend_request,
    normalize_harness_config,
)

logger = logging.getLogger(__name__)


_ACTIONS = [
    "refine_question",
    "chavrusa_brief",
    "teaching_friend_request",
    "eduyot_entry",
]

_ACTION_CONFIG_KEYS = {
    "refine_question": "amoraic",
    "chavrusa_brief": "chavrusa",
    "teaching_friend_request": "teaching_friend",
    "eduyot_entry": "eduyot",
}

_LEGACY_DEFAULT_LEDGER_PATH = "~/.hermes/talmudic_harness/eduyot.jsonl"


TALMUDIC_HARNESS_SCHEMA = {
    "name": "talmudic_harness",
    "description": (
        "Run deterministic Talmudic harness primitives: Amoraic question "
        "refinement, Chavrusa proposer/challenger briefs, Teaching Friend "
        "verification requests, and Eduyot rejected-branch entries."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": _ACTIONS,
                "description": "Harness primitive to execute.",
            },
            "task": {
                "type": "string",
                "description": "The task, claim, or decision being reasoned about.",
            },
            "context": {
                "type": "string",
                "description": "Optional grounding context or constraints.",
            },
            "question_count": {
                "type": "integer",
                "description": "Number of candidate questions for refine_question.",
                "default": 5,
                "minimum": 1,
                "maximum": 12,
            },
            "proposed_solution": {
                "type": "string",
                "description": "Solution path to debate for chavrusa_brief.",
            },
            "answer": {
                "type": "string",
                "description": "Draft answer to verify for teaching_friend_request.",
            },
            "rejected_branch": {
                "type": "string",
                "description": "Rejected or minority branch to preserve for eduyot_entry.",
            },
            "reason": {
                "type": "string",
                "description": "Reason the branch was rejected for eduyot_entry.",
            },
            "resurrect_when": {
                "type": "string",
                "description": "Future condition where the rejected branch may become relevant.",
            },
            "evidence": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional evidence lines for an eduyot_entry.",
            },
        },
        "required": ["action", "task"],
        "additionalProperties": False,
    },
}


def _success(result: Dict[str, Any]) -> str:
    return json.dumps({"success": True, "result": result}, ensure_ascii=False)


def _error(code: str, message: str | None = None) -> str:
    payload = {"error": code}
    if message:
        payload["message"] = message
    return json.dumps(payload, ensure_ascii=False)


class HarnessError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _load_harness_config() -> Dict[str, Any]:
    config = load_config() or {}
    section = config.get("talmudic_harness", {}) if isinstance(config, dict) else {}
    return normalize_harness_config(section if isinstance(section, dict) else {})


def _require_enabled(action: str) -> Dict[str, Any]:
    harness_config = _load_harness_config()
    if not harness_config.get("enabled"):
        raise HarnessError("action_disabled", "talmudic_harness is disabled")
    section_name = _ACTION_CONFIG_KEYS[action]
    section = harness_config.get(section_name, {})
    if not isinstance(section, dict) or not section.get("enabled"):
        raise HarnessError(
            "action_disabled", f"talmudic_harness action '{action}' is disabled"
        )
    if action == "eduyot_entry" and not section.get("retain_rejected_branches", True):
        raise HarnessError(
            "action_disabled", "talmudic_harness action 'eduyot_entry' is disabled"
        )
    return harness_config


def _append_jsonl(path: Path, entry: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    encoded = (
        json.dumps(entry, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        written = os.write(descriptor, encoded)
        if written != len(encoded):
            raise OSError(f"short JSONL write: wrote {written} of {len(encoded)} bytes")
    finally:
        os.close(descriptor)


def _resolve_ledger_path(configured_path: Any) -> Path:
    hermes_home = get_hermes_home().expanduser().resolve()
    raw_path = str(configured_path or "").strip()
    if not raw_path:
        raise HarnessError("invalid_ledger_path", "eduyot ledger_path is required")
    if raw_path == _LEGACY_DEFAULT_LEDGER_PATH:
        candidate = hermes_home / "talmudic_harness" / "eduyot.jsonl"
    else:
        expanded = Path(os.path.expandvars(os.path.expanduser(raw_path)))
        candidate = expanded if expanded.is_absolute() else hermes_home / expanded
    candidate = candidate.resolve()
    try:
        candidate.relative_to(hermes_home)
    except ValueError as exc:
        raise HarnessError(
            "invalid_ledger_path", "eduyot ledger_path must stay within HERMES_HOME"
        ) from exc
    return candidate


def talmudic_harness(args: Dict[str, Any], **kwargs) -> str:
    if not isinstance(args, dict):
        return _error("invalid_arguments", "arguments must be an object")
    action = str(args.get("action") or "").strip()
    task = str(args.get("task") or "").strip()
    context = str(args.get("context") or "").strip()

    if action not in _ACTIONS:
        return _error(
            "unsupported_action", f"Unsupported action: {action or '<empty>'}"
        )
    if not task:
        return _error("invalid_arguments", "task is required")

    try:
        harness_config = _require_enabled(action)

        if action == "refine_question":
            return _success(
                build_amoraic_refinement(
                    task=task,
                    context=context,
                    question_count=args.get("question_count", 5),
                )
            )

        if action == "chavrusa_brief":
            brief = build_chavrusa_brief(
                task=task,
                proposed_solution=args.get("proposed_solution", ""),
                context=context,
            )
            chavrusa_cfg = harness_config.get("chavrusa") or {}
            brief["model_routing"] = {
                "proposer": {
                    "model": str(chavrusa_cfg.get("proposer_model") or "").strip()
                    or None,
                    "provider": str(chavrusa_cfg.get("proposer_provider") or "").strip()
                    or None,
                },
                "challenger": {
                    "model": str(chavrusa_cfg.get("challenger_model") or "").strip()
                    or None,
                    "provider": str(
                        chavrusa_cfg.get("challenger_provider") or ""
                    ).strip()
                    or None,
                },
            }
            brief["executor"] = "caller_managed"
            brief["next_instruction"] = (
                "If model review is warranted, the caller must dispatch proposer and "
                "challenger separately with explicitly restricted read-only tools."
            )
            return _success(brief)

        if action == "teaching_friend_request":
            request = build_teaching_friend_request(
                task=task,
                answer=args.get("answer", ""),
                context=context,
            )
            request["executor"] = "caller_managed"
            request["next_instruction"] = (
                "If an independent restatement is warranted, the caller must dispatch "
                "a verifier with explicitly restricted read-only tools."
            )
            return _success(request)

        if action == "eduyot_entry":
            entry = build_eduyot_entry(
                task=task,
                rejected_branch=args.get("rejected_branch", ""),
                reason=args.get("reason", ""),
                resurrect_when=args.get("resurrect_when", ""),
                evidence=args.get("evidence") or [],
            )
            parent_agent = kwargs.get("parent_agent")
            entry["timestamp"] = time.time()
            if parent_agent is not None:
                session_id = getattr(parent_agent, "session_id", None)
                task_id = getattr(parent_agent, "task_id", None)
                if session_id:
                    entry["session_id"] = session_id
                if task_id:
                    entry["task_id"] = task_id

            eduyot_config = harness_config["eduyot"]
            ledger_path = _resolve_ledger_path(eduyot_config["ledger_path"])
            _append_jsonl(ledger_path, entry)
            entry["persisted"] = True
            entry["ledger_type"] = "jsonl"
            entry["ledger_path"] = str(
                ledger_path.relative_to(get_hermes_home().expanduser().resolve())
            )
            return _success(entry)
    except HarnessError as exc:
        return _error(exc.code, str(exc))
    except ValueError as exc:
        return _error("invalid_arguments", str(exc))
    except OSError:
        logger.exception("talmudic_harness persistence failed")
        return _error("persistence_failed", "The harness could not persist this entry")
    except Exception:
        logger.exception("talmudic_harness action failed")
        return _error("action_failed", "The harness action failed")

    return _error("unsupported_action", f"Unsupported action: {action}")
