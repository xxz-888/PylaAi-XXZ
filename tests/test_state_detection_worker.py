import threading
import time
import unittest
from pathlib import Path

from state_detection_worker import StateDetectionWorker


class StateDetectionWorkerTests(unittest.TestCase):
    def test_request_runs_detector_off_calling_thread(self):
        caller_thread = threading.get_ident()
        detector_threads = []

        def detector(frame):
            detector_threads.append(threading.get_ident())
            return frame

        worker = StateDetectionWorker(detector)
        worker.start()
        try:
            worker.request("lobby", frame_id=7)
            deadline = time.time() + 1.0
            result = None
            while time.time() < deadline and result is None:
                result = worker.consume_latest()
                time.sleep(0.01)
        finally:
            worker.close()

        self.assertIsNotNone(result)
        _, payload = result
        self.assertEqual(payload["state"], "lobby")
        self.assertEqual(payload["frame_id"], 7)
        self.assertNotEqual(detector_threads[0], caller_thread)

    def test_consume_latest_only_returns_new_sequences(self):
        worker = StateDetectionWorker(lambda frame: frame)
        worker.start()
        try:
            worker.request("match", frame_id=3)
            deadline = time.time() + 1.0
            result = None
            while time.time() < deadline and result is None:
                result = worker.consume_latest()
                time.sleep(0.01)
            sequence, payload = result
            self.assertEqual(payload["state"], "match")
            self.assertIsNone(worker.consume_latest(after_sequence=sequence))
        finally:
            worker.close()

    def test_main_uses_worker_without_moving_context_guards(self):
        source = Path("main.py").read_text(encoding="utf-8")

        self.assertIn("StateDetectionWorker(get_state)", source)
        self.assertIn("self.state_detection_worker.request(", source)
        self.assertIn("self.handle_detected_state(result[\"state\"])", source)
        self.assertIn("self.apply_state_context_guard(detected_state, previous_state)", source)
        self.assertIn("self.state_detection_worker.close()", source)


if __name__ == "__main__":
    unittest.main()
