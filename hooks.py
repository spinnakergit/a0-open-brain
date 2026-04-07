"""Plugin lifecycle hooks for the Open Brain plugin.

Called by Agent Zero's plugin system during install, uninstall, and update.
See: helpers/plugins.py -> call_plugin_hook()
"""
import logging
import os
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger("open_brain_hooks")


def _get_plugin_dir() -> Path:
    """Return the directory this hooks.py lives in."""
    return Path(__file__).parent.resolve()


def _get_a0_root() -> Path:
    """Detect A0 root directory."""
    if Path("/a0/plugins").is_dir():
        return Path("/a0")
    if Path("/git/agent-zero/plugins").is_dir():
        return Path("/git/agent-zero")
    return Path("/a0")


def _find_python() -> str:
    """Find the appropriate Python interpreter."""
    candidates = ["/opt/venv-a0/bin/python3", sys.executable, "python3"]
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return "python3"


def install(**kwargs):
    """Post-install hook: set up data dir, deps, skills, toggle."""
    plugin_dir = _get_plugin_dir()
    a0_root = _get_a0_root()
    plugin_name = "open_brain"

    logger.info("Running post-install hook...")

    # 1. Enable plugin
    toggle = plugin_dir / ".toggle-1"
    if not toggle.exists():
        toggle.touch()
        logger.info("Created %s", toggle)

    # 2. Create data directory with restrictive permissions
    data_dir = plugin_dir / "data"
    data_dir.mkdir(exist_ok=True)
    os.chmod(str(data_dir), 0o700)

    # 3. Pre-create config.json with restrictive permissions (0o600).
    config_file = plugin_dir / "config.json"
    if not config_file.exists():
        import json
        fd = os.open(str(config_file), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump({}, f)
        logger.info("Created config.json with 0o600 permissions")

    # 4. Install Python dependencies directly (inlined for streamlined lifecycle)
    python = _find_python()
    deps = {"aiohttp": "aiohttp>=3.9,<4"}
    for import_name, pip_spec in deps.items():
        try:
            result = subprocess.run(
                [python, "-c", f"import {import_name}"],
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0:
                logger.info("%s already installed", pip_spec)
                continue
        except Exception:
            pass
        logger.info("Installing %s...", pip_spec)
        try:
            import shutil as _shutil

            uv = _shutil.which("uv")
            if uv:
                subprocess.check_call(
                    [uv, "pip", "install", pip_spec, "--python", python],
                    timeout=120,
                )
            else:
                subprocess.check_call(
                    [python, "-m", "pip", "install", pip_spec],
                    timeout=120,
                )
            logger.info("%s installed", pip_spec)
        except subprocess.CalledProcessError as e:
            logger.warning("Failed to install %s: %s", pip_spec, type(e).__name__)
        except subprocess.TimeoutExpired:
            logger.warning("Install of %s timed out", pip_spec)

    # 5. Create import symlink at <a0_root>/plugins/<name> -> <plugin_dir>
    symlink = a0_root / "plugins" / plugin_name
    if not symlink.exists():
        try:
            symlink.symlink_to(plugin_dir)
            logger.info("Created symlink: %s -> %s", symlink, plugin_dir)
        except Exception:
            logger.debug("Could not create symlink (may already exist)")

    logger.info("Post-install hook complete")


def uninstall(**kwargs):
    """Pre-uninstall hook: clean up skills and symlink."""
    a0_root = _get_a0_root()
    plugin_name = "open_brain"

    logger.info("Running uninstall hook...")

    # Remove import symlink
    symlink = a0_root / "plugins" / plugin_name
    if symlink.is_symlink():
        symlink.unlink()
        logger.info("Removed symlink: %s", symlink)
    logger.info("Uninstall hook complete")
