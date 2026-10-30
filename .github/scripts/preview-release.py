"""Guard preview tags and immutable PyPI artifacts using only the standard library."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.request


CHECKS = {
    "quality-check",
    "tox (3.10)",
    "tox (3.14)",
    "docs",
    "modsim-equivalence",
}


def package_version(path):
    section = ""
    for line in Path(path).read_text().splitlines():
        if line.strip().startswith("["):
            section = line.strip()
        elif section == "[tool.poetry]":
            match = re.fullmatch(r'\s*version\s*=\s*"([^"]+)"\s*', line)
            if match:
                return match[1]
    raise ValueError("missing package version")


def release_target(tag):
    if re.fullmatch(r"modpoll-wot-v0\.[0-9]+\.[0-9]+(?:a|b|rc)[0-9]+", tag):
        return (
            "modpoll-wot",
            tag.removeprefix("modpoll-wot-v"),
            Path("packages/modpoll-wot"),
        )
    if re.fullmatch(r"v2\.[0-9]+\.[0-9]+(?:a|b|rc)[0-9]+", tag):
        return "modpoll", tag[1:], Path(".")
    raise ValueError("unsupported preview tag")


def get_json(url, token=None):
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    with urllib.request.urlopen(
        urllib.request.Request(url, headers=headers), timeout=30
    ) as response:
        return json.load(response)


def require_checks(checks, sha):
    # Select the most recent result for each name; reruns must not mask a new failure.
    latest = {}
    for check in checks:
        name = check["name"]
        if name not in latest or check["id"] > latest[name]["id"]:
            latest[name] = check
    for name in CHECKS:
        check = latest.get(name, {})
        if check.get("head_sha") != sha or check.get("conclusion") != "success":
            raise ValueError("candidate lacks a successful check: " + name)


def pypi_state(name, version, artifacts):
    expected = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in artifacts
    }
    if (
        len(expected) != 2
        or not any(n.endswith(".whl") for n in expected)
        or not any(n.endswith(".tar.gz") for n in expected)
    ):
        raise ValueError("exactly one wheel and one sdist are required")
    try:
        data = get_json(
            f"https://pypi.org/pypi/{name}/{version}/json?cache_bust={time.time_ns()}"
        )
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return "absent"
        raise
    actual = {item["filename"]: item["digests"]["sha256"] for item in data["urls"]}
    if actual != expected:
        raise ValueError(
            "existing PyPI release differs; use the original artifacts or a new version"
        )
    return "identical"


def download_published_wheel(name, version, directory):
    """Download the exact registry wheel, bypassing stale simple-index caches."""
    url = f"https://pypi.org/pypi/{name}/{version}/json" f"?cache_bust={time.time_ns()}"
    for attempt in range(6):
        try:
            data = get_json(url)
            break
        except urllib.error.HTTPError as exc:
            if exc.code != 404 or attempt == 5:
                raise
            time.sleep(10)
    wheels = [item for item in data["urls"] if item["filename"].endswith(".whl")]
    if len(wheels) != 1:
        raise ValueError("expected exactly one published wheel")
    item = wheels[0]
    destination = Path(directory) / item["filename"]
    destination.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(6):
        try:
            with urllib.request.urlopen(item["url"], timeout=60) as response:
                content = response.read()
            break
        except urllib.error.HTTPError as exc:
            if exc.code != 404 or attempt == 5:
                raise
            time.sleep(10)
    if hashlib.sha256(content).hexdigest() != item["digests"]["sha256"]:
        raise ValueError("downloaded wheel does not match PyPI's SHA-256")
    destination.write_bytes(content)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("guard", "pypi", "download"))
    parser.add_argument("tag")
    parser.add_argument("--directory")
    args = parser.parse_args()
    name, version, path = release_target(args.tag)
    if package_version(path / "pyproject.toml") != version:
        raise ValueError("tag does not match package metadata")
    if args.operation == "guard":
        sha = os.environ["GITHUB_SHA"]
        api = os.environ["GITHUB_API_URL"]
        repo = os.environ["GITHUB_REPOSITORY"]
        checks = get_json(
            f"{api}/repos/{repo}/commits/{sha}/check-runs?per_page=100",
            os.environ["GH_TOKEN"],
        )
        if checks.get("total_count", 0) > 100:
            raise ValueError("too many check runs; inspect the candidate explicitly")
        require_checks(checks["check_runs"], sha)
        print(f"Validated {name} {version} at {sha}")
    elif args.operation == "pypi":
        state = pypi_state(name, version, list((path / "dist").iterdir()))
        with open(os.environ["GITHUB_OUTPUT"], "a") as output:
            output.write(f"state={state}\n")
        print("PyPI artifacts: " + state)
    else:
        if not args.directory:
            parser.error("download requires --directory")
        print(download_published_wheel(name, version, args.directory))


if __name__ == "__main__":
    main()
