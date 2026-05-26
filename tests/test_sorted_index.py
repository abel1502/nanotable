from __future__ import annotations
import typing

import pytest

pytest.importorskip("sortedcontainers")

import nanotable.index
from nanotable.index import SortedUniqueIndex
from nanotable.field import dict_getter

def test_public() -> None:
    exported = nanotable.index.__all__
    
    assert "SortedUniqueIndex" in exported
    # assert "SortedMultiIndex" in exported


class TestSortedUniqueIndex:
    def create(self, **kwargs) -> SortedUniqueIndex[dict[str, typing.Any]]:
        return SortedUniqueIndex("id", dict_getter, **kwargs)
    
    def test_inherits_unique(self) -> None:
        index = self.create(required=True)
        
        assert isinstance(index, SortedUniqueIndex)

    def test_sorted(self) -> None:
        index = self.create(required=True)
        
        obj1 = {"id": 1, "other": "foo"}
        obj2 = {"id": 5, "other": "bar"}
        obj3 = {"id": 3, "other": "baz"}
        
        index.register(obj1)
        index.register(obj2)
        index.register(obj3)
        
        assert list(index.keys()) == [1, 3, 5]
        assert list(index.values()) == [obj1, obj3, obj2]
        assert list(index.items()) == [(1, obj1), (3, obj3), (5, obj2)]
        
        index.unregister(obj2)
        
        assert list(index.keys()) == [1, 3]
        assert list(index.values()) == [obj1, obj3]
        assert list(index.items()) == [(1, obj1), (3, obj3)]

        with pytest.raises(TypeError):
            index.register({"id": "not comparable with ints"})

