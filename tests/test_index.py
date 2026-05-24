from __future__ import annotations
import typing

import pytest

from nanotable.index import UniqueIndex


def register(index: UniqueIndex[dict[str, typing.Any]], obj: dict[str, typing.Any], **kwargs) -> None:
    index.register(obj["id"], obj, **kwargs)


def unregister(index: UniqueIndex[dict[str, typing.Any]], obj: dict[str, typing.Any], **kwargs) -> None:
    index.unregister(obj["id"], obj, **kwargs)


def test_normal() -> None:
    index: UniqueIndex[dict[str, typing.Any]] = UniqueIndex("id")
    
    obj1 = {"id": 1, "other": "foo"}
    obj2 = {"id": 2, "other": "bar"}
    obj3 = {"id": 3, "other": "baz"}
    
    register(index, obj1)
    register(index, obj2)
    register(index, obj3)
    
    assert index.get(1) == obj1
    assert index.get(2) == obj2
    assert index.get(3) == obj3
    
    with pytest.raises(KeyError):
        index.get(4)
    
    unregister(index, obj1)
    
    with pytest.raises(KeyError):
        index.get(1)
    
    assert index.get(1, "hello") == "hello"
    assert index.get(2, "hello") == obj2
    
    with pytest.raises(KeyError):
        unregister(index, obj1)
    
    unregister(index, obj1, missing_ok=True)
    unregister(index, {"id": -1}, missing_ok=True)
    
    with pytest.raises(ValueError):
        unregister(index, {}, missing_ok=True)

    with pytest.raises(ValueError):
        register(index, {})

    with pytest.raises(ValueError):
        register(index, {"id": None})

    register(index, {"id": 1, "other": None})


def test_none_valued() -> None:
    index: UniqueIndex[dict[str, typing.Any]] = UniqueIndex("id", none_as_value=True)
    
    obj = {"id": None, "other": "foo"}
    
    with pytest.raises(KeyError):
        index.get(None)
    
    register(index, obj)
    
    assert index.get(None) == obj
    
    with pytest.raises(KeyError):
        register(index, obj)


def test_optional() -> None:
    index: UniqueIndex[dict[str, typing.Any]] = UniqueIndex("id", required=False)
    
    obj1 = {"id": 1, "other": "foo"}
    obj2 = {"other": "bar"}
    obj3 = {"id": None, "other": "baz"}
    
    register(index, obj1)
    register(index, obj2)
    
    assert index.get(1) == obj1
    
    with pytest.raises(KeyError):
        index.get(None)
    
    register(index, obj3)
    
    with pytest.raises(KeyError):
        index.get(None)


def test_optional_none_valued() -> None:
    index: UniqueIndex[dict[str, typing.Any]] = UniqueIndex("id", required=False, none_as_value=True)
    
    obj1 = {"id": 1, "other": "foo"}
    obj2 = {"other": "bar"}
    obj3 = {"id": None, "other": "baz"}
    
    register(index, obj1)
    register(index, obj2)
    
    assert index.get(1) == obj1
    
    with pytest.raises(KeyError):
        index.get(None)
    
    register(index, obj3)
    
    assert index.get(None) == obj3


def test_get_overloads() -> None:
    index: UniqueIndex[dict[str, typing.Any]] = UniqueIndex("id")
    
    obj = {"id": 1}
    register(index, obj)
    
    assert index.get(1) == obj
    assert index.get(1, None) == obj
    assert index.get(2, None) is None
    
    with pytest.raises(TypeError):
        index.get()  # type: ignore
    
    with pytest.raises(TypeError):
        index.get(1, None, None)  # type: ignore
