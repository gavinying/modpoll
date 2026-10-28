"""Export locked requirements with a portable local shared-package path."""

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
lines = []
for line in output.splitlines():
    if "file://" in line and "/packages/modpoll-wot-modbus" in line:
        line = "./packages/modpoll-wot-modbus"
    lines.append(line)
(root / "requirements.txt").write_text(
    "\n".join(sorted(lines, key=lambda line: line.split("==", 1)[0].lower())) + "\n"
)
