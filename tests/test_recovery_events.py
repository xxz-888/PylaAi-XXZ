import tempfile
import unittest
from pathlib import Path

from recovery_events import log_recovery, read_recent_events


class RecoveryEventsTests(unittest.TestCase):
    def test_recovery_events_are_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "recovery_events.jsonl"

            log_recovery("scrcpy_restart", detail="feed stale", path=path)
            events = read_recent_events(path=path)

            self.assertEqual(events[0]["event_type"], "scrcpy_restart")
            self.assertEqual(events[0]["detail"], "feed stale")


if __name__ == "__main__":
    unittest.main()
