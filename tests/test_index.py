from __future__ import annotations
import typing

import pytest

from nanotable.index import UniqueIndex
from nanotable.field import dict_getter


def test_normal() -> None:
    index: UniqueIndex[dict[str, typing.Any]] = UniqueIndex("id")
    
    obj1 = {"id": 1, "other": "foo"}
    obj2 = {"id": 2, "other": "bar"}
    obj3 = {"id": 3, "other": "baz"}
    
    index.add(obj1, getfield=dict_getter)
    index.add(obj2, getfield=dict_getter)
    index.add(obj3, getfield=dict_getter)
    
    assert index.get(1) == obj1
    assert index.get(2) == obj2
    assert index.get(3) == obj3
    
    with pytest.raises(KeyError):
        index.get(4)
    
    index.remove(obj1, getfield=dict_getter)
    
    with pytest.raises(KeyError):
        index.get(1)
    
    assert index.get(1, "hello") == "hello"
    assert index.get(2, "hello") == obj2
    
    with pytest.raises(KeyError):
        index.remove(obj1, getfield=dict_getter)
    
    index.remove(obj1, getfield=dict_getter, missing_ok=True)
    index.remove({"id": -1}, getfield=dict_getter, missing_ok=True)
    
    with pytest.raises(ValueError):
        index.remove({}, getfield=dict_getter, missing_ok=True)

    with pytest.raises(ValueError):
        index.add({}, getfield=dict_getter)

    with pytest.raises(ValueError):
        index.add({"id": None}, getfield=dict_getter)

    index.add({"id": 1, "other": None}, getfield=dict_getter)


def test_none_valued() -> None:
    index: UniqueIndex[dict[str, typing.Any]] = UniqueIndex("id", none_as_value=True)
    
    obj = {"id": None, "other": "foo"}
    
    with pytest.raises(KeyError):
        index.get(None)
    
    index.add(obj, getfield=dict_getter)
    
    assert index.get(None) == obj
    
    with pytest.raises(KeyError):
        index.add(obj, getfield=dict_getter)


def test_optional() -> None:
    index: UniqueIndex[dict[str, typing.Any]] = UniqueIndex("id", required=False)
    
    obj1 = {"id": 1, "other": "foo"}
    obj2 = {"other": "bar"}
    obj3 = {"id": None, "other": "baz"}
    
    index.add(obj1, getfield=dict_getter)
    index.add(obj2, getfield=dict_getter)
    
    assert index.get(1) == obj1
    
    with pytest.raises(KeyError):
        index.get(None)
    
    index.add(obj3, getfield=dict_getter)
    
    with pytest.raises(KeyError):
        index.get(None)


def test_optional_none_valued() -> None:
    index: UniqueIndex[dict[str, typing.Any]] = UniqueIndex("id", required=False, none_as_value=True)
    
    obj1 = {"id": 1, "other": "foo"}
    obj2 = {"other": "bar"}
    obj3 = {"id": None, "other": "baz"}
    
    index.add(obj1, getfield=dict_getter)
    index.add(obj2, getfield=dict_getter)
    
    assert index.get(1) == obj1
    
    with pytest.raises(KeyError):
        index.get(None)
    
    index.add(obj3, getfield=dict_getter)
    
    assert index.get(None) == obj3


def test_get_overloads() -> None:
    index: UniqueIndex[dict[str, typing.Any]] = UniqueIndex("id")
    
    obj = {"id": 1}
    index.add(obj, getfield=dict_getter)
    
    assert index.get(1) == obj
    assert index.get(1, None) == obj
    assert index.get(2, None) is None
    
    with pytest.raises(TypeError):
        index.get()  # type: ignore
    
    with pytest.raises(TypeError):
        index.get(1, None, None)  # type: ignore
