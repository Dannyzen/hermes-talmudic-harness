"""Foundational Talmudic AI harness primitives (user plugin).

Deterministic and side-effect free. Runtime tools and hooks compose these
helpers without hidden memory dispatch or background state.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, List


DEFAULT_TALMUDIC_HARNESS_CONFIG: Dict[str, Any] = {
    "enabled": False,
    "prompt_guidance": False,
    "amoraic": {
        "enabled": True,
        "question_count": 5,
        "scoring_weights": {
            "disambiguation": 3,
            "risk_reduction": 3,
            "actionability": 2,
            "context_reuse": 1,
        },
    },
    "chavrusa": {
        "enabled": False,
        "proposer_model": "",
        "proposer_provider": "",
        "challenger_model": "",
        "challenger_provider": "",
        "consensus_required": False,
    },
    "teaching_friend": {
        "enabled": False,
        "provider": "auto",
        "model": "",
        "temperature": 0,
    },
    "eduyot": {
        "enabled": True,
        "ledger_path": "~/.hermes/talmudic_harness/eduyot.jsonl",
        "retain_rejected_branches": True,
    },
}


TALMUDIC_HARNESS_PROMPT_GUIDANCE = """
Talmudic AI Harness: when this mode is enabled and the talmudic_harness tool is
available, use explicit logical signposts for hard reasoning tasks. Start with a
kushya by calling talmudic_harness(action="refine_question") when the best next
question is unclear. Use Chavrusa structure for contested solution paths: keep a
proposer and challenger isolated, compare their claims, and only then converge.
Use the Teaching Friend check to restate the answer in plain English and detect
skipped logical steps. Preserve Eduyot as compact rejected or minority branches
with reasons, using memory or session_search only when the branch is likely to
matter in future sessions.
""".strip()


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(result.get(key), dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on", "enabled"}:
            return True
        if lowered in {"0", "false", "no", "off", "disabled"}:
            return False
    return default


def _clamp_int(value: Any, default: int, minimum: int = 1, maximum: int = 12) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def normalize_harness_config(config: Dict[str, Any] | None) -> Dict[str, Any]:
    """Merge user config with safe defaults and normalize primitive types."""

    merged = _deep_merge(DEFAULT_TALMUDIC_HARNESS_CONFIG, config or {})
    merged["enabled"] = _as_bool(merged.get("enabled"), False)
    merged["prompt_guidance"] = _as_bool(merged.get("prompt_guidance"), False)

    amoraic = merged.get("amoraic")
    if not isinstance(amoraic, dict):
        amoraic = deepcopy(DEFAULT_TALMUDIC_HARNESS_CONFIG["amoraic"])
        merged["amoraic"] = amoraic
    amoraic["enabled"] = _as_bool(amoraic.get("enabled"), True)
    amoraic["question_count"] = _clamp_int(amoraic.get("question_count"), 5)

    chavrusa = merged.get("chavrusa")
    if not isinstance(chavrusa, dict):
        chavrusa = deepcopy(DEFAULT_TALMUDIC_HARNESS_CONFIG["chavrusa"])
        merged["chavrusa"] = chavrusa
    chavrusa["enabled"] = _as_bool(chavrusa.get("enabled"), False)
    chavrusa["consensus_required"] = _as_bool(chavrusa.get("consensus_required"), False)
    chavrusa["proposer_model"] = str(chavrusa.get("proposer_model") or "").strip()
    chavrusa["proposer_provider"] = str(chavrusa.get("proposer_provider") or "").strip()
    chavrusa["challenger_model"] = str(chavrusa.get("challenger_model") or "").strip()
    chavrusa["challenger_provider"] = str(
        chavrusa.get("challenger_provider") or ""
    ).strip()

    teaching_friend = merged.get("teaching_friend")
    if not isinstance(teaching_friend, dict):
        teaching_friend = deepcopy(DEFAULT_TALMUDIC_HARNESS_CONFIG["teaching_friend"])
        merged["teaching_friend"] = teaching_friend
    teaching_friend["enabled"] = _as_bool(teaching_friend.get("enabled"), False)
    teaching_friend["temperature"] = _clamp_int(
        teaching_friend.get("temperature"), 0, 0, 2
    )

    eduyot = merged.get("eduyot")
    if not isinstance(eduyot, dict):
        eduyot = deepcopy(DEFAULT_TALMUDIC_HARNESS_CONFIG["eduyot"])
        merged["eduyot"] = eduyot
    eduyot["enabled"] = _as_bool(eduyot.get("enabled"), True)
    eduyot["retain_rejected_branches"] = _as_bool(
        eduyot.get("retain_rejected_branches"), True
    )
    return merged


def build_talmudic_harness_prompt_guidance(
    config: Dict[str, Any] | None,
) -> str:
    """Build guidance containing only actions enabled in config."""

    harness_config = normalize_harness_config(config)
    if not harness_config["enabled"] or not harness_config["prompt_guidance"]:
        return ""

    guidance = [
        "Talmudic AI Harness: use explicit logical signposts for hard reasoning tasks."
    ]
    if harness_config["amoraic"]["enabled"]:
        guidance.append(
            "Start with a kushya by calling "
            'talmudic_harness(action="refine_question") when the best next '
            "question is unclear."
        )
    if harness_config["chavrusa"]["enabled"]:
        guidance.append(
            "Use Chavrusa structure for contested solution paths: keep a proposer "
            "and challenger isolated, compare their claims, and only then converge."
        )
    if harness_config["teaching_friend"]["enabled"]:
        guidance.append(
            "Use the Teaching Friend check to restate the answer in plain English "
            "and detect skipped logical steps."
        )
    if (
        harness_config["eduyot"]["enabled"]
        and harness_config["eduyot"]["retain_rejected_branches"]
    ):
        guidance.append(
            "Preserve Eduyot as compact rejected or minority branches with reasons."
        )
    return " ".join(guidance)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _question_templates(task: str, context: str) -> List[Dict[str, Any]]:
    task_phrase = task or "the task"
    context_clause = "given the supplied context" if context else "before acting"
    return [
        {
            "question": f"What exact constraint would most change the answer to {task_phrase}?",
            "signpost": "kushya",
            "score": 9,
            "rationale": "Maximizes disambiguation before tool use or implementation.",
        },
        {
            "question": f"Which existing Hermes primitive should be reused for {task_phrase} {context_clause}?",
            "signpost": "teretz_candidate",
            "score": 8,
            "rationale": "Reduces architectural drift by preferring existing tools, skills, and hooks.",
        },
        {
            "question": f"What failure mode would make the proposed approach to {task_phrase} unsafe or misleading?",
            "signpost": "kushya",
            "score": 7,
            "rationale": "Surfaces adversarial objections before convergence.",
        },
        {
            "question": f"What evidence or test would prove the answer to {task_phrase} is grounded?",
            "signpost": "teretz_candidate",
            "score": 6,
            "rationale": "Converts reasoning into a verifiable next step.",
        },
        {
            "question": f"Which rejected branch for {task_phrase} should be retained as a minority opinion?",
            "signpost": "eduyot",
            "score": 5,
            "rationale": "Preserves useful non-winning reasoning for future context shifts.",
        },
        {
            "question": f"How would a plain-English Teaching Friend explain the next step for {task_phrase}?",
            "signpost": "teaching_friend",
            "score": 4,
            "rationale": "Checks whether the reasoning can be taught without hidden leaps.",
        },
        {
            "question": f"What user-facing assumption must be stated before resolving {task_phrase}?",
            "signpost": "kushya",
            "score": 3,
            "rationale": "Avoids silent assumptions when ambiguity remains.",
        },
    ]


def build_amoraic_refinement(
    task: str,
    context: str = "",
    question_count: int = 5,
) -> Dict[str, Any]:
    """Return a ranked question matrix and the optimal question, Q_opt."""

    clean_task = _clean_text(task)
    if not clean_task:
        raise ValueError("task is required")
    clean_context = _clean_text(context)
    count = _clamp_int(question_count, 5)
    matrix = _question_templates(clean_task, clean_context)[:count]
    matrix = sorted(matrix, key=lambda item: item["score"], reverse=True)
    return {
        "stage": "amoraic_refinement",
        "signpost": "kushya",
        "task": clean_task,
        "context": clean_context,
        "q_opt": matrix[0]["question"],
        "question_matrix": matrix,
        "next_instruction": "Answer Q_opt before producing the final response or implementation plan.",
    }


def build_chavrusa_brief(
    task: str,
    proposed_solution: str,
    context: str = "",
) -> Dict[str, Any]:
    """Build isolated proposer and challenger briefs for subagent debate."""

    clean_task = _clean_text(task)
    clean_solution = _clean_text(proposed_solution)
    if not clean_task:
        raise ValueError("task is required")
    if not clean_solution:
        raise ValueError("proposed_solution is required")
    return {
        "stage": "chavrusa",
        "task": clean_task,
        "proposed_solution": clean_solution,
        "context": _clean_text(context),
        "isolation_rule": "Run proposer and challenger with strict isolation; do not share hidden session context between them.",
        "roles": {
            "proposer": {
                "stance": "for",
                "instructions": "Build the strongest logical scaffolding for the proposed solution. Identify evidence, prerequisites, and tests.",
            },
            "challenger": {
                "stance": "against",
                "instructions": "Argue the inverse hypothesis. Find contradictions, missing constraints, unsafe assumptions, and cheaper alternatives.",
            },
        },
        "convergence_rule": "Compare claims, evidence, and unresolved disputes before adopting a teretz.",
    }


def build_teaching_friend_request(
    task: str, answer: str, context: str = ""
) -> Dict[str, Any]:
    """Build a zero-temperature plain-English verifier request."""

    clean_task = _clean_text(task)
    clean_answer = _clean_text(answer)
    if not clean_task:
        raise ValueError("task is required")
    if not clean_answer:
        raise ValueError("answer is required")
    return {
        "stage": "teaching_friend",
        "task": clean_task,
        "answer": clean_answer,
        "context": _clean_text(context),
        "verifier_role": "plain_english_friend",
        "temperature": 0,
        "checks": [
            "Identify any skipped logical step.",
            "Rewrite the core claim in plain English.",
            "Name the weakest assumption.",
            "State one verification action the main agent should run before finalizing.",
        ],
    }


def build_eduyot_entry(
    task: str,
    rejected_branch: str,
    reason: str,
    resurrect_when: str = "",
    evidence: Iterable[str] | None = None,
) -> Dict[str, Any]:
    """Create a compact rejected-branch ledger entry."""

    clean_task = _clean_text(task)
    clean_branch = _clean_text(rejected_branch)
    clean_reason = _clean_text(reason)
    if not clean_task:
        raise ValueError("task is required")
    if not clean_branch:
        raise ValueError("rejected_branch is required")
    if not clean_reason:
        raise ValueError("reason is required")
    return {
        "stage": "eduyot",
        "status": "rejected_minority_opinion",
        "task": clean_task,
        "rejected_branch": clean_branch,
        "reason": clean_reason,
        "resurrect_when": _clean_text(resurrect_when),
        "evidence": [
            str(item).strip() for item in (evidence or []) if str(item).strip()
        ],
    }
