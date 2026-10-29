from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP_ENTRY = ROOT / "app.py"


def main() -> None:
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name",
        "SD Prompt Assembler",
        "--onefile",
        "--windowed",
        "--distpath",
        str(ROOT / "dist"),
        "--workpath",
        str(ROOT / "build"),
        "--specpath",
        str(ROOT),
        str(APP_ENTRY),
    ]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
