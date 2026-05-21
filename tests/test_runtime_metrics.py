import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from runtime_control import draw_ips_sparkline
from runtime_metrics import metrics_path_for_pid, read_metrics, write_metrics


class RuntimeMetricsTests(unittest.TestCase):
    def test_metrics_path_for_pid(self):
        path = metrics_path_for_pid(12345)
        self.assertEqual(path.name, "runtime_metrics_12345.json")
        self.assertEqual(path.parent.name, "logs")

    def test_write_read_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "metrics.json"
            history = [10.0, 12.5, 11.0, 13.2]
            write_metrics(path, 13.2, 28.0, history)
            data = read_metrics(path)
            self.assertIsNotNone(data)
            self.assertAlmostEqual(data["ips"], 13.2)
            self.assertAlmostEqual(data["feed_fps"], 28.0)
            self.assertEqual(data["history"], history)

    def test_write_falls_back_when_replace_is_locked(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "metrics.json"
            write_metrics(path, 9.0, 20.0, [9.0])
            original_replace = os.replace

            def locked_replace(src, dst):
                if Path(dst) == path:
                    raise PermissionError(5, "Access is denied")
                return original_replace(src, dst)

            with patch("runtime_metrics.os.replace", side_effect=locked_replace):
                write_metrics(path, 11.5, 24.0, [9.0, 11.5])
            data = read_metrics(path)
            self.assertIsNotNone(data)
            self.assertAlmostEqual(data["ips"], 11.5)
            self.assertEqual(data["history"], [9.0, 11.5])

    def test_write_truncates_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "metrics.json"
            history = list(range(20))
            write_metrics(path, 19.0, 30.0, history, max_samples=5)
            data = read_metrics(path)
            self.assertEqual(data["history"], [15, 16, 17, 18, 19])

    def test_read_missing_returns_none(self):
        self.assertIsNone(read_metrics(Path("logs/does_not_exist_metrics.json")))

    def test_draw_ips_sparkline_handles_sample_counts(self):
        canvas = MagicMock()
        for samples in ([], [5.0], list(range(10))):
            draw_ips_sparkline(canvas, samples, "#30d158")
        self.assertTrue(canvas.delete.called)
        self.assertTrue(canvas.create_line.called)


if __name__ == "__main__":
    unittest.main()
