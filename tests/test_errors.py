from __future__ import annotations
import typing

import pytest

import nanotable.errors


def test_exports() -> None:
    exports = nanotable.errors.__all__
    
    assert "ConflictError" in exports
    assert "PrimaryIndexError" in exports
    assert "UnfinishedTableError" in exports
    assert "FeatureError" in exports
    assert "warn" in exports
    assert "IndexedFieldChangedWarning" in exports
    assert "UnsupportedOperationWarning" in exports

