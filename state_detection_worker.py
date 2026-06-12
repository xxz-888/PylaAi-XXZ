import threading
import time


class StateDetectionWorker:
    def __init__(self, detector, name="pyla-state-detector"):
        self.detector = detector
        self.name = name
        self._request_event = threading.Event()
        self._stop_event = threading.Event()
        self._request_lock = threading.Lock()
        self._result_lock = threading.Lock()
        self._detector_lock = threading.Lock()
        self._requested_frame = None
        self._requested_frame_id = -1
        self._result_sequence = 0
        self._latest_result = None
        self._thread = None

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name=self.name)
        self._thread.start()

    def request(self, frame, frame_id=-1):
        if frame is None:
            return
        with self._request_lock:
            self._requested_frame = frame
            self._requested_frame_id = frame_id
        self._request_event.set()

    def consume_latest(self, after_sequence=0):
        with self._result_lock:
            if self._latest_result is None or self._result_sequence <= after_sequence:
                return None
            return self._result_sequence, self._latest_result

    def detect_now(self, frame):
        with self._detector_lock:
            return self.detector(frame)

    def close(self, timeout=1.0):
        self._stop_event.set()
        self._request_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    def _take_request(self):
        with self._request_lock:
            frame = self._requested_frame
            frame_id = self._requested_frame_id
            self._requested_frame = None
            self._requested_frame_id = -1
        return frame, frame_id

    def _run(self):
        while not self._stop_event.is_set():
            self._request_event.wait(0.25)
            if self._stop_event.is_set():
                return
            if not self._request_event.is_set():
                continue
            self._request_event.clear()
            frame, frame_id = self._take_request()
            if frame is None:
                continue

            started_at = time.perf_counter()
            try:
                state = self.detect_now(frame)
            except Exception as exc:
                print(f"State detector worker failed: {exc}")
                continue

            result = {
                "state": state,
                "frame_id": frame_id,
                "finished_at": time.time(),
                "duration": time.perf_counter() - started_at,
            }
            with self._result_lock:
                self._result_sequence += 1
                self._latest_result = result
