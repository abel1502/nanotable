from __future__ import annotations
import typing

import pytest

import nanotable.safety


def test_exports() -> None:
    exports = nanotable.safety.__all__
    
    assert "disable_safety_checks" in exports
    assert "verify_immutable_key" in exports


def test_catches_change() -> None:
    with pytest.warns(UserWarning, match=r"An indexed field [\'\"]foo[\'\"] was changed"):
        nanotable.safety.verify_immutable_key(1, 2, object(), "foo")


def test_accepts_constant(recwarn: pytest.WarningsRecorder) -> None:
    nanotable.safety.verify_immutable_key(1, 1, object(), "foo")
    
    assert recwarn.list == []


def test_respects_silencing(recwarn: pytest.WarningsRecorder, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nanotable.safety, "disable_safety_checks", True)
    
    nanotable.safety.verify_immutable_key(1, 2, object(), "foo")
    
    assert recwarn.list == []

