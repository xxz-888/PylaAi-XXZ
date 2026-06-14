from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path

from gui.instance_config import (
    MAX_INSTANCES,
    delete_instance_profile,
    list_available_emulator_instances,
    resolve_emulator_instance,
    set_instance_player_tag,
    set_instance_resource_profile,
    set_multi_instance_enabled,
    upsert_instance_profile,
)
from gui.instance_supervisor import get_instance_supervisor
from gui.qml_hub import configure_qt_startup, ensure_pyside6_available


def _available_instances() -> list[dict]:
    available = []
    for item in list_available_emulator_instances():
        available.append({
            **item,
            "label": (
                f"{item['display_emulator']} {item['index']}  |  "
                f"{item['name']}  |  ADB {item['adb_port']}"
            ),
        })
    return available


class MultiInstanceLauncher:
    def __init__(self, *, smoke_test: bool = False):
        if smoke_test:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        configure_qt_startup()
        ensure_pyside6_available()

        from PySide6.QtCore import QObject, QTimer, QUrl, Signal, Slot
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtQml import QQmlApplicationEngine

        set_multi_instance_enabled(True)
        supervisor = get_instance_supervisor()

        class LauncherBridge(QObject):
            actionFinished = Signal(str)

            @Slot(result=str)
            def stateJson(self):
                items = supervisor.list_status()
                payload = {
                    "instances": items,
                    "available": _available_instances(),
                    "configuredCount": len(items),
                    "runningCount": sum(1 for item in items if item.get("running")),
                    "pausedCount": sum(1 for item in items if item.get("paused")),
                    "maxInstances": MAX_INSTANCES,
                }
                return json.dumps(payload)

            def _emit_result(self, ok: bool, message: str):
                self.actionFinished.emit(json.dumps({"ok": bool(ok), "message": str(message)}))

            def _run_background(self, callback):
                def runner():
                    try:
                        ok, message = callback()
                    except Exception as exc:
                        ok, message = False, str(exc)
                    self._emit_result(ok, message)

                threading.Thread(target=runner, daemon=True).start()

            @Slot(str)
            def runAction(self, action):
                action = str(action or "")

                def execute():
                    if action == "start-all":
                        return supervisor.start_all()
                    if action == "pause-all":
                        from runtime_control import PAUSED

                        return supervisor.set_all_state(PAUSED)
                    if action == "resume-all":
                        from runtime_control import RUNNING

                        return supervisor.set_all_state(RUNNING)
                    if action == "stop-all":
                        return supervisor.stop_all()
                    if action == "align":
                        return supervisor.align_windows(wait_seconds=1.0)
                    if ":" not in action:
                        return False, f"Unknown launcher action: {action}"
                    operation, instance_id = action.split(":", 1)
                    if operation == "start":
                        return supervisor.start_instance(instance_id)
                    if operation == "pause":
                        return supervisor.pause_instance(instance_id)
                    if operation == "resume":
                        return supervisor.resume_instance(instance_id)
                    if operation == "restart":
                        return supervisor.restart_instance(instance_id)
                    if operation == "stop":
                        return supervisor.stop_instance(instance_id)
                    if operation == "delete":
                        if any(
                            item["id"] == instance_id and item.get("running")
                            for item in supervisor.list_status()
                        ):
                            return False, "Stop the instance before deleting it."
                        if not delete_instance_profile(instance_id):
                            return False, f"Unknown instance '{instance_id}'."
                        return True, f"Removed '{instance_id}'. Queue files were kept."
                    if operation == "log":
                        profile = next(
                            (item for item in supervisor.list_status() if item["id"] == instance_id),
                            None,
                        )
                        if not profile:
                            return False, f"Unknown instance '{instance_id}'."
                        log_path = Path(profile["log_path"])
                        log_path.parent.mkdir(parents=True, exist_ok=True)
                        log_path.touch(exist_ok=True)
                        if os.name == "nt":
                            os.startfile(log_path)  # type: ignore[attr-defined]
                        return True, f"Opened log for '{instance_id}'."
                    return False, f"Unknown launcher action: {operation}"

                self._run_background(execute)

            @Slot(str, str, str, result=str)
            def addInstance(self, selected_json, player_tag, resource_profile):
                try:
                    selected = json.loads(selected_json)
                    if not isinstance(selected, dict):
                        raise ValueError("Select an emulator instance first.")
                    current = supervisor.list_status()
                    if len(current) >= MAX_INSTANCES:
                        raise ValueError(f"Only {MAX_INSTANCES} instances can be configured.")
                    resolved = resolve_emulator_instance(
                        selected.get("emulator", ""),
                        selected.get("name", ""),
                    )
                    profile = upsert_instance_profile(resolved["name"], {
                        "name": resolved["name"],
                        "emulator": resolved["emulator"],
                        "emulator_port": resolved["emulator_port"],
                        "emulator_profile_index": resolved["emulator_profile_index"],
                        "emulator_instance_name": resolved["name"],
                        "player_tag": player_tag,
                        "resource_profile": resource_profile or "auto",
                    })
                    return json.dumps({
                        "ok": True,
                        "message": f"Added {profile['name']} in slot {profile['slot']}.",
                    })
                except Exception as exc:
                    return json.dumps({"ok": False, "message": str(exc)})

            @Slot(str, str, result=str)
            def savePlayerTag(self, instance_id, player_tag):
                try:
                    profile = set_instance_player_tag(instance_id, player_tag)
                    return json.dumps({
                        "ok": True,
                        "message": f"Saved player tag for {profile['name']}.",
                    })
                except Exception as exc:
                    return json.dumps({"ok": False, "message": str(exc)})

            @Slot(str, str, result=str)
            def saveResourceProfile(self, instance_id, resource_profile):
                try:
                    profile = set_instance_resource_profile(instance_id, resource_profile)
                    return json.dumps({
                        "ok": True,
                        "message": (
                            f"{profile['name']} will use {profile['resource_profile']} resources "
                            "on its next start."
                        ),
                    })
                except Exception as exc:
                    return json.dumps({"ok": False, "message": str(exc)})

        self.app = QGuiApplication.instance() or QGuiApplication(sys.argv)
        self.engine = QQmlApplicationEngine()
        self.bridge = LauncherBridge()
        self.engine.rootContext().setContextProperty("launcherBridge", self.bridge)
        qml_path = Path(__file__).resolve().parent / "qml" / "MultiInstanceLauncher.qml"
        self.engine.load(QUrl.fromLocalFile(str(qml_path)))
        if not self.engine.rootObjects():
            raise RuntimeError(f"Could not load multi-instance launcher UI: {qml_path}")
        if smoke_test:
            QTimer.singleShot(600, self.app.quit)

    def run(self) -> int:
        return int(self.app.exec())


def run_multi_instance_launcher(*, smoke_test: bool = False) -> int:
    return MultiInstanceLauncher(smoke_test=smoke_test).run()
