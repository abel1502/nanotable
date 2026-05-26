from __future__ import annotations
import typing

import pytest

import nanotable.index
from nanotable.index import UniqueIndex, PrimaryIndex, MultiIndex
from nanotable.field import getfield_item
from nanotable.errors import ValidationError
from nanotable.safety import IndexedFieldChangedWarning


def test_exports() -> None:
    exported = nanotable.index.__all__
    
    assert "Index" in exported
    assert "UniqueIndex" in exported
    assert "PrimaryIndex" in exported
    assert "MultiIndex" in exported


class TestUniqueIndex:
    def create(self, **kwargs) -> UniqueIndex[dict[str, typing.Any]]:
        return UniqueIndex("id", getfield_item, **kwargs)
    
    def test_normal(self) -> None:
        index = self.create(required=True)
        
        obj1 = {"id": 1, "other": "foo"}
        obj2 = {"id": 2, "other": "bar"}
        obj3 = {"id": 3, "other": "baz"}
        
        index.register(obj1)
        index.register(obj2)
        index.register(obj3)
        
        assert index.get(1) == obj1
        assert index.get(2) == obj2
        assert index.get(3) == obj3
        
        with pytest.raises(KeyError):
            index.get(4)
        
        index.unregister(obj1)
        
        with pytest.raises(KeyError):
            index.get(1)
        
        assert index.get(1, "hello") == "hello"
        assert index.get(2, "hello") == obj2
        
        with pytest.raises(KeyError):
            index.unregister(obj1)
        
        index.unregister(obj1, missing_ok=True)
        index.unregister({"id": -1}, missing_ok=True)
        
        with pytest.raises(ValueError):
            index.unregister({}, missing_ok=True)

        with pytest.raises(ValueError):
            index.register({})

        with pytest.raises(ValueError):
            index.register({"id": None})

        index.register({"id": 1, "other": None})


    def test_none_valued(self) -> None:
        index = self.create(required=True, none_means_empty=False)
        
        obj = {"id": None, "other": "foo"}
        
        with pytest.raises(KeyError):
            index.get(None)
        
        index.register(obj)
        
        assert index.get(None) == obj
        
        with pytest.raises(ValidationError):
            index.register(obj)


    def test_optional(self) -> None:
        index = self.create(required=False)
        
        obj1 = {"id": 1, "other": "foo"}
        obj2 = {"other": "bar"}
        obj3 = {"id": None, "other": "baz"}
        
        index.register(obj1)
        index.register(obj2)
        
        assert index.get(1) == obj1
        
        with pytest.raises(KeyError):
            index.get(None)
        
        index.register(obj3)
        
        with pytest.raises(KeyError):
            index.get(None)
        
        assert len(index) == 1
        index.unregister(obj3)
        assert len(index) == 1

    def test_optional_none_valued(self) -> None:
        index = self.create(required=False, none_means_empty=False)
        
        obj1 = {"id": 1, "other": "foo"}
        obj2 = {"other": "bar"}
        obj3 = {"id": None, "other": "baz"}
        
        index.register(obj1)
        index.register(obj2)
        
        assert index.get(1) == obj1
        
        with pytest.raises(KeyError):
            index.get(None)
        
        index.register(obj3)
        
        assert index.get(None) == obj3


    def test_get_overloads(self) -> None:
        index = self.create(required=True)
        
        obj = {"id": 1}
        index.register(obj)
        
        assert index.get(1) == obj
        assert index.get(1, None) == obj
        assert index.get(2, None) is None
        
        with pytest.raises(TypeError):
            index.get()  # type: ignore
        
        with pytest.raises(TypeError):
            index.get(1, None, None)  # type: ignore
    
    def test_safety_checks(self) -> None:
        index = self.create(required=True)
        
        obj = {"id": 1, "foo": "bar"}
        index.register(obj)
        
        obj["id"] = 2
        
        with pytest.warns(IndexedFieldChangedWarning):
            index.get(1)
        
        with pytest.warns(IndexedFieldChangedWarning):
            index[1]
        
        with pytest.raises(KeyError):
            index[2]
        
        with pytest.warns(IndexedFieldChangedWarning):
            # Note: keep this, otherwise a warning may show up at a random future point when `__del__` is called
            index.unregister_all()
    
    def test_mapping(self) -> None:
        index = self.create(required=True)
        
        obj1 = {"id": 1, "extra": "foo"}
        obj2 = {"id": 2, "extra": "baz"}
        obj3 = {"id": 3, "extra": "baz"}
        
        index.register(obj1)
        index.register(obj2)
        index.register(obj3)
        
        assert set(index.keys()) == {1, 2, 3}
        assert sorted(list(index.values()), key=lambda x: x["id"]) == [obj1, obj2, obj3]
        assert sorted(list(index.items())) == [(1, obj1), (2, obj2), (3, obj3)]
        
        assert 1 in index
        assert -1 not in index
        
        assert len(index) == 3
        
        assert set(index) == set(index.keys())
    
    def test_no_slice(self) -> None:
        index = self.create(required=True)
        
        with pytest.raises(TypeError):
            index[:]


class TestPrimaryIndex:
    def create(self, **kwargs) -> PrimaryIndex[dict[str, typing.Any]]:
        return PrimaryIndex("id", getfield_item, **kwargs)
    
    def test_defaults(self) -> None:
        index = self.create()
        
        assert isinstance(index, UniqueIndex)
        assert index.required
        
        with pytest.raises(TypeError):
            self.create(required=False)


class TestMultiIndex:
    def create(self, **kwargs) -> MultiIndex[dict[str, typing.Any]]:
        return MultiIndex("id", getfield_item, **kwargs)
    
    def test_normal(self) -> None:
        index = self.create(required=True)
        
        obj1 = {"id": 1, "other": "foo"}
        obj2 = {"id": 2, "other": "bar"}
        obj3 = {"id": 3, "other": "baz"}
        
        index.register(obj1)
        index.register(obj2)
        index.register(obj3)
        
        assert index.get(1) == [obj1]
        assert index.get(2) == [obj2]
        assert index.get(3) == [obj3]
        
        assert index.get(4) == []
        
        index.unregister(obj1)
        
        assert index.get(1) == []
        
        assert index.get(1, [{"hello": "world"}]) == [{"hello": "world"}]
        assert index.get(2, []) == [obj2]
        
        with pytest.raises(KeyError):
            index.unregister(obj1)
        
        index.unregister(obj1, missing_ok=True)
        index.unregister({"id": -1}, missing_ok=True)
        
        with pytest.raises(ValueError):
            index.unregister({}, missing_ok=True)

        with pytest.raises(ValueError):
            index.register({})

        with pytest.raises(ValueError):
            index.register({"id": None})

        index.register(obj1)
        index.register(obj1)
        
        assert index.get(1) == [obj1, obj1]
        
        index.register({"id": 1, "other": None})
        
        assert len(index.get(1)) == 3
        assert {"id": 1, "other": None} in index.get(1)
        
        index.unregister(obj1)
        index.unregister(obj1)
        index.unregister(index.get(1)[0])
        
        assert index.get(1) == []

