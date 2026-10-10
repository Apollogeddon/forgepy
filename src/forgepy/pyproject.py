from __future__ import annotations

import re
from collections.abc import MutableMapping
from pathlib import Path
from typing import Any, cast

import tomlkit
from tomlkit import TOMLDocument, table
from tomlkit.exceptions import TOMLKitError

from forgepy.config import DEFAULT_PYTHON_VERSION
from forgepy.utils.filesystem import FileSystem

PYPROJECT_FILENAME = "pyproject.toml"

# tomlkit's stubs return Unknown/Any - every helper here returns a concrete type
# so that leakage stays contained to this module.

AnyMap = MutableMapping[str, Any]


class PyprojectError(Exception):
    pass


def normalize_project_name(name: str) -> str:
    normalized = re.sub(r"[-_.]+", "-", name).lower()
    return normalized.strip("-") or "project"


def project_name(doc: TOMLDocument, cwd: Path) -> str:
    """The project's declared name, falling back to the directory name."""
    project: AnyMap = cast(AnyMap, doc).get("project") or {}
    name = project.get("name")
    return str(name) if name else cwd.name


def project_urls(doc: TOMLDocument) -> list[str]:
    """The URLs in the project's [project.urls] table, in order."""
    project: AnyMap = cast(AnyMap, doc).get("project") or {}
    urls: AnyMap = project.get("urls") or {}
    return [str(url) for url in urls.values()]


def package_module_name(doc: TOMLDocument, cwd: Path) -> str:
    """The importable module name for the project (PEP 503 name with '-' -> '_')."""
    return normalize_project_name(project_name(doc, cwd)).replace("-", "_")


def _default_document(project_dir_name: str, python_version: str) -> TOMLDocument:
    doc = tomlkit.document()

    project = table()
    project.add("name", normalize_project_name(project_dir_name))
    project.add("version", "0.1.0")
    project.add("requires-python", f">={python_version}")
    project.add("dependencies", tomlkit.array())
    doc.add("project", project)
    # [build-system] is added by BaseFeature, which knows whether the mode builds a package
    return doc


def load_or_create(fs: FileSystem, cwd: Path, python_version: str = DEFAULT_PYTHON_VERSION) -> TOMLDocument:
    path = cwd / PYPROJECT_FILENAME
    if not fs.exists(path):
        return _default_document(cwd.name, python_version)

    raw = fs.read_text(path)
    try:
        return tomlkit.parse(raw)
    except TOMLKitError as exc:
        raise PyprojectError(f"{PYPROJECT_FILENAME} is malformed: {exc}") from exc


def save(fs: FileSystem, cwd: Path, doc: TOMLDocument) -> None:
    fs.write_text(cwd / PYPROJECT_FILENAME, tomlkit.dumps(doc))


def _ensure_table(doc: TOMLDocument, dotted_path: tuple[str, ...]) -> AnyMap:
    node = cast(AnyMap, doc)
    for key in dotted_path:
        if key not in node or not isinstance(node[key], dict):
            node[key] = table()
        node = cast(AnyMap, node[key])
    return node


def set_key_if_absent(doc: TOMLDocument, dotted_path: tuple[str, ...], key: str, value: object, *, force: bool) -> None:
    """Set a single key within a (possibly pre-existing) table without touching its other keys."""
    node = _ensure_table(doc, dotted_path)
    if key in node and not force:
        return
    node[key] = tomlkit.item(value)


def set_task(doc: TOMLDocument, name: str, cmd: str, *, force: bool) -> None:
    tasks = _ensure_table(doc, ("tool", "poe", "tasks"))
    if name in tasks and not force:
        return
    tasks[name] = cmd


def set_shell_task(doc: TOMLDocument, name: str, cmd: str, *, force: bool) -> None:
    """poe runs plain string tasks without a shell, so &&/| need the {shell = ...} form."""
    tasks = _ensure_table(doc, ("tool", "poe", "tasks"))
    if name in tasks and not force:
        return
    task_table = table()
    task_table.add("shell", cmd)
    tasks[name] = task_table


def ensure_classifier(doc: TOMLDocument, classifier: str) -> None:
    project = _ensure_table(doc, ("project",))
    classifiers = project.get("classifiers")
    if classifiers is None:
        classifiers = tomlkit.array()
        project["classifiers"] = classifiers
    typed = cast("list[str]", classifiers)
    if classifier not in list(typed):
        typed.append(classifier)


def ensure_dev_dependency(doc: TOMLDocument, requirement: str) -> None:
    dep_groups = _ensure_table(doc, ("dependency-groups",))
    dev = dep_groups.get("dev")
    if dev is None:
        dev = tomlkit.array()
        dep_groups["dev"] = dev
    typed = cast("list[str]", dev)
    package_name = re.split(r"[\[<>=!~ ]", requirement, maxsplit=1)[0]
    if not any(str(item).split("[")[0].strip() == package_name for item in typed):
        typed.append(requirement)


def set_table_if_absent(
    doc: TOMLDocument,
    dotted_path: tuple[str, ...],
    content: dict[str, object],
    *,
    force: bool,
) -> None:
    node = _ensure_table(doc, dotted_path[:-1])

    leaf_key = dotted_path[-1]
    if leaf_key in node and not force:
        return

    new_table = table()
    for k, v in content.items():
        new_table.add(k, tomlkit.item(v))
    node[leaf_key] = new_table
