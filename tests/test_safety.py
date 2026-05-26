from __future__ import annotations
import typing

import pytest

import nanotable.safety
from nanotable.safety import IndexedFieldChangedWarning, verify_immutable_key


def test_exports() -> None:
    exports = nanotable.safety.__all__
    
    assert "disable_safety_checks" in exports
    assert "IndexedFieldChangedWarning" in exports
    assert "verify_immutable_key" in exports


def test_catches_change() -> None:
    with pytest.warns(IndexedFieldChangedWarning, match=r"An indexed field [\'\"]foo[\'\"] was changed"):
        verify_immutable_key(1, 2, object(), "foo")


def test_accepts_constant(recwarn: pytest.WarningsRecorder) -> None:
    verify_immutable_key(1, 1, object(), "foo")
    
    assert recwarn.list == []


def test_respects_silencing(recwarn: pytest.WarningsRecorder, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nanotable.safety, "disable_safety_checks", True)
    
    verify_immutable_key(1, 2, object(), "foo")
    
    assert recwarn.list == []

