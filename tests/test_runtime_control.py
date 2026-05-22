import unittest
from pathlib import Path


class RuntimeControlWindowTests(unittest.TestCase):
    def test_pause_window_has_custom_minimize_button(self):
        source = Path("runtime_control.py").read_text(encoding="utf-8")

        self.assertIn("def on_minimize", source)
        self.assertIn("root.iconify()", source)
        self.assertIn('root.bind("<Map>", restore_chrome)', source)
        self.assertIn('text="-"', source)


if __name__ == "__main__":
    unittest.main()
