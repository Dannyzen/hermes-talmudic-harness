from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "talmudic_harness_primitives", ROOT / "harness.py"
)
assert SPEC is not None and SPEC.loader is not None
HARNESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HARNESS)


class PromptGuidanceDefaultsTest(unittest.TestCase):
    def test_enabling_harness_does_not_enable_prompt_guidance(self) -> None:
        config = HARNESS.normalize_harness_config({"enabled": True})

        self.assertFalse(config["prompt_guidance"])
        self.assertEqual(HARNESS.build_talmudic_harness_prompt_guidance(config), "")

    def test_prompt_guidance_remains_available_as_explicit_opt_in(self) -> None:
        config = HARNESS.normalize_harness_config(
            {"enabled": True, "prompt_guidance": True}
        )

        self.assertTrue(config["prompt_guidance"])
        guidance = HARNESS.build_talmudic_harness_prompt_guidance(config)
        self.assertIn("Talmudic AI Harness", guidance)
        self.assertIn("contested, irreversible", guidance)
        self.assertIn("does not spawn agents", guidance.lower())


class PrimitiveBehaviorTest(unittest.TestCase):
    def test_normalization_preserves_safe_defaults_and_overrides(self) -> None:
        config = HARNESS.normalize_harness_config(
            {
                "enabled": True,
                "amoraic": {"question_count": 3},
                "chavrusa": {"enabled": True},
            }
        )

        self.assertTrue(config["enabled"])
        self.assertFalse(config["prompt_guidance"])
        self.assertEqual(config["amoraic"]["question_count"], 3)
        self.assertTrue(config["amoraic"]["enabled"])
        self.assertTrue(config["chavrusa"]["enabled"])
        self.assertFalse(config["teaching_friend"]["enabled"])
        self.assertEqual(
            config["eduyot"]["ledger_path"],
            "~/.hermes/talmudic_harness/eduyot.jsonl",
        )

    def test_malformed_nested_sections_fall_back_to_safe_defaults(self) -> None:
        config = HARNESS.normalize_harness_config(
            {
                "enabled": True,
                "amoraic": [],
                "chavrusa": "invalid",
                "teaching_friend": None,
                "eduyot": 42,
            }
        )

        self.assertTrue(config["amoraic"]["enabled"])
        self.assertFalse(config["chavrusa"]["enabled"])
        self.assertFalse(config["teaching_friend"]["enabled"])
        self.assertTrue(config["eduyot"]["enabled"])

    def test_amoraic_refinement_returns_ranked_questions(self) -> None:
        result = HARNESS.build_amoraic_refinement(
            task="Choose a reasoning approach",
            context="Prefer existing Hermes primitives.",
            question_count=4,
        )

        self.assertEqual(result["stage"], "amoraic_refinement")
        self.assertEqual(result["signpost"], "kushya")
        self.assertEqual(len(result["question_matrix"]), 4)
        scores = [candidate["score"] for candidate in result["question_matrix"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual(result["question_matrix"][0]["question"], result["q_opt"])
        self.assertTrue(
            all("rationale" in candidate for candidate in result["question_matrix"])
        )

    def test_chavrusa_brief_keeps_roles_isolated(self) -> None:
        brief = HARNESS.build_chavrusa_brief(
            task="Choose a runtime design",
            proposed_solution="Use a user plugin.",
            context="Subagents do not share hidden context.",
        )

        self.assertEqual(brief["stage"], "chavrusa")
        self.assertEqual(brief["roles"]["proposer"]["stance"], "for")
        self.assertEqual(brief["roles"]["challenger"]["stance"], "against")
        self.assertIn("strict isolation", brief["isolation_rule"].lower())
        self.assertIn(
            "inverse hypothesis",
            brief["roles"]["challenger"]["instructions"].lower(),
        )

    def test_teaching_friend_request_is_plain_english_and_step_focused(self) -> None:
        request = HARNESS.build_teaching_friend_request(
            task="Explain deterministic tools",
            answer="Stable JSON makes behavior testable.",
        )

        self.assertEqual(request["stage"], "teaching_friend")
        self.assertEqual(request["verifier_role"], "plain_english_friend")
        self.assertEqual(request["temperature"], 0)
        self.assertTrue(
            any("skipped logical step" in check for check in request["checks"])
        )

    def test_eduyot_entry_retains_rejected_branch(self) -> None:
        entry = HARNESS.build_eduyot_entry(
            task="Choose persistence",
            rejected_branch="Store procedural doctrine in user memory",
            reason="User memory is bounded and not a procedure store.",
            resurrect_when="The user requests a compact durable reminder.",
        )

        self.assertEqual(entry["stage"], "eduyot")
        self.assertEqual(entry["status"], "rejected_minority_opinion")
        self.assertTrue(entry["rejected_branch"].startswith("Store procedural"))
        self.assertIn("resurrect_when", entry)


if __name__ == "__main__":
    unittest.main()
