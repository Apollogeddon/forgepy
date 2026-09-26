from __future__ import annotations

# Plain (non f-string) templates — see workflows.py for why.
# Caveat: uv-built venvs bake in the absolute path they were created at, so the
# venv packaged here must be built at the same /opt/<name>/.venv path it will run
# at - moving a built .venv elsewhere breaks its shebangs.
# __FORGEPY_DEB_NAME__ is the Debian-policy name (package, unit, /opt dir);
# __FORGEPY_MODULE_NAME__ is the underscored importable module name.

NFPM_YAML = """\
# Requires the nfpm CLI on PATH (https://nfpm.goreleaser.com) - it's a standalone
# Go binary, not a Python package, so it isn't pulled in via pip/uv.
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
  - src: .venv
    dst: /opt/__FORGEPY_DEB_NAME__/.venv
  - src: src/__FORGEPY_MODULE_NAME__
    dst: /opt/__FORGEPY_DEB_NAME__/__FORGEPY_MODULE_NAME__
  - src: packaging/__FORGEPY_DEB_NAME__.service
    dst: /etc/systemd/system/__FORGEPY_DEB_NAME__.service

depends:
  - python3

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


def render(template: str, *, deb_name: str, module_name: str, maintainer: str = "unspecified") -> str:
    return (
        template.replace("__FORGEPY_DEB_NAME__", deb_name)
        .replace("__FORGEPY_MODULE_NAME__", module_name)
        .replace("__FORGEPY_MAINTAINER__", maintainer)
    )
