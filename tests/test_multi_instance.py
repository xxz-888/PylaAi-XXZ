import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import utils
from gui import instance_config
from gui.instance_registry import build_manifest, write_manifest, list_instances, remove_manifest
from runtime_control import STOP_REQUESTED, read_state, write_state


class MultiInstanceTests(unittest.TestCase):
    def setUp(self):
        instance_config.set_active_instance(None)
        utils.clear_toml_cache()

    def test_instance_config_creates_queue_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            resolver = lambda p: str(root / p)
            with patch("gui.instance_config.resolve_project_path", side_effect=resolver), \
                    patch("utils.resolve_project_path", side_effect=resolver):
                instance_config.set_multi_instance_enabled(True)
                profile = instance_config.upsert_instance_profile("test-1", {
                    "name": "Test 1",
                    "emulator": "ldplayer",
                    "emulator_port": 5555,
                })

                self.assertEqual(profile["id"], "test-1")
                self.assertTrue((root / profile["queue_path"]).exists())

    def test_manifest_lists_running_instance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_path = root / "runtime.state"
            write_state(state_path, STOP_REQUESTED)
            resolver = lambda p: str(root / p)
            with patch("gui.instance_config.resolve_project_path", side_effect=resolver), \
                    patch("utils.resolve_project_path", side_effect=resolver), \
                    patch("gui.instance_registry.MANIFEST_DIR", str(root / "logs" / "instances")):
                instance_config.set_multi_instance_enabled(True)
                instance_config.upsert_instance_profile("default", {"name": "Default"})
                write_manifest("default", build_manifest("default", state_path=state_path, metrics_path=""))

                items = list_instances()

                self.assertEqual(items[0]["id"], "default")
                self.assertTrue(items[0]["running"])
                self.assertEqual(read_state(state_path), STOP_REQUESTED)
                remove_manifest("default")

    def test_resolve_ldplayer_instance_by_name(self):
        completed = type("Completed", (), {
            "returncode": 0,
            "stdout": "0,Main,,,,\n1,Farm Account,,,,\n",
        })()
        with patch("gui.instance_config._ldplayer_console_path", return_value="dnconsole.exe"), \
                patch("gui.instance_config.subprocess.run", return_value=completed):
            resolved = instance_config.resolve_emulator_instance("ldplayer", "Farm Account")

        self.assertEqual(resolved["name"], "Farm Account")
        self.assertEqual(resolved["emulator_port"], 5557)
        self.assertEqual(resolved["emulator_profile_index"], "1")

    def test_resolve_mumu_instance_by_name(self):
        completed = type("Completed", (), {
            "returncode": 0,
            "stdout": '{"0": {"index": 0, "name": "Main"}, "2": {"index": 2, "name": "Farm", "adb_port": 16448}}',
        })()
        with patch("gui.instance_config._mumu_manager_path", return_value="MuMuManager.exe"), \
                patch("gui.instance_config.subprocess.run", return_value=completed):
            resolved = instance_config.resolve_emulator_instance("mumu", "Farm")

        self.assertEqual(resolved["name"], "Farm")
        self.assertEqual(resolved["emulator_port"], 16448)
        self.assertEqual(resolved["emulator_profile_index"], "2")

    def test_resolve_instance_accepts_adb_serial(self):
        resolved = instance_config.resolve_emulator_instance("ldplayer", "127.0.0.1:5559")

        self.assertEqual(resolved["emulator_port"], 5559)
        self.assertEqual(resolved["emulator_profile_index"], "2")

    def test_list_available_emulator_instances_combines_ldplayer_and_mumu(self):
        ld_completed = type("Completed", (), {
            "returncode": 0,
            "stdout": "0,Main,,,,\n",
        })()
        mumu_completed = type("Completed", (), {
            "returncode": 0,
            "stdout": '{"1": {"index": 1, "name": "Mu Farm", "adb_port": 16416}}',
        })()

        def fake_run(command, **_kwargs):
            if "list2" in command:
                return ld_completed
            return mumu_completed

        with patch("gui.instance_config._ldplayer_console_path", return_value="dnconsole.exe"), \
                patch("gui.instance_config._mumu_manager_path", return_value="MuMuManager.exe"), \
                patch("gui.instance_config.subprocess.run", side_effect=fake_run):
            available = instance_config.list_available_emulator_instances()

        self.assertEqual(
            [(item["emulator"], item["name"]) for item in available],
            [("ldplayer", "Main"), ("mumu", "Mu Farm")],
        )


if __name__ == "__main__":
    unittest.main()
