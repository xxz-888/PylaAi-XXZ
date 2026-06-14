from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import TextIO

from gui.instance_config import (
    MAX_INSTANCES,
    find_port_collision,
    get_instance_profile,
    is_multi_instance_enabled,
    list_instance_profiles,
)
from gui.instance_registry import list_instances, read_manifest, resolve_instance
from gui.window_arranger import arrange_emulator_windows
from runtime_control import (
    PAUSED,
    RUNNING,
    STOP_REQUESTED,
    process_is_alive,
    read_state,
    write_state,
)


class InstanceSupervisor:
    def __init__(self, project_root: str | Path | None = None):
        self.project_root = Path(project_root or Path(__file__).resolve().parent.parent)
        self._processes: dict[str, subprocess.Popen] = {}
        self._log_handles: dict[str, TextIO] = {}

    def _python_cmd(self, instance_id: str) -> list[str]:
        return [sys.executable, str(self.project_root / "main.py"), "--instance", instance_id]

    def _worker_env(self, active_count: int, *, remote_control_owner: bool = False) -> dict[str, str]:
        env = dict(os.environ)
        env["PYLA_ACTIVE_INSTANCE_COUNT"] = str(max(1, min(MAX_INSTANCES, int(active_count))))
        env["PYLA_HEADLESS_CONTROL"] = "1"
        env["PYLA_REMOTE_CONTROL_OWNER"] = "1" if remote_control_owner else "0"
        env.setdefault("OMP_NUM_THREADS", "2")
        env.setdefault("OPENBLAS_NUM_THREADS", "2")
        env.setdefault("MKL_NUM_THREADS", "2")
        env.setdefault("NUMEXPR_NUM_THREADS", "2")
        return env

    def _log_path(self, instance_id: str) -> Path:
        return self.project_root / "logs" / "instances" / f"{instance_id}.log"

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

    def start_instance(
            self,
            instance_id: str,
            *,
            active_count: int | None = None,
            remote_control_owner: bool | None = None,
    ) -> tuple[bool, str]:
        ok, message = self.validate_start(instance_id)
        if not ok:
            return False, message

        running_count = sum(1 for item in list_instances() if item.get("running"))
        active_count = int(active_count or (running_count + 1))
        if remote_control_owner is None:
            remote_control_owner = running_count == 0
        log_path = self._log_path(instance_id)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_handle = log_path.open("a", encoding="utf-8", buffering=1)
        log_handle.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Launcher starting instance.\n")

        creation_flags = 0
        if sys.platform == "win32":
            creation_flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            creation_flags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            process = subprocess.Popen(
                self._python_cmd(instance_id),
                cwd=str(self.project_root),
                env=self._worker_env(active_count, remote_control_owner=remote_control_owner),
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                creationflags=creation_flags,
                close_fds=True,
            )
        except Exception:
            log_handle.close()
            raise

        self._processes[instance_id] = process
        self._log_handles[instance_id] = log_handle
        return True, f"Started '{instance_id}' (PID {process.pid})."

    def start_all(self) -> tuple[bool, str]:
        profiles = [item for item in list_instance_profiles() if item.get("enabled", True)]
        if not profiles:
            return False, "No enabled instances are configured."
        if len(profiles) > MAX_INSTANCES:
            return False, f"Only {MAX_INSTANCES} instances can run at once."

        results = []
        target_count = len(profiles)
        remote_owner_assigned = any(item.get("running") for item in list_instances())
        for profile in profiles:
            if resolve_instance(profile["id"]) and resolve_instance(profile["id"]).get("running"):
                continue
            ok, message = self.start_instance(
                profile["id"],
                active_count=target_count,
                remote_control_owner=not remote_owner_assigned,
            )
            results.append((ok, message))
            if ok:
                remote_owner_assigned = True

        started = [message for ok, message in results if ok]
        failed = [message for ok, message in results if not ok]
        if not started and not failed:
            return True, "All configured instances are already running."
        summary = f"Started {len(started)} instance{'s' if len(started) != 1 else ''}."
        if failed:
            summary += " Failed: " + " | ".join(failed)
        if started:
            self.align_windows(wait_seconds=3.0)
        return bool(started) or not failed, summary

    def align_windows(self, wait_seconds: float = 0.0) -> tuple[bool, str]:
        try:
            instances = list_instances()
            running = sum(1 for item in instances if item.get("running"))
            count = arrange_emulator_windows(
                max_windows=running or len(instances) or None,
                wait_seconds=wait_seconds,
            )
        except Exception as exc:
            return False, f"Could not align emulator windows: {exc}"
        if count <= 0:
            return False, "No emulator windows found to align."
        return True, f"Aligned {count} emulator window{'s' if count != 1 else ''}."

    def set_instance_state(self, instance_id: str, state: str) -> tuple[bool, str]:
        if state not in {RUNNING, PAUSED, STOP_REQUESTED}:
            return False, f"Unsupported runtime state: {state}"
        live = resolve_instance(instance_id)
        if not live or not live.get("running"):
            return False, f"Instance '{instance_id}' is not running."
        state_path = str(live.get("state_path") or "")
        if not state_path:
            return False, f"Instance '{instance_id}' has not published its control path yet."
        write_state(state_path, state)
        label = "resumed" if state == RUNNING else "paused" if state == PAUSED else "stopping"
        return True, f"Instance '{instance_id}' is {label}."

    def pause_instance(self, instance_id: str) -> tuple[bool, str]:
        return self.set_instance_state(instance_id, PAUSED)

    def resume_instance(self, instance_id: str) -> tuple[bool, str]:
        return self.set_instance_state(instance_id, RUNNING)

    def set_all_state(self, state: str) -> tuple[bool, str]:
        running = [item for item in list_instances() if item.get("running")]
        if not running:
            return False, "No instances are running."
        changed = 0
        failures = []
        for item in running:
            ok, message = self.set_instance_state(item["id"], state)
            if ok:
                changed += 1
            else:
                failures.append(message)
        action = "resumed" if state == RUNNING else "paused"
        summary = f"{action.title()} {changed} instance{'s' if changed != 1 else ''}."
        if failures:
            summary += " " + " | ".join(failures)
        return changed > 0, summary

    def _close_process_resources(self, instance_id: str) -> None:
        self._processes.pop(instance_id, None)
        handle = self._log_handles.pop(instance_id, None)
        if handle:
            try:
                handle.close()
            except OSError:
                pass

    @staticmethod
    def _force_stop_pid(pid: int) -> None:
        if not pid or not process_is_alive(pid):
            return
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            return
        try:
            os.kill(pid, 15)
        except OSError:
            pass

    def stop_instance(self, instance_id: str, *, timeout: float = 20.0) -> tuple[bool, str]:
        live = resolve_instance(instance_id)
        if not live or not live.get("running"):
            self._close_process_resources(instance_id)
            return True, f"Instance '{instance_id}' is already stopped."

        state_path = str(live.get("state_path") or "")
        if state_path:
            write_state(state_path, STOP_REQUESTED)
        pid = int(live.get("pid") or 0)
        process = self._processes.get(instance_id)
        deadline = time.time() + max(0.5, timeout)
        while time.time() < deadline:
            if process and process.poll() is not None:
                break
            if pid and not process_is_alive(pid):
                break
            time.sleep(0.25)

        if pid and process_is_alive(pid):
            self._force_stop_pid(pid)
        self._close_process_resources(instance_id)
        if pid and process_is_alive(pid):
            return False, f"Instance '{instance_id}' did not stop in time."
        return True, f"Stopped instance '{instance_id}'."

    def stop_all(self, *, timeout: float = 20.0) -> tuple[bool, str]:
        running = [item for item in list_instances() if item.get("running")]
        if not running:
            return True, "All instances are already stopped."

        for item in running:
            state_path = str(item.get("state_path") or "")
            if state_path:
                write_state(state_path, STOP_REQUESTED)

        deadline = time.time() + max(0.5, timeout)
        remaining = {item["id"]: int(item.get("pid") or 0) for item in running}
        while remaining and time.time() < deadline:
            remaining = {
                instance_id: pid
                for instance_id, pid in remaining.items()
                if pid and process_is_alive(pid)
            }
            if remaining:
                time.sleep(0.25)

        for instance_id, pid in remaining.items():
            self._force_stop_pid(pid)
            self._close_process_resources(instance_id)
        for item in running:
            self._close_process_resources(item["id"])

        still_running = [pid for pid in remaining.values() if process_is_alive(pid)]
        if still_running:
            return False, f"{len(still_running)} instances could not be stopped."
        return True, f"Stopped {len(running)} instance{'s' if len(running) != 1 else ''}."

    def restart_instance(self, instance_id: str) -> tuple[bool, str]:
        ok, message = self.stop_instance(instance_id)
        if not ok:
            return False, message
        return self.start_instance(instance_id)

    def list_status(self) -> list[dict]:
        statuses = []
        for item in list_instances():
            manifest = read_manifest(item["id"]) or {}
            process = self._processes.get(item["id"])
            pid = manifest.get("pid") or (process.pid if process and process.poll() is None else None)
            running = bool(pid and process_is_alive(int(pid)))
            runtime_control_state = read_state(item.get("state_path", "")) if running else ""
            statuses.append({
                **item,
                "pid": pid,
                "running": running,
                "paused": runtime_control_state == PAUSED,
                "control_state": runtime_control_state,
                "log_path": str(self._log_path(item["id"])),
            })
        return statuses

    def close(self, *, stop_workers: bool = False) -> None:
        if stop_workers:
            self.stop_all()
        for instance_id in list(self._log_handles):
            self._close_process_resources(instance_id)


_DEFAULT_SUPERVISOR: InstanceSupervisor | None = None


def get_instance_supervisor() -> InstanceSupervisor:
    global _DEFAULT_SUPERVISOR
    if _DEFAULT_SUPERVISOR is None:
        _DEFAULT_SUPERVISOR = InstanceSupervisor()
    return _DEFAULT_SUPERVISOR


def _queue_has_data(path: Path) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(data, list) and bool(data)
