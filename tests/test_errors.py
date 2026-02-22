from pathlib import Path

import pytest

from claude_code_plugins_sdk.errors import LoadError


def test_load_error_message():
    err = LoadError("something went wrong")
    assert str(err) == "something went wrong"
    assert err.path is None


def test_load_error_with_path():
    p = Path("/some/file.json")
    err = LoadError("not found", path=p)
    assert err.path == p


def test_load_error_is_exception():
    with pytest.raises(LoadError):
        raise LoadError("test")
