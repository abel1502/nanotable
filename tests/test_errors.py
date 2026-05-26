from __future__ import annotations
import typing

import pytest

import nanotable.errors


def test_exports() -> None:
    exports = nanotable.errors.__all__
    
    assert "ValidationError" in exports
    assert "PrimaryIndexError" in exports
    assert "FeatureError" in exports

