from __future__ import annotations

import re
from pathlib import Path

import tomlkit
from tomlkit import TOMLDocument, table
from tomlkit.exceptions import TOMLKitError

from forgepy.utils.filesystem import FileSystem

PYPROJECT_FILENAME = "pyproject.toml"


class PyprojectError(Exception):
    pass


def normalize_project_name(name: str) -> str:
    normalized = re.sub(r"[-_.]+", "-", name).lower()
    return normalized.strip("-") or "project"


def package_module_name(doc: TOMLDocument, cwd: Path) -> str:
    """The importable module name for the project (PEP 503 name with '-' -> '_')."""
    project = doc.get("project", {})
    name = project.get("name") if isinstance(project, dict) else None
    return normalize_project_name(str(name) if name else cwd.name).replace("-", "_")


def _default_document(project_name: str, python_version: str) -> TOMLDocument:
    doc = tomlkit.document()

    project = table()
    project.add("name", normalize_project_name(project_name))
    project.add("version", "0.1.0")
    project.add("requires-python", f">={python_version}")
    project.add("dependencies", tomlkit.array())
    doc.add("project", project)

    build_system = table()
    build_system.add("requires", tomlkit.item(["uv_build>=0.7,<0.9"]))
    build_system.add("build-backend", "uv_build")
    doc.add("build-system", build_system)

    return doc


def load_or_create(
    fs: FileSystem, cwd: Path, python_version: str = "3.13"
) -> TOMLDocument:
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


def _ensure_table(doc: TOMLDocument, dotted_path: tuple[str, ...]):
    node = doc
    for key in dotted_path:
        if key not in node or not isinstance(node[key], (dict,)):
            node[key] = table()
        node = node[key]
    return node


def set_task(doc: TOMLDocument, name: str, cmd: str, *, force: bool) -> None:
    tasks = _ensure_table(doc, ("tool", "poe", "tasks"))
    if name in tasks and not force:
        return
    tasks[name] = cmd


def ensure_classifier(doc: TOMLDocument, classifier: str) -> None:
    project = _ensure_table(doc, ("project",))
    classifiers = project.get("classifiers")
    if classifiers is None:
        classifiers = tomlkit.array()
        project["classifiers"] = classifiers
    if classifier not in list(classifiers):
        classifiers.append(classifier)


def ensure_dev_dependency(doc: TOMLDocument, requirement: str) -> None:
    dep_groups = _ensure_table(doc, ("dependency-groups",))
    dev = dep_groups.get("dev")
    if dev is None:
        dev = tomlkit.array()
        dep_groups["dev"] = dev
    package_name = re.split(r"[\[<>=!~ ]", requirement, maxsplit=1)[0]
    if not any(str(item).split("[")[0].strip() == package_name for item in dev):
        dev.append(requirement)


def set_table_if_absent(
    doc: TOMLDocument,
    dotted_path: tuple[str, ...],
    content: dict[str, object],
    *,
    force: bool,
) -> None:
    node = doc
    for key in dotted_path[:-1]:
        if key not in node or not isinstance(node[key], (dict,)):
            node[key] = table()
        node = node[key]

    leaf_key = dotted_path[-1]
    if leaf_key in node and not force:
        return

    new_table = table()
    for k, v in content.items():
        new_table.add(k, tomlkit.item(v))
    node[leaf_key] = new_table
