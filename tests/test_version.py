from importlib.metadata import PackageNotFoundError
import runpy
from unittest.mock import patch

import invoq


def test_version_comes_from_package_metadata():
    with patch("importlib.metadata.version", return_value="installed-version") as version:
        package = runpy.run_path(invoq.__file__)

    version.assert_called_once_with("invoq")
    assert package["__version__"] == "installed-version"


def test_missing_metadata_does_not_invent_a_version():
    with patch("importlib.metadata.version", side_effect=PackageNotFoundError):
        package = runpy.run_path(invoq.__file__)

    assert package["__version__"] == "unknown"
