"""Install reviewed, pinned upstream skills without executing repository code."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

LOCK = Path(__file__).resolve().parent / "resources" / "anthropic-skills.lock.json"
APACHE_LICENSE_DIGESTS = {
    "bc6b3af2f331cbc7fb0da1344efb2cbe5877a31498b4d70dbc7000f3405a1362",
    "0d542e0c8804e39aa7f37eb00da5a762149dc682d7829451287e11b938e94594",
}
MAX_FILES = 512
MAX_BYTES = 16_777_216
SKILL_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


class SkillSourceError(ValueError):
    """The pinned source, selected package, or destination failed validation."""


def load_lock(path: Path = LOCK) -> dict[str, Any]:
    """Read the bundled source pin and reject malformed or restricted selections."""
    lock = json.loads(path.read_text(encoding="utf-8"))
    if (
        lock.get("schemaVersion") != "nucleus.federated-skills/v1"
        or lock.get("source") != "https://github.com/anthropics/skills.git"
        or not re.fullmatch(r"[0-9a-f]{40}", lock.get("commit", ""))
        or not isinstance(lock.get("packages"), dict)
        or not lock["packages"]
    ):
        raise SkillSourceError("invalid-skill-lock")
    for name, package in lock["packages"].items():
        files = package.get("files") if isinstance(package, dict) else None
        if (
            not SKILL_NAME.fullmatch(name)
            or name in {"docx", "pdf", "pptx", "xlsx"}
            or package.get("license") != "Apache-2.0"
            or not isinstance(files, dict)
            or not {"SKILL.md", "LICENSE.txt"} <= files.keys()
            or files["LICENSE.txt"] not in APACHE_LICENSE_DIGESTS
            or any(
                not isinstance(relative, str)
                or Path(relative).is_absolute()
                or ".." in Path(relative).parts
                or not re.fullmatch(r"[0-9a-f]{64}", digest)
                for relative, digest in files.items()
            )
        ):
            raise SkillSourceError("invalid-skill-lock")
    return lock


def _git(*args: str, timeout: int = 120) -> str:
    """Run a fixed Git operation without exposing subprocess output on failure."""
    result = subprocess.run(
        ["git", *args], capture_output=True, text=True, check=False, timeout=timeout
    )
    if result.returncode:
        raise SkillSourceError("upstream-git-unavailable")
    return result.stdout.strip()


def fetch_pinned_source(lock: dict[str, Any], base: Path) -> Path:
    """Fetch the public repository and detach at the exact reviewed commit."""
    checkout = base / "source"
    _git("clone", "--filter=blob:none", "--no-checkout", lock["source"], str(checkout))
    _git("-C", str(checkout), "checkout", "--detach", lock["commit"])
    if _git("-C", str(checkout), "rev-parse", "HEAD") != lock["commit"]:
        raise SkillSourceError("source-commit-mismatch")
    return checkout


def verify_package(checkout: Path, name: str, lock: dict[str, Any]) -> Path:
    """Verify a clean pinned package's full file inventory and Apache license."""
    if name not in lock["packages"]:
        raise SkillSourceError("skill-not-selected")
    if _git("-C", str(checkout), "rev-parse", "HEAD", timeout=5) != lock["commit"]:
        raise SkillSourceError("source-commit-mismatch")
    package = checkout / "skills" / name
    if package.is_symlink() or not package.is_dir():
        raise SkillSourceError("skill-unavailable")
    if _git(
        "-C", str(checkout), "status", "--porcelain", "--ignored", "--", str(package), timeout=5
    ):
        raise SkillSourceError("source-not-clean")
    if _hash_package_files(package) != lock["packages"][name]["files"]:
        raise SkillSourceError("skill-content-mismatch")
    return package


def verify_bundled_candidate(package: Path, name: str, lock: dict[str, Any]) -> None:
    """Confirm packaged review content still matches the pinned source lock."""
    if name not in lock["packages"] or package.is_symlink() or not package.is_dir():
        raise SkillSourceError("skill-unavailable")
    if _hash_package_files(package, exclude_object=True) != lock["packages"][name]["files"]:
        raise SkillSourceError("skill-content-mismatch")


def _hash_package_files(package: Path, *, exclude_object: bool = False) -> dict[str, str]:
    """Hash a bounded, symlink-free skill tree; ignore only Nucleus metadata."""
    actual: dict[str, str] = {}
    total = 0
    for path in sorted(package.rglob("*")):
        if path.is_symlink():
            raise SkillSourceError("symlink-in-skill")
        if not path.is_file():
            continue
        relative = path.relative_to(package).as_posix()
        if exclude_object and relative == "object.json":
            continue
        data = path.read_bytes()
        total += len(data)
        if len(actual) >= MAX_FILES or total > MAX_BYTES:
            raise SkillSourceError("skill-too-large")
        actual[relative] = hashlib.sha256(data).hexdigest()
    return actual


def install_from_checkout(
    checkout: Path, names: list[str], destination: Path, lock: dict[str, Any]
) -> list[Path]:
    """Copy verified packages atomically, refusing any existing destination."""
    if (
        not names
        or len(set(names)) != len(names)
        or any(name not in lock["packages"] for name in names)
    ):
        raise SkillSourceError("invalid-skill-selection")
    packages = {name: verify_package(checkout, name, lock) for name in names}
    if destination.is_symlink():
        raise SkillSourceError("unsafe-skill-destination")
    destination.mkdir(parents=True, exist_ok=True)
    if any((destination / name).exists() or (destination / name).is_symlink() for name in names):
        raise SkillSourceError("skill-already-installed")
    installed: list[Path] = []
    with tempfile.TemporaryDirectory(prefix=".nucleus-skills-", dir=destination) as temporary:
        staging = Path(temporary)
        for name, package in packages.items():
            shutil.copytree(package, staging / name, symlinks=False)
            (staging / name / ".nucleus-source.json").write_text(
                json.dumps(
                    {"source": lock["source"], "commit": lock["commit"], "path": f"skills/{name}"},
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
        try:
            for name in names:
                target = destination / name
                if target.exists() or target.is_symlink():
                    raise SkillSourceError("skill-already-installed")
                (staging / name).rename(target)
                installed.append(target)
        except (OSError, SkillSourceError):
            for target in installed:
                shutil.rmtree(target)
            raise
    return installed


def install(names: list[str], destination: Path, lock: dict[str, Any]) -> list[Path]:
    """Fetch once, verify every selection, and install to an explicit local root."""
    with tempfile.TemporaryDirectory(prefix="nucleus-anthropic-skills-") as temporary:
        checkout = fetch_pinned_source(lock, Path(temporary))
        return install_from_checkout(checkout, names, destination, lock)


def main(argv: list[str] | None = None) -> None:
    """Provide offline discovery and explicit Codex or custom-directory install."""
    parser = argparse.ArgumentParser(description="Use pinned Apache-2.0 Anthropic skills")
    action = parser.add_subparsers(dest="action", required=True)
    action.add_parser("list", help="List the 13 reviewed skill names without network access")
    installer = action.add_parser("install", help="Fetch and install selected skills")
    installer.add_argument("names", nargs="*")
    installer.add_argument("--all", action="store_true", help="Install all 13 selected skills")
    installer.add_argument("--dest", type=Path, help="Skills root; defaults to ~/.codex/skills")
    args = parser.parse_args(argv)
    lock = load_lock()
    if args.action == "list":
        for name in sorted(lock["packages"]):
            print(name)
        return
    if args.all == bool(args.names):
        parser.error("provide skill names or --all")
    names = sorted(lock["packages"]) if args.all else args.names
    destination = args.dest if args.dest is not None else Path.home() / ".codex" / "skills"
    try:
        for path in install(names, destination, lock):
            print(path)
    except (OSError, SkillSourceError, subprocess.TimeoutExpired) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
