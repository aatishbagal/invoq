from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("invoq")
except PackageNotFoundError:
    __version__ = "unknown"
