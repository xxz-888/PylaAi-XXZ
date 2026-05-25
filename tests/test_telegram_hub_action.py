import unittest
from pathlib import Path


class TelegramHubActionTests(unittest.TestCase):
    def test_telegram_test_runs_in_background_thread(self):
        source = Path("gui/qml_hub.py").read_text(encoding="utf-8")

        self.assertIn('if action == "telegram-test":', source)
        self.assertIn("threading.Thread(target=send_test, daemon=True).start()", source)
        self.assertIn("Telegram test is sending in the background.", source)


if __name__ == "__main__":
    unittest.main()
