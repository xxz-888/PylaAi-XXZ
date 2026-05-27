from __future__ import annotations

import subprocess
import sys
import time
import json
from pathlib import Path

from gui.instance_config import (
    find_port_collision,
    get_instance_profile,
    is_multi_instance_enabled,
)
from gui.instance_registry import list_instances, read_manifest, resolve_instance
from gui.window_arranger import arrange_emulator_windows
from runtime_control import STOP_REQUESTED, process_is_alive, write_state


class InstanceSupervisor:
    def __init__(self, project_root: str | Path | None = None):
        self.project_root = Path(project_root or Path(__file__).resolve().parent.parent)
        self._processes: dict[str, subprocess.Popen] = {}

    def _python_cmd(self, instance_id: str) -> list[str]:
        return [sys.executable, str(self.project_root / "main.py"), "--instance", instance_id]

    def validate_start(self, instance_id: str) -> tuple[bool, str]:
        if not is_multi_instance_enabled():
            return False, "Multi-instance mode is disabled."
        profile = get_instance_profile(instance_id)
        if not profile:
            return False, f"Unknown instance '{instance_id}'."
        if not profile.get("enabled", True):
            return False, f"Instance '{instance_id}' is disabled."
        collision = find_port_collision(instance_id, profile["emulator_port"])
        if collision:
            return False, f"Port {profile['emulator_port']} is already used by instance '{collision}'."
        live = resolve_instance(instance_id)
        if live and live.get("running"):
            return False, f"Instance '{instance_id}' is already running."
        queue_path = self.project_root / str(profile.get("queue_path", ""))
        if not queue_path.exists() or not _queue_has_data(queue_path):
            default_queue = self.project_root / "latest_brawler_data.json"
            if default_queue.exists() and _queue_has_data(default_queue):
                queue_path.parent.mkdir(parents=True, exist_ok=True)
                queue_path.write_text(default_queue.read_text(encoding="utf-8"), encoding="utf-8")
            else:
                return False, (
                    f"Instance '{instance_id}' has no brawler queue yet. "
                    "Pick brawlers or use Push All once, then start the instance."
                )
        return True, "OK"

    def start_instance(self, instance_id: str) -> tuple[bool, str]:
        ok, message = self.validate_start(instance_id)
        if not ok:
            return False, message
        process = subprocess.Popen(
            self._python_cmd(instance_id),
            cwd=str(self.project_root),
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if sys.platform == "win32" else 0,
        )
        self._processes[instance_id] = process
        self.align_windows(wait_seconds=2.0)
        return True, f"Started instance '{instance_id}' (PID {process.pid})."

    def align_windows(self, wait_seconds: float = 0.0) -> tuple[bool, str]:
        try:
            configured = len(list_instances())
            count = arrange_emulator_windows(max_windows=configured or None, wait_seconds=wait_seconds)
        except Exception as exc:
            return False, f"Could not align emulator windows: {exc}"
        if count <= 0:
            return False, "No emulator windows found to align."
        return True, f"Aligned {count} emulator window{'s' if count != 1 else ''}."

    def stop_instance(self, instance_id: str, *, timeout: float = 20.0) -> tuple[bool, str]:
        live = resolve_instance(instance_id)
        state_path = live.get("state_path") if live else ""
        if state_path:
            write_state(state_path, STOP_REQUESTED)
        process = self._processes.get(instance_id)
        if process and process.poll() is None:
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
        elif live and live.get("pid"):
            deadline = time.time() + timeout
            while time.time() < deadline:
                if not process_is_alive(int(live["pid"])):
                    break
                time.sleep(0.5)
        self._processes.pop(instance_id, None)
        if live and live.get("pid") and process_is_alive(int(live["pid"])):
            return False, f"Instance '{instance_id}' did not stop in time."
        return True, f"Stop requested for instance '{instance_id}'."

    def restart_instance(self, instance_id: str) -> tuple[bool, str]:
        ok, message = self.stop_instance(instance_id)
        if not ok and "did not stop" in message:
            return False, message
        return self.start_instance(instance_id)

    def list_status(self) -> list[dict]:
        statuses = []
        for item in list_instances():
            manifest = read_manifest(item["id"]) or {}
            process = self._processes.get(item["id"])
            pid = manifest.get("pid") or (process.pid if process and process.poll() is None else None)
            statuses.append({
                **item,
                "pid": pid,
                "running": bool(pid and process_is_alive(int(pid))),
            })
        return statuses


def _queue_has_data(path: Path) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(data, list) and bool(data)
