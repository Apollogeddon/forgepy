from __future__ import annotations

from pathlib import Path

import pytest
import tomlkit

from forgepy import pyproject as pj
from forgepy.utils.filesystem import MemoryFileSystem


def test_load_or_create_builds_default_when_missing():
    fs = MemoryFileSystem()
    doc = pj.load_or_create(fs, Path("my-cool-project"), "3.13")
    assert doc["project"]["name"] == "my-cool-project"
    assert doc["project"]["requires-python"] == ">=3.13"
    assert doc["build-system"]["build-backend"] == "uv_build"


def test_load_or_create_normalizes_project_name():
    fs = MemoryFileSystem()
    doc = pj.load_or_create(fs, Path("My_Cool.Project"), "3.13")
    assert doc["project"]["name"] == "my-cool-project"


def test_load_or_create_parses_existing_file_preserving_comments():
    fs = MemoryFileSystem()
    content = '# a comment\n[project]\nname = "existing"\n'
    fs.write_text(Path("proj/pyproject.toml"), content)
    doc = pj.load_or_create(fs, Path("proj"))
    assert doc["project"]["name"] == "existing"
    assert tomlkit.dumps(doc).startswith("# a comment")


def test_load_or_create_raises_on_malformed_toml():
    fs = MemoryFileSystem()
    fs.write_text(Path("proj/pyproject.toml"), "not [ valid toml")
    with pytest.raises(pj.PyprojectError):
        pj.load_or_create(fs, Path("proj"))


def test_set_task_adds_when_missing():
    doc = tomlkit.document()
    pj.set_task(doc, "lint", "ruff check", force=False)
    assert doc["tool"]["poe"]["tasks"]["lint"] == "ruff check"


def test_set_task_preserves_custom_value_without_force():
    doc = tomlkit.document()
    pj.set_task(doc, "lint", "custom command", force=False)
    pj.set_task(doc, "lint", "ruff check", force=False)
    assert doc["tool"]["poe"]["tasks"]["lint"] == "custom command"


def test_set_task_overwrites_with_force():
    doc = tomlkit.document()
    pj.set_task(doc, "lint", "custom command", force=False)
    pj.set_task(doc, "lint", "ruff check", force=True)
    assert doc["tool"]["poe"]["tasks"]["lint"] == "ruff check"


def test_ensure_classifier_appends_once():
    doc = tomlkit.document()
    pj.ensure_classifier(doc, "Private :: Do Not Upload")
    pj.ensure_classifier(doc, "Private :: Do Not Upload")
    assert list(doc["project"]["classifiers"]) == ["Private :: Do Not Upload"]


def test_ensure_dev_dependency_avoids_duplicates_by_package_name():
    doc = tomlkit.document()
    pj.ensure_dev_dependency(doc, "forgepy[toolchain]")
    pj.ensure_dev_dependency(doc, "forgepy[toolchain]>=1.0")
    assert len(doc["dependency-groups"]["dev"]) == 1


def test_set_table_if_absent_creates_nested_table():
    doc = tomlkit.document()
    pj.set_table_if_absent(
        doc,
        ("build-system",),
        {"requires": ["uv_build"], "build-backend": "uv_build"},
        force=False,
    )
    assert list(doc["build-system"]["requires"]) == ["uv_build"]
    assert doc["build-system"]["build-backend"] == "uv_build"


def test_set_table_if_absent_respects_existing_without_force():
    doc = tomlkit.document()
    pj.set_table_if_absent(
        doc, ("build-system",), {"build-backend": "custom"}, force=False
    )
    pj.set_table_if_absent(
        doc, ("build-system",), {"build-backend": "uv_build"}, force=False
    )
    assert doc["build-system"]["build-backend"] == "custom"


def test_save_round_trips(tmp_path=None):
    fs = MemoryFileSystem()
    doc = pj.load_or_create(fs, Path("proj"))
    pj.save(fs, Path("proj"), doc)
    reloaded = tomlkit.parse(fs.read_text(Path("proj/pyproject.toml")))
    assert reloaded["project"]["name"] == "proj"
