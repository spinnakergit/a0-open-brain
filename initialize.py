"""One-time setup script for the Open Brain plugin.

Installs required Python dependencies into the Agent Zero venv.
Called by the Init button in Agent Zero's Plugin List UI.
Must define main() returning 0 on success, non-zero on failure.
"""

import logging
import shutil
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger("open_brain_init")


def _find_python():
    """Find the correct Python interpreter (prefer A0 venv)."""
    venv_python = Path("/opt/venv-a0/bin/python")
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def _install(pip_name: str, python: str):
    """Install a package using uv (preferred) or pip as fallback."""
    uv = shutil.which("uv")
    if uv:
        subprocess.check_call([uv, "pip", "install", pip_name, "--python", python])
    else:
        subprocess.check_call([python, "-m", "pip", "install", pip_name])


def main():
    python = _find_python()
    # Map of import name -> pip spec
    deps = {
        "aiohttp": "aiohttp>=3.9,<4",
    }
    failed = []
    for import_name, pip_name in deps.items():
        try:
            result = subprocess.run(
                [python, "-c", f"import {import_name}"],
                capture_output=True,
            )
            if result.returncode == 0:
                logger.info(f"{pip_name} already installed.")
                continue
        except Exception:
            pass
        logger.info(f"Installing {pip_name}...")
        try:
            _install(pip_name, python)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install {pip_name}: {type(e).__name__}")
            failed.append(pip_name)

    if failed:
        logger.error(f"Failed to install: {', '.join(failed)}")
        return 1

    logger.info("All dependencies ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
