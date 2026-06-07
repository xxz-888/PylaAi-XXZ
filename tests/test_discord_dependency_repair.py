import unittest
from pathlib import Path

import dependency_repair


class DiscordDependencyRepairTest(unittest.TestCase):
    def test_runtime_pin_uses_known_discord_py_package(self):
        self.assertEqual(dependency_repair.DISCORD_RUNTIME_REQUIREMENT, "discord.py==2.4.0")
        self.assertIn("discord", dependency_repair.DISCORD_CONFLICT_PACKAGES)
        self.assertIn("py-cord", dependency_repair.DISCORD_CONFLICT_PACKAGES)

    def test_startup_runs_repair_before_discord_control_import(self):
        source = Path("main.py").read_text(encoding="utf-8")

        repair_index = source.index("repair_discord_runtime_before_import()")
        discord_control_index = source.index("from discord_control import DiscordControlServer")

        self.assertLess(repair_index, discord_control_index)

    def test_setup_and_gpu_tool_use_same_discord_runtime(self):
        setup_source = Path("setup.py").read_text(encoding="utf-8")
        gpu_tool_source = Path("tools/fix_gpu_runtime.py").read_text(encoding="utf-8")

        self.assertIn("DISCORD_RUNTIME_REQUIREMENT", setup_source)
        self.assertIn("repair_discord_runtime(restart=False)", setup_source)
        self.assertIn("DISCORD_RUNTIME_REQUIREMENT", gpu_tool_source)
        self.assertIn("repair_discord_runtime(restart=False)", gpu_tool_source)


if __name__ == "__main__":
    unittest.main()
