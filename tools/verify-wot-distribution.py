"""Verify a producer wheel with a temporary consumer pin, without source imports.

The real application's dependency remains unchanged until producer publication.
Only a disposable copy of its package metadata receives the candidate pin.
"""

import argparse
import email
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def verify(wheel, modsim, report):
    wheel = wheel.resolve()
    modsim = modsim.resolve()
    with zipfile.ZipFile(wheel) as archive:
        metadata = next(
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        )
        info = email.message_from_bytes(archive.read(metadata))
        if info["Name"] != "modpoll-wot":
            raise ValueError("expected a modpoll-wot producer wheel")
        version = info["Version"]
    with tempfile.TemporaryDirectory(prefix="modpoll-wot-distribution-") as temp:
        work = Path(temp)
        consumer = work / "consumer"
        consumer.mkdir()
        shutil.copytree(
            ROOT / "modpoll",
            consumer / "modpoll",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        for name in ("README.md", "LICENSE"):
            shutil.copy2(ROOT / name, consumer / name)
        project = (ROOT / "pyproject.toml").read_text()
        project, count = re.subn(
            r'(?m)^([ \t]*)"modpoll-wot==[^"]+",$',
            rf'\1"modpoll-wot=={version}",',
            project,
        )
        if count != 1:
            raise ValueError("expected exactly one consumer registry pin")
        project = re.sub(
            r'(?m)^version = "([^"+]+)(?:\+[^" ]+)?"',
            r'version = "\1+wotcontract"',
            project,
            count=1,
        )
        (consumer / "pyproject.toml").write_text(project)
        subprocess.run(["uv", "build", "--no-sources"], cwd=consumer, check=True)
        consumer_wheel = next((consumer / "dist").glob("*.whl"))
        # Expose test tools, never either package's source directory.
        helpers = work / "helpers"
        helpers.mkdir()
        shutil.copytree(
            ROOT / "tools",
            helpers / "tools",
            ignore=shutil.ignore_patterns("node_modules", "__pycache__"),
        )
        env = dict(
            os.environ,
            PYTHONPATH=str(helpers),
            MODSIM_SOURCE=str(modsim),
            MODSIM_PYTHON=str(modsim / ".venv/bin/python"),
        )
        env.pop("VIRTUAL_ENV", None)
        junit = work / "distribution-tests.xml"
        runner = f"""import importlib.metadata, pathlib, modpoll, modpoll_wot, pytest
root = pathlib.Path({str(ROOT)!r}).resolve()
for module in (modpoll, modpoll_wot):
    path = pathlib.Path(module.__file__).resolve()
    assert "site-packages" in path.parts, path
    assert not path.is_relative_to(root), path
assert importlib.metadata.version("modpoll-wot") == {version!r}
print("Installed consumer:", modpoll.__file__)
print("Installed producer:", modpoll_wot.__file__)
raise SystemExit(pytest.main(["--import-mode=importlib", "-q", "--junitxml={junit}", {str(ROOT / 'tests/test_profile_interop.py')!r}]))
"""
        subprocess.run(
            [
                "uv",
                "run",
                "--isolated",
                "--with",
                str(wheel),
                "--with",
                str(consumer_wheel) + "[serial]",
                "--with",
                "pytest>=8.2.2,<9",
                "python",
                "-c",
                runner,
            ],
            cwd=work,
            env=env,
            check=True,
        )
        from xml.etree import ElementTree

        suites = ElementTree.parse(junit).getroot().findall("testsuite")
        counts = {
            key: sum(int(suite.get(key, 0)) for suite in suites)
            for key in ("tests", "failures", "errors", "skipped")
        }
        if not counts["tests"] or any(
            counts[key] for key in ("failures", "errors", "skipped")
        ):
            raise ValueError(
                f"distribution gate requires all tests, with no skips: {counts}"
            )
        evidence = {
            "producer_version": version,
            "producer_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
            "temporary_consumer_pin": version,
            "source_imports": False,
            **counts,
        }
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(evidence, indent=2) + "\n")
        print(json.dumps(evidence))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--modsim", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    verify(args.wheel, args.modsim, args.report.resolve())


if __name__ == "__main__":
    main()
