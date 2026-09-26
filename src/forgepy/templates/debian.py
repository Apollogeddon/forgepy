from __future__ import annotations

# Plain (non f-string) templates — see workflows.py for why.
#
# The shipped .venv must be built with `uv venv --relocatable --no-managed-python`
# (system Python, not uv's own managed download) then `uv sync --no-editable` -
# uv-managed Python installs live at a fixed absolute path outside the venv itself,
# which a .deb install on an arbitrary target can't guarantee exists. Building
# against the system python3 means `depends: python3 (>= X.Y)` actually covers it,
# since apt installs that to a stable, well-known location.
#
# __FORGEPY_DEB_NAME__ is the Debian-policy name (package, unit, /opt dir);
# __FORGEPY_MODULE_NAME__ is the underscored importable module name;
# __FORGEPY_PYTHON_VERSION__ is the target Python version (e.g. "3.13").

NFPM_YAML = """\
# Requires the nfpm CLI on PATH (https://nfpm.goreleaser.com) - it's a standalone
# Go binary, not a Python package, so it isn't pulled in via pip/uv.
# Build with: python packaging/build_deb.py (sets $VERSION from pyproject.toml).
name: "__FORGEPY_DEB_NAME__"
arch: "amd64"
platform: "linux"
version: "${VERSION}"
section: "default"
priority: "extra"
maintainer: "__FORGEPY_MAINTAINER__"
description: "__FORGEPY_DEB_NAME__"
license: "MIT"

contents:
  # A --no-editable `uv sync` installs the project into .venv's own site-packages,
  # so shipping the venv alone is enough - no separate src/ copy needed.
  - src: .venv
    dst: /opt/__FORGEPY_DEB_NAME__/.venv
  - src: packaging/__FORGEPY_DEB_NAME__.service
    dst: /etc/systemd/system/__FORGEPY_DEB_NAME__.service

depends:
  - python3 (>= __FORGEPY_PYTHON_VERSION__)

scripts:
  postinstall: packaging/postinstall.sh
"""

SYSTEMD_UNIT = """\
[Unit]
Description=__FORGEPY_DEB_NAME__
After=network.target

[Service]
Type=simple
ExecStart=/opt/__FORGEPY_DEB_NAME__/.venv/bin/python -m __FORGEPY_MODULE_NAME__
Restart=on-failure
User=__FORGEPY_DEB_NAME__

[Install]
WantedBy=multi-user.target
"""

POSTINSTALL_SH = """\
#!/bin/sh
set -e
id -u __FORGEPY_DEB_NAME__ >/dev/null 2>&1 || useradd --system --no-create-home __FORGEPY_DEB_NAME__
systemctl daemon-reload
systemctl enable __FORGEPY_DEB_NAME__.service
"""

BUILD_DEB_PY = '''\
"""Builds the .deb: stamps nfpm.yaml's ${VERSION} from pyproject.toml, since nfpm
doesn't read it itself. Run after `uv venv --relocatable --no-managed-python .venv`
and `uv sync --locked --no-dev --no-editable` have populated .venv.
"""

import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

nfpm = shutil.which("nfpm")
if nfpm is None:
    print("nfpm not found on PATH - install it from https://nfpm.goreleaser.com", file=sys.stderr)
    sys.exit(1)

with Path("pyproject.toml").open("rb") as f:
    version = tomllib.load(f)["project"]["version"]

env = os.environ | {"VERSION": version}
result = subprocess.run([nfpm, "pkg", "--packager", "deb", "-f", "nfpm.yaml"], env=env, check=False)  # noqa: S603
sys.exit(result.returncode)
'''


def render(
    template: str,
    *,
    deb_name: str,
    module_name: str,
    python_version: str = "3.13",
    maintainer: str = "unspecified",
) -> str:
    return (
        template.replace("__FORGEPY_DEB_NAME__", deb_name)
        .replace("__FORGEPY_MODULE_NAME__", module_name)
        .replace("__FORGEPY_PYTHON_VERSION__", python_version)
        .replace("__FORGEPY_MAINTAINER__", maintainer)
    )
