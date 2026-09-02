from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "talmudic_harness_registration_test"


class FakeContext:
    def __init__(self) -> None:
        self.tools = []
        self.hooks = {}

    def register_tool(self, **kwargs) -> None:
        self.tools.append(kwargs)

    def register_hook(self, name, callback) -> None:
        self.hooks[name] = callback


def load_plugin(config):
    package_spec = importlib.util.spec_from_file_location(
        PACKAGE,
        ROOT / "__init__.py",
        submodule_search_locations=[str(ROOT)],
    )
    assert package_spec is not None and package_spec.loader is not None

    config_module = types.ModuleType("hermes_cli.config")
    setattr(config_module, "load_config", lambda: config)
    sys.modules["hermes_cli"] = types.ModuleType("hermes_cli")
    sys.modules["hermes_cli.config"] = config_module

    constants = types.ModuleType("hermes_constants")
    setattr(constants, "get_hermes_home", lambda: Path("/tmp/hermes-registration"))
    sys.modules["hermes_constants"] = constants

    module = importlib.util.module_from_spec(package_spec)
    sys.modules[PACKAGE] = module
    package_spec.loader.exec_module(module)
    return module


class PluginRegistrationTest(unittest.TestCase):
    def test_manifest_declares_current_hook_metadata(self) -> None:
        manifest = (ROOT / "plugin.yaml").read_text(encoding="utf-8")

        self.assertIn("version: 0.2.2", manifest)
        self.assertIn("Use for contested or irreversible decisions", manifest)
        self.assertIn("Does not spawn agents", manifest)
        self.assertIn("provides_hooks:\n  - pre_llm_call", manifest)
        self.assertNotIn("\nhooks:", manifest)

    def test_registers_tool_and_quiet_hook_by_default(self) -> None:
        plugin = load_plugin(
            {"talmudic_harness": {"enabled": True, "prompt_guidance": False}}
        )
        context = FakeContext()
        plugin.register(context)

        self.assertEqual([tool["name"] for tool in context.tools], ["talmudic_harness"])
        self.assertIn("pre_llm_call", context.hooks)
        self.assertIsNone(context.hooks["pre_llm_call"]())

    def test_prompt_hook_remains_explicitly_opt_in(self) -> None:
        plugin = load_plugin(
            {"talmudic_harness": {"enabled": True, "prompt_guidance": True}}
        )
        context = FakeContext()
        plugin.register(context)

        result = context.hooks["pre_llm_call"]()
        self.assertIsInstance(result, dict)
        self.assertIn("Talmudic AI Harness", result["context"])


if __name__ == "__main__":
    unittest.main()
