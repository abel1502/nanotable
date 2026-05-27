from __future__ import annotations
import typing
from types import SimpleNamespace
from dataclasses import dataclass

import pytest

import nanotable.field
from nanotable.field import FieldGetter, FieldGetterFactory, getfield_attr, getfield_item, MISSING, typeof_MISSING


def test_exports() -> None:
    exports = nanotable.field.__all__
    
    assert "FieldGetter" in exports
    assert "FieldGetterFactory" in exports
    assert "getfield_attr" in exports
    assert "getfield_item" in exports
    assert "MISSING" in exports
    assert "typeof_MISSING" in exports


def test_missing_type() -> None:
    typing.assert_type(MISSING, typeof_MISSING)


def test_field_getter_types() -> None:
    factory_attr: FieldGetterFactory[object] = getfield_attr
    factory_item: FieldGetterFactory[typing.Mapping[str, typing.Any]] = getfield_item


@dataclass
class MyDataclass:
    a: int
    b: int


@pytest.mark.parametrize("obj", [
    SimpleNamespace(a=1, b=2),
    MyDataclass(a=1, b=2),
])
def test_getfield_attr(obj: object) -> None:
    getter_a = getfield_attr("a")
    getter_missing = getfield_attr("not_present")
    
    assert getter_a(obj) == 1
    assert getter_missing(obj) is MISSING


def test_getfield_dict() -> None:
    obj = {"a": 1, "b": 2}
    
    getter_a = getfield_item("a")
    getter_missing = getfield_item("not_present")
    
    assert getter_a(obj) == 1
    assert getter_missing(obj) is MISSING

