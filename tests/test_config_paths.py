import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import config_paths


class ConfigPathTests(unittest.TestCase):
    def setUp(self):
        config_paths._PROJECT_CFG_WRITABLE = None

    def tearDown(self):
        config_paths._PROJECT_CFG_WRITABLE = None

    def test_cfg_toml_moves_to_local_appdata_when_project_is_not_writable(self):
        with tempfile.TemporaryDirectory() as appdata:
            with patch.dict(os.environ, {"PYLAAI_FORCE_USER_CONFIG": "1", "LOCALAPPDATA": appdata}):
                resolved = Path(config_paths.resolve_project_path("cfg/bot_config.toml"))
                self.assertEqual(resolved.name, "bot_config.toml")
                self.assertIn("PylaAi-XXZ", resolved.parts)
                self.assertTrue(resolved.exists())

    def test_non_config_assets_stay_in_project_folder(self):
        with tempfile.TemporaryDirectory() as appdata:
            with patch.dict(os.environ, {"PYLAAI_FORCE_USER_CONFIG": "1", "LOCALAPPDATA": appdata}):
                resolved = Path(config_paths.resolve_project_path("cfg/brawlers_info.json"))

        self.assertEqual(resolved, Path(config_paths.project_root()) / "cfg" / "brawlers_info.json")


if __name__ == "__main__":
    unittest.main()
