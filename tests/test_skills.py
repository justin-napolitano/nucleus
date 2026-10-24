"""Synthetic checks for pinned skill discovery and safe local installation."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from nucleus.skills import SkillSourceError, install_from_checkout, load_lock, verify_package


def _git(*args: str) -> str:
    """Create a credential-free Git fixture with deterministic local identity."""
    result = subprocess.run(["git", *args], check=True, capture_output=True, text=True)
    return result.stdout.strip()


def _source(tmp_path: Path) -> tuple[Path, dict]:
    """Build a tiny fictional skill source and a matching in-memory lock."""
    checkout = tmp_path / "source"
    skill = checkout / "skills" / "demo-skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: demo-skill\n---\nFictional skill.\n")
    (skill / "LICENSE.txt").write_text("Fictional test license.\n")
    _git("init", str(checkout))
    _git("-C", str(checkout), "add", "skills/demo-skill")
    _git(
        "-C",
        str(checkout),
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-m",
        "Add fictional skill",
    )
    commit = _git("-C", str(checkout), "rev-parse", "HEAD")
    files = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in skill.iterdir()
        if path.is_file()
    }
    return checkout, {
        "source": "https://example.invalid/skills.git",
        "commit": commit,
        "packages": {"demo-skill": {"files": files}},
    }


def test_public_lock_contains_only_reviewed_apache_packages() -> None:
    """The bundled lock excludes separately licensed document packages."""
    lock = load_lock()
    assert len(lock["packages"]) == 13
    assert not {"docx", "pdf", "pptx", "xlsx"} & lock["packages"].keys()
    assert all(package["license"] == "Apache-2.0" for package in lock["packages"].values())


def test_fictional_skill_installs_with_source_receipt(tmp_path: Path) -> None:
    """Only exact source files can be copied and reinstallation cannot overwrite them."""
    checkout, lock = _source(tmp_path)
    destination = tmp_path / "codex" / "skills"
    installed = install_from_checkout(checkout, ["demo-skill"], destination, lock)
    assert installed == [destination / "demo-skill"]
    assert (installed[0] / "SKILL.md").is_file()
    receipt = json.loads((installed[0] / ".nucleus-source.json").read_text())
    assert receipt == {
        "source": lock["source"],
        "commit": lock["commit"],
        "path": "skills/demo-skill",
    }
    with pytest.raises(SkillSourceError, match="skill-already-installed"):
        install_from_checkout(checkout, ["demo-skill"], destination, lock)


def test_changed_or_symlinked_skill_fails_before_install(tmp_path: Path) -> None:
    """A changed file or symlink cannot become an installed package."""
    checkout, lock = _source(tmp_path)
    skill = checkout / "skills" / "demo-skill"
    (skill / "SKILL.md").write_text("Changed after pin.\n")
    with pytest.raises(SkillSourceError):
        verify_package(checkout, "demo-skill", lock)
    assert not (tmp_path / "skills").exists()

    (skill / "SKILL.md").write_text("---\nname: demo-skill\n---\nFictional skill.\n")
    (skill / "link").symlink_to(skill / "SKILL.md")
    with pytest.raises(SkillSourceError):
        install_from_checkout(checkout, ["demo-skill"], tmp_path / "skills", lock)
    assert not (tmp_path / "skills").exists()


def test_invalid_selection_does_not_create_destination(tmp_path: Path) -> None:
    """Unknown or duplicated selections fail before destination creation."""
    checkout, lock = _source(tmp_path)
    destination = tmp_path / "skills"
    for names in (["unknown"], ["demo-skill", "demo-skill"], []):
        with pytest.raises(SkillSourceError, match="invalid-skill-selection"):
            install_from_checkout(checkout, names, destination, lock)
    assert not destination.exists()
