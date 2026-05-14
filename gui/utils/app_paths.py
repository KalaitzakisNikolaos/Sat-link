"""Shared helpers for app resource and user-writable paths."""

import os
import sys

APP_NAME = "Sat-Link"


def get_app_root():
    """Return the runtime app root for source and frozen builds."""
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return meipass
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_resource_path(*parts):
    """Build an absolute path under the runtime app root."""
    return os.path.join(get_app_root(), *parts)


def get_user_data_dir():
    """Return a per-user writable config folder and create it if needed."""
    if os.name == "nt":
        base_dir = os.environ.get("APPDATA")
        if not base_dir:
            base_dir = os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
    elif sys.platform == "darwin":
        base_dir = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:
        base_dir = os.environ.get("XDG_CONFIG_HOME")
        if not base_dir:
            base_dir = os.path.join(os.path.expanduser("~"), ".config")

    path = os.path.join(base_dir, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path
