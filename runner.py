"""Build an isolated venv for a set of pins and run the test command in it."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .core import Outcome


def _venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def run_trial(
    lines: list[str], test_cmd: str, project_dir: Path, editable: bool = False
) -> Outcome:
    uv = shutil.which("uv")
    with tempfile.TemporaryDirectory(prefix="culpip-") as tmp:
        tmp_path = Path(tmp)
        venv = tmp_path / "venv"
        py = _venv_python(venv)
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("\n".join(lines) + "\n")

        if uv:
            create = [uv, "venv", "--python", sys.executable, str(venv)]
            install = [uv, "pip", "install", "--python", str(py)]
        else:
            create = [sys.executable, "-m", "venv", str(venv)]
            install = [str(py), "-m", "pip", "install"]

        steps = [create, install + ["-r", str(req_file)]]
        if editable:
            steps.append(install + ["--no-deps", "-e", str(project_dir)])
        for cmd in steps:
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode != 0:
                return Outcome.ERROR

        env = dict(os.environ)
        env["VIRTUAL_ENV"] = str(venv)
        env["PATH"] = str(py.parent) + os.pathsep + env.get("PATH", "")
        env.pop("PYTHONHOME", None)
        r = subprocess.run(test_cmd, shell=True, cwd=project_dir, env=env)
        return Outcome.PASS if r.returncode == 0 else Outcome.FAIL
