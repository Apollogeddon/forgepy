from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("forgepy")
except PackageNotFoundError:
    __version__ = "0.6.0"
