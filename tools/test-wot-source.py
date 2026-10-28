"""Run candidate source tests with the same interpreter visible to child CLIs.

pytest's pythonpath option changes only its own sys.path. Export PYTHONPATH to
exercise the source candidate in subprocesses while preserving the registry pin.
"""

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    environment = dict(os.environ)
    paths = [str(ROOT / "packages/modpoll-wot")]
    if environment.get("PYTHONPATH"):
        paths.append(environment["PYTHONPATH"])
    environment["PYTHONPATH"] = os.pathsep.join(paths)
    return subprocess.run(
        [sys.executable, "-m", "pytest", *sys.argv[1:]],
        cwd=ROOT,
        env=environment,
    ).returncode


if __name__ == "__main__":
    sys.exit(main())
