import tempfile
import unittest
from pathlib import Path

import utils
import config_paths
from gui import hub_state


class TomlRecoveryTests(unittest.TestCase):
    def setUp(self):
        utils.clear_toml_cache()

    def test_runtime_toml_decode_error_is_backed_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = root / "cfg"
            cfg.mkdir()
            history = cfg / "match_history.toml"
            history.write_text("'.bad", encoding="utf-8")

            original_root = utils.project_root
            original_config_root = config_paths.project_root
            try:
                utils.project_root = lambda: str(root)
                config_paths.project_root = lambda: str(root)
                config_paths._PROJECT_CFG_WRITABLE = None
                data = utils.load_toml_as_dict("cfg/match_history.toml")
            finally:
                utils.project_root = original_root
                config_paths.project_root = original_config_root
                config_paths._PROJECT_CFG_WRITABLE = None

            self.assertEqual(data, {})
            self.assertTrue(list(cfg.glob("match_history.toml.invalid-*")))

    def test_hub_state_uses_safe_toml_loader(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "match_history.toml"
            path.write_text("'.bad", encoding="utf-8")

            data = hub_state.load_toml_as_dict(str(path))

            self.assertEqual(data, {})
            self.assertTrue(list(Path(tmp).glob("match_history.toml.invalid-*")))


if __name__ == "__main__":
    unittest.main()
