from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "talmudic_harness_plugin_test"


def load_tool_module():
    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(ROOT)]
    sys.modules[PACKAGE] = package

    config_module = types.ModuleType("hermes_cli.config")
    setattr(
        config_module,
        "load_config",
        lambda: {
            "talmudic_harness": {
                "enabled": True,
                "chavrusa": {"enabled": True},
                "teaching_friend": {"enabled": True},
                "eduyot": {
                    "enabled": True,
                    "retain_rejected_branches": True,
                    "ledger_path": "talmudic_harness/eduyot.jsonl",
                },
            }
        },
    )
    sys.modules["hermes_cli"] = types.ModuleType("hermes_cli")
    sys.modules["hermes_cli.config"] = config_module

    constants = types.ModuleType("hermes_constants")
    setattr(
        constants,
        "get_hermes_home",
        lambda: Path(tempfile.gettempdir()) / "hermes-test-home",
    )
    sys.modules["hermes_constants"] = constants

    tools_package = types.ModuleType("tools")
    tools_package.__path__ = []
    delegate_module = types.ModuleType("tools.delegate_tool")

    def forbidden_delegate(*args, **kwargs):
        raise AssertionError("deterministic plugin actions must not spawn child agents")

    setattr(delegate_module, "delegate_task", forbidden_delegate)
    sys.modules["tools"] = tools_package
    sys.modules["tools.delegate_tool"] = delegate_module

    spec = importlib.util.spec_from_file_location(f"{PACKAGE}.tool", ROOT / "tool.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


TOOL = load_tool_module()


class ToolBehaviorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp())
        self.home_patch = patch.object(TOOL, "get_hermes_home", return_value=self.home)
        self.home_patch.start()
        self.addCleanup(self.home_patch.stop)

    def result(self, args):
        return json.loads(TOOL.talmudic_harness(args))

    def test_malformed_arguments_fail_closed(self) -> None:
        payload = json.loads(TOOL.talmudic_harness(None))
        self.assertEqual(payload["error"], "invalid_arguments")

    def test_disabled_global_gate_blocks_action(self) -> None:
        with patch.object(
            TOOL,
            "load_config",
            return_value={"talmudic_harness": {"enabled": False}},
        ):
            payload = self.result({"action": "refine_question", "task": "T"})
        self.assertEqual(payload["error"], "action_disabled")

    def test_chavrusa_returns_brief_without_spawning_children(self) -> None:
        payload = self.result(
            {
                "action": "chavrusa_brief",
                "task": "Choose a design",
                "proposed_solution": "Use a plugin",
            }
        )
        self.assertTrue(payload["success"])
        self.assertEqual(payload["result"]["executor"], "caller_managed")
        self.assertEqual(payload["result"]["roles"]["proposer"]["stance"], "for")
        self.assertEqual(payload["result"]["roles"]["challenger"]["stance"], "against")
        self.assertNotIn("delegate_result", payload["result"])

    def test_teaching_friend_returns_request_without_spawning_child(self) -> None:
        payload = self.result(
            {
                "action": "teaching_friend_request",
                "task": "Explain the design",
                "answer": "It is bounded.",
            }
        )
        self.assertTrue(payload["success"])
        self.assertEqual(payload["result"]["executor"], "caller_managed")
        self.assertNotIn("verifier_result", payload["result"])

    def test_eduyot_rejects_paths_outside_hermes_home(self) -> None:
        with patch.object(
            TOOL,
            "load_config",
            return_value={
                "talmudic_harness": {
                    "enabled": True,
                    "eduyot": {
                        "enabled": True,
                        "retain_rejected_branches": True,
                        "ledger_path": "/tmp/outside.jsonl",
                    },
                }
            },
        ):
            payload = self.result(
                {
                    "action": "eduyot_entry",
                    "task": "T",
                    "rejected_branch": "B",
                    "reason": "R",
                }
            )
        self.assertEqual(payload["error"], "invalid_ledger_path")

    def test_eduyot_rejects_relative_traversal(self) -> None:
        with patch.object(
            TOOL,
            "load_config",
            return_value={
                "talmudic_harness": {
                    "enabled": True,
                    "eduyot": {
                        "enabled": True,
                        "retain_rejected_branches": True,
                        "ledger_path": "../outside.jsonl",
                    },
                }
            },
        ):
            payload = self.result(
                {
                    "action": "eduyot_entry",
                    "task": "T",
                    "rejected_branch": "B",
                    "reason": "R",
                }
            )
        self.assertEqual(payload["error"], "invalid_ledger_path")

    def test_persistence_error_does_not_disclose_filesystem_details(self) -> None:
        with (
            patch.object(
                TOOL,
                "_append_jsonl",
                side_effect=OSError("failed at /private/operator/path"),
            ),
            patch.object(TOOL, "logger") as logger,
        ):
            payload = self.result(
                {
                    "action": "eduyot_entry",
                    "task": "T",
                    "rejected_branch": "B",
                    "reason": "R",
                }
            )
        self.assertEqual(payload["error"], "persistence_failed")
        self.assertNotIn("/private/operator/path", json.dumps(payload))
        logger.exception.assert_called_once_with("talmudic_harness persistence failed")

    def test_eduyot_persists_inside_home_without_disclosing_absolute_path(self) -> None:
        payload = self.result(
            {
                "action": "eduyot_entry",
                "task": "T",
                "rejected_branch": "B",
                "reason": "R",
            }
        )
        self.assertTrue(payload["success"])
        result = payload["result"]
        self.assertTrue(result["persisted"])
        self.assertEqual(result["ledger_path"], "talmudic_harness/eduyot.jsonl")
        ledger = self.home / result["ledger_path"]
        self.assertTrue(ledger.is_file())
        self.assertNotIn(str(self.home), json.dumps(payload))


if __name__ == "__main__":
    unittest.main()
