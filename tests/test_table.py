from __future__ import annotations
import typing
import dataclasses

import pytest

import nanotable.table
from nanotable.table import Table
from nanotable.storage import MultiListStorage
from nanotable.field import getfield_attr, getfield_item
from nanotable.errors import ConflictError, UnfinishedTableError


def test_exports() -> None:
    exports = nanotable.table.__all__
    
    assert "Table" in exports

@dataclasses.dataclass()
class MyObject:
    id: int
    name: str
    something_incomprehensible: typing.Any = None


class TestTable:
    def test_no_index(self) -> None:
        table = Table(storage=MultiListStorage(), of=MyObject)
        
        table.add(MyObject(1, "Foo"))
        table.add(MyObject(2, "Bar", something_incomprehensible=lambda x: x(x)))
        
        assert len(table) == 2
        
        table.add(MyObject(1, "Foo"))
        assert len(table) == 3
        
        table.remove(MyObject(1, "Foo"))
        assert len(table) == 2
        
        # Doesn't overwrite with a MultiListStorage
        table.add(MyObject(1, "Foo"), overwrite=True)
        assert len(table) == 3
        
        table.remove(MyObject(1, "Foo"))
        assert len(table) == 2
        
        table.clear()
        assert len(table) == 0
    
    def test_getfield_options(self) -> None:
        t = Table[typing.Any]()
        assert t._getfield_factory is getfield_attr
        
        t = Table(of=dict)
        assert t._getfield_factory is getfield_item
        
        t = Table(of=dict[str, typing.Any])
        assert t._getfield_factory is getfield_item
        
        t = Table(of=MyObject)
        assert t._getfield_factory is getfield_attr
        
        t = Table(of_objects=True)
        assert t._getfield_factory is getfield_attr
        
        t = Table(of_dicts=True)
        assert t._getfield_factory is getfield_item
        
        t = Table(getfield_factory=lambda name: lambda obj: 123)
        assert t._getfield_factory("foo")(None) == 123
        
        with pytest.raises(TypeError):
            Table(of_objects=True, of_dicts=True)
        
        with pytest.raises(TypeError):
            Table(of_objects=True, getfield_factory=getfield_attr)
        
        with pytest.raises(TypeError):
            Table(of_dicts=True, getfield_factory=getfield_item)
    
    def test_primary_index_collision(self) -> None:
        table = Table[MyObject]()
        
        table.index_on("id")
        
        with pytest.raises(ConflictError, match=r"another index with that name already exists"):
            table.primary_index_on("id")

    def test_primary_index(self) -> None:
        table = Table[MyObject]()
        
        obj = MyObject(1, "Foo")
        
        with pytest.raises(UnfinishedTableError, match=r"primary_index_on"):
            table.add(obj)
        
        with pytest.raises(UnfinishedTableError, match=r"primary_index_on"):
            len(table)
        
        table.primary_index_on("id")
        
        table.add(obj)
        
        assert len(table) == 1
        assert obj in table
        assert table.at[1] == obj
        
        table.add(MyObject(2, "Bar"))
        
        assert len(table) == 2
        assert table.at[1].name == "Foo"
        assert table.at[2].name == "Bar"
        assert table.by.id[1].name == "Foo"
        assert table.by.id[2].name == "Bar"
        
        with pytest.raises(ConflictError, match=r"another primary index"):
            table.primary_index_on("name")
    
    def test_unique_index(self) -> None:
        table = Table(MultiListStorage(), of=MyObject)
        
        table.add(MyObject(1, "Foo"))
        
        # TODO

