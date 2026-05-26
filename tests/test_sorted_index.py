from __future__ import annotations
import typing

import pytest

pytest.importorskip("sortedcontainers")

import nanotable.index
from nanotable.index import SortedUniqueIndex, SortedPrimaryIndex, SortedMultiIndex
from nanotable.field import getfield_item

def test_exports() -> None:
    exported = nanotable.index.__all__
    
    assert "SortedUniqueIndex" in exported
    assert "SortedPrimaryIndex" in exported
    assert "SortedMultiIndex" in exported


class TestSortedUniqueIndex:
    def create(self, **kwargs) -> SortedUniqueIndex[dict[str, typing.Any]]:
        return SortedUniqueIndex("id", getfield_item, **kwargs)
    
    def test_inherits_unique(self) -> None:
        index = self.create(required=True)
        
        assert isinstance(index, nanotable.index.UniqueIndex)

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
    
    def test_slice_range_access(self) -> None:
        index = self.create(required=True)
        
        for i in range(1, 6):
            index.register({"id": i})
        
        assert index[1] == {"id": 1}
        assert index[3] == {"id": 3}
        assert index[5] == {"id": 5}
        
        assert list(index[2:4]) == [{"id": 2}, {"id": 3}]
        assert list(index[2:]) == [{"id": 2}, {"id": 3}, {"id": 4}, {"id": 5}]
        assert list(index[:4]) == [{"id": 1}, {"id": 2}, {"id": 3}]
        assert list(index[:]) == [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}, {"id": 5}]
        
        with pytest.raises(TypeError):
            index[::-1]
    
    def test_range_access_bounds(self) -> None:
        index = self.create(required=True)
        
        for i in range(1, 6):
            index.register({"id": i})
        
        assert list(index.get_range(
            low=2,
            high=4,
            low_inclusive=True,
            high_inclusive=True,
        )) == [{"id": 2}, {"id": 3}, {"id": 4}]
        
        assert list(index.get_range(
            low=2,
            high=4,
            low_inclusive=False,
            high_inclusive=True,
        )) == [{"id": 3}, {"id": 4}]
        
        assert list(index.get_range(
            low=2,
            high=4,
            low_inclusive=True,
            high_inclusive=False,
        )) == [{"id": 2}, {"id": 3}]
        
        assert list(index.get_range(
            low=2,
            high=4,
            low_inclusive=False,
            high_inclusive=False,
        )) == [{"id": 3}]
        
        assert list(index.get_range(
            low=2,
            high=2,
        )) == [{"id": 2}]
        
        assert list(index.get_range(
            low=2,
            high=2,
            high_inclusive=False
        )) == []
        
        assert list(index.get_range(
            low=2,
            high=2,
            low_inclusive=False
        )) == []
    
    def test_range_access_reverse(self) -> None:
        index = self.create(required=True)
        
        for i in range(1, 6):
            index.register({"id": i})
        
        assert list(index.get_range(
            low=2,
            high=4,
            low_inclusive=True,
            high_inclusive=True,
            reverse=True,
        )) == [{"id": 4}, {"id": 3}, {"id": 2}]
        
        assert list(index.get_range(
            low=2,
            high=4,
            low_inclusive=True,
            high_inclusive=False,
            reverse=True,
        )) == [{"id": 3}, {"id": 2}]
        
        assert list(index.get_range(
            low=2,
            high=4,
            low_inclusive=False,
            high_inclusive=True,
            reverse=True,
        )) == [{"id": 4}, {"id": 3}]


class TestSortedPrimaryIndex:
    def create(self, **kwargs) -> SortedPrimaryIndex[dict[str, typing.Any]]:
        return SortedPrimaryIndex("id", getfield_item, **kwargs)
    
    def test_inherits_unique(self) -> None:
        index = self.create()
        
        assert isinstance(index, SortedUniqueIndex)
    
    def test_inherits_primary(self) -> None:
        index = self.create()
        
        assert isinstance(index, nanotable.index.PrimaryIndex)
    
    def test_defaults(self) -> None:
        index = self.create()
        
        assert index.required
        
        with pytest.raises(TypeError):
            self.create(required=False)


class TestSortedMultiIndex:
    def create(self, **kwargs) -> SortedMultiIndex[dict[str, typing.Any]]:
        return SortedMultiIndex("id", getfield_item, **kwargs)
    
    def test_inherits_multi(self) -> None:
        index = self.create()
        
        assert isinstance(index, nanotable.index.MultiIndex)
    
    # TODO: Tests

