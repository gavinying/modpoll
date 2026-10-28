"""Export deterministic registry requirements from the application lock."""

from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
output = subprocess.run(
    ["poetry", "export", "-f", "requirements.txt", "--without-hashes"],
    cwd=root,
    capture_output=True,
    text=True,
    check=True,
).stdout
lines = output.splitlines()
if any("file://" in line or line.startswith(("./", "../", "-e ")) for line in lines):
    raise ValueError("release requirements must not contain local dependencies")
(root / "requirements.txt").write_text(
    "\n".join(sorted(lines, key=lambda line: line.split("==", 1)[0].lower())) + "\n"
)
