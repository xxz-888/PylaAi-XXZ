import tempfile
import unittest
import os
from pathlib import Path
from unittest.mock import patch

import utils
from gui import instance_config
from gui.instance_registry import build_manifest, write_manifest, list_instances, remove_manifest
from gui.window_arranger import compute_grid_rects, is_emulator_window_title
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
                    "player_tag": "#ABC123",
                })

                self.assertEqual(profile["id"], "test-1")
                self.assertEqual(profile["player_tag"], "#ABC123")
                self.assertTrue((root / profile["queue_path"]).exists())

    def test_active_instance_player_tag_overrides_global_api_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            resolver = lambda p: str(root / p)
            with patch("gui.instance_config.resolve_project_path", side_effect=resolver), \
                    patch("utils.resolve_project_path", side_effect=resolver), \
                    patch("config_paths.project_root", return_value=str(root)):
                cfg = root / "cfg"
                cfg.mkdir(exist_ok=True)
                (cfg / "general_config.toml").write_text("player_tag = \"#GLOBAL\"\n", encoding="utf-8")
                (cfg / "brawl_stars_api.toml").write_text("player_tag = \"#API\"\n", encoding="utf-8")
                instance_config.set_multi_instance_enabled(True)
                instance_config.upsert_instance_profile("instance-1", {
                    "name": "Instance 1",
                    "emulator": "ldplayer",
                    "emulator_port": 5555,
                    "player_tag": "#PLAYER1",
                })
                instance_config.set_active_instance("instance-1")
                utils.clear_toml_cache()

                self.assertEqual(utils.get_config_player_tag({}), "#PLAYER1")
                self.assertEqual(utils.load_brawl_stars_api_config()["player_tag"], "#PLAYER1")

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

    def test_window_arranger_builds_clean_grid(self):
        rects = compute_grid_rects(3, area=(0, 0, 1200, 800))

        self.assertEqual(len(rects), 3)
        self.assertEqual(rects[0][:2], (8, 8))
        self.assertGreater(rects[1][0], rects[0][0])
        self.assertGreater(rects[2][1], rects[0][1])

    def test_window_arranger_matches_emulator_titles(self):
        self.assertTrue(is_emulator_window_title("LDPlayer"))
        self.assertTrue(is_emulator_window_title("Android Device"))
        self.assertTrue(is_emulator_window_title("Brawl Stars"))
        self.assertFalse(is_emulator_window_title("Discord"))

    def test_supervisor_align_windows_reports_arranged_count(self):
        with patch("gui.instance_supervisor.list_instances", return_value=[{"id": "one"}, {"id": "two"}]), \
                patch("gui.instance_supervisor.arrange_emulator_windows", return_value=2) as arrange:
            from gui.instance_supervisor import InstanceSupervisor

            ok, message = InstanceSupervisor().align_windows()

        self.assertTrue(ok)
        self.assertIn("Aligned 2 emulator windows", message)
        arrange.assert_called_once_with(max_windows=2, wait_seconds=0.0)

    def test_instance_limit_is_eight(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            resolver = lambda p: str(root / p)
            with patch("gui.instance_config.resolve_project_path", side_effect=resolver), \
                    patch("utils.resolve_project_path", side_effect=resolver):
                instance_config.set_multi_instance_enabled(True)
                for index in range(instance_config.MAX_INSTANCES):
                    instance_config.upsert_instance_profile(f"slot-{index}", {
                        "name": f"Slot {index}",
                        "emulator": "mumu",
                        "emulator_port": 16384 + (32 * index),
                    })

                with self.assertRaisesRegex(ValueError, "at most 8"):
                    instance_config.upsert_instance_profile("slot-9", {
                        "name": "Slot 9",
                        "emulator": "mumu",
                        "emulator_port": 16640,
                    })

    def test_auto_resource_budget_scales_with_worker_count(self):
        self.assertEqual(instance_config.resource_budget("auto", 1)[0], "full")
        self.assertEqual(instance_config.resource_budget("auto", 4)[0], "balanced")
        name, budget = instance_config.resource_budget("auto", 8)
        self.assertEqual(name, "economy")
        self.assertEqual(budget["onnx_cpu_threads"], 1)
        self.assertEqual(budget["scrcpy_max_fps"], 24)

    def test_worker_environment_is_headless_and_bounded(self):
        from gui.instance_supervisor import InstanceSupervisor

        env = InstanceSupervisor()._worker_env(99, remote_control_owner=True)

        self.assertEqual(env["PYLA_HEADLESS_CONTROL"], "1")
        self.assertEqual(env["PYLA_ACTIVE_INSTANCE_COUNT"], "8")
        self.assertEqual(env["PYLA_REMOTE_CONTROL_OWNER"], "1")

    def test_apply_instance_overrides_uses_worker_resource_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            resolver = lambda p: str(root / p)
            cfg = root / "cfg"
            cfg.mkdir(parents=True)
            (cfg / "general_config.toml").write_text(
                'current_emulator = "LDPlayer"\nmax_ips = 0\n',
                encoding="utf-8",
            )
            (cfg / "brawl_stars_api.toml").write_text('player_tag = ""\n', encoding="utf-8")
            with patch("gui.instance_config.resolve_project_path", side_effect=resolver), \
                    patch("utils.resolve_project_path", side_effect=resolver), \
                    patch.dict(os.environ, {"PYLA_ACTIVE_INSTANCE_COUNT": "6"}, clear=False):
                instance_config.set_multi_instance_enabled(True)
                instance_config.upsert_instance_profile("farm", {
                    "name": "Farm",
                    "emulator": "mumu",
                    "emulator_port": 16384,
                    "resource_profile": "auto",
                })
                utils.clear_toml_cache()
                instance_config.apply_instance_overrides("farm")
                general = utils.load_toml_as_dict("cfg/general_config.toml")

        self.assertEqual(general["multi_instance_resource_profile"], "economy")
        self.assertEqual(general["onnx_cpu_threads"], 1)

    def test_pause_and_resume_write_worker_control_state(self):
        from gui.instance_supervisor import InstanceSupervisor
        from runtime_control import PAUSED, RUNNING

        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "worker.state"
            write_state(state_path, RUNNING)
            live = {
                "id": "farm",
                "running": True,
                "state_path": str(state_path),
                "pid": os.getpid(),
            }
            with patch("gui.instance_supervisor.resolve_instance", return_value=live):
                supervisor = InstanceSupervisor()
                self.assertTrue(supervisor.pause_instance("farm")[0])
                self.assertEqual(read_state(state_path), PAUSED)
                self.assertTrue(supervisor.resume_instance("farm")[0])
                self.assertEqual(read_state(state_path), RUNNING)

    def test_start_all_assigns_one_remote_control_owner(self):
        from gui.instance_supervisor import InstanceSupervisor

        profiles = [
            {"id": "one", "enabled": True},
            {"id": "two", "enabled": True},
            {"id": "three", "enabled": True},
        ]
        supervisor = InstanceSupervisor()
        starts = []

        def fake_start(instance_id, **kwargs):
            starts.append((instance_id, kwargs))
            return True, "started"

        with patch("gui.instance_supervisor.list_instance_profiles", return_value=profiles), \
                patch("gui.instance_supervisor.list_instances", return_value=[]), \
                patch("gui.instance_supervisor.resolve_instance", return_value=None), \
                patch.object(supervisor, "start_instance", side_effect=fake_start), \
                patch.object(supervisor, "align_windows", return_value=(True, "aligned")):
            ok, _ = supervisor.start_all()

        self.assertTrue(ok)
        self.assertEqual([item[1]["active_count"] for item in starts], [3, 3, 3])
        self.assertEqual(
            [item[1]["remote_control_owner"] for item in starts],
            [True, False, False],
        )


if __name__ == "__main__":
    unittest.main()
