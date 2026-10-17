from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("forgepy")
except PackageNotFoundError:
    __version__ = "1.0.1"
