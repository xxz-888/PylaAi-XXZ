import json
import os
import time
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parent


def metrics_path_for_pid(pid=None):
    pid = os.getpid() if pid is None else pid
    return project_root() / "logs" / f"runtime_metrics_{pid}.json"


def _write_metrics_text(path, text):
    path = Path(path)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(text, encoding="utf-8")
    try:
        os.replace(temp_path, path)
        return
    except OSError:
        pass
    try:
        path.write_text(text, encoding="utf-8")
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass


def write_metrics(path, ips, feed_fps, history, max_samples=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    samples = list(history)
    if max_samples is not None and max_samples > 0:
        samples = samples[-max_samples:]
    payload = {
        "ips": float(ips),
        "feed_fps": float(feed_fps),
        "history": [float(v) for v in samples],
    }
    text = json.dumps(payload)
    for attempt in range(3):
        try:
            _write_metrics_text(path, text)
            return
        except OSError:
            if attempt == 2:
                return
            time.sleep(0.02 * (attempt + 1))


def read_metrics(path):
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    history = data.get("history")
    if not isinstance(history, list):
        history = []
    try:
        ips = float(data.get("ips", 0.0))
        feed_fps = float(data.get("feed_fps", 0.0))
        history = [float(v) for v in history]
    except (TypeError, ValueError):
        return None
    return {"ips": ips, "feed_fps": feed_fps, "history": history}


def delete_metrics(path):
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        pass
