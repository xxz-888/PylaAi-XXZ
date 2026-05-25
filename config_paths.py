import os
import shutil
import sys
from pathlib import Path


_PROJECT_CFG_WRITABLE = None


def project_root():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def _normalized_relative_path(file_path):
    normalized = os.fspath(file_path).replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def raw_project_path(file_path):
    file_path = os.fspath(file_path)
    if os.path.isabs(file_path):
        return file_path
    return os.path.join(project_root(), _normalized_relative_path(file_path))


def _is_cfg_toml_path(file_path):
    normalized = _normalized_relative_path(file_path).lower()
    return normalized.startswith("cfg/") and normalized.endswith(".toml")


def user_config_root():
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    if not base:
        base = str(Path.home() / "AppData" / "Local")
    return os.path.join(base, "PylaAi-XXZ")


def _project_cfg_dir_is_writable():
    global _PROJECT_CFG_WRITABLE
    if os.environ.get("PYLAAI_FORCE_USER_CONFIG", "").strip().lower() in {"1", "true", "yes"}:
        return False
    if _PROJECT_CFG_WRITABLE is not None:
        return _PROJECT_CFG_WRITABLE

    cfg_dir = Path(project_root()) / "cfg"
    try:
        cfg_dir.mkdir(parents=True, exist_ok=True)
        probe = cfg_dir / f".pyla_write_test_{os.getpid()}"
        probe.write_text("ok", encoding="ascii")
        probe.unlink(missing_ok=True)
        _PROJECT_CFG_WRITABLE = True
    except OSError:
        _PROJECT_CFG_WRITABLE = False
    return _PROJECT_CFG_WRITABLE


def should_use_user_config(file_path):
    return _is_cfg_toml_path(file_path) and not _project_cfg_dir_is_writable()


def user_config_path(file_path):
    return os.path.join(user_config_root(), _normalized_relative_path(file_path))


def ensure_user_config_seeded(file_path):
    destination = user_config_path(file_path)
    if os.path.exists(destination):
        return destination

    source = raw_project_path(file_path)
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    if os.path.exists(source):
        shutil.copy2(source, destination)
    else:
        Path(destination).touch()
    return destination


def resolve_project_path(file_path):
    file_path = os.fspath(file_path)
    if os.path.isabs(file_path):
        return file_path
    if should_use_user_config(file_path):
        return ensure_user_config_seeded(file_path)
    return raw_project_path(file_path)
