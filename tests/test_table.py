from __future__ import annotations
import typing
import dataclasses

import pytest

import nanotable.table
from nanotable.table import Table
import nanotable.field
from nanotable.errors import PrimaryIndexError


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
        table = Table[MyObject](of_objects=True)
        
        table.add(MyObject(1, "Foo"))
        table.add(MyObject(2, "Bar", something_incomprehensible=lambda x: x(x)))
        
        assert len(table) == 2
        
        table.add(MyObject(1, "Foo"))
        assert len(table) == 3
        
        table.remove(MyObject(1, "Foo"))
        assert len(table) == 2
        
        # Doesn't actually overwrite without a primary index to define object identity
        # TODO: Implicit object identity as the primary index? The downside would be that tables couldn't hold duplicates.
        table.add(MyObject(1, "Foo"), overwrite=True)
        assert len(table) == 3
        
        table.remove(MyObject(1, "Foo"))
        assert len(table) == 2
        
        table.clear()
        assert len(table) == 0
    
    def test_getfield_options(self) -> None:
        t = Table[typing.Any]()
        assert t._getfield_factory is nanotable.field.getfield_attr
        
        t = Table(of_objects=True)
        assert t._getfield_factory is nanotable.field.getfield_attr
        
        t = Table(of_dicts=True)
        assert t._getfield_factory is nanotable.field.getfield_item
        
        t = Table(getfield_factory=lambda name: lambda obj: 123)
        assert t._getfield_factory("foo")(None) == 123
        
        with pytest.raises(TypeError):
            Table(of_objects=True, of_dicts=True)
        
        with pytest.raises(TypeError):
            Table(of_objects=True, getfield_factory=nanotable.field.getfield_attr)
        
        with pytest.raises(TypeError):
            Table(of_dicts=True, getfield_factory=nanotable.field.getfield_item)
    
    def test_primary_index_collision(self) -> None:
        table = Table[MyObject]()
        
        table.index_on("id")
        
        with pytest.raises(PrimaryIndexError, match=r"another index already exists"):
            table.primary_index_on("id")

    def test_primary_index(self) -> None:
        table = Table[MyObject]()
        
        table.add(MyObject(1, "Foo"))
        
        assert len(table) == 1
        assert not table.has_primary_index
        
        with pytest.raises(PrimaryIndexError):
            table[1]
        
        table.primary_index_on("id")
        
        assert len(table) == 1
        assert table.has_primary_index
        
        assert table[1].name == "Foo"
        assert table.primary_index[1].name == "Foo"
        assert table.by.id[1].name == "Foo"
        
        table.add(MyObject(2, "Bar"))
        
        assert len(table) == 2
        
        assert table[1].name == "Foo"
        assert table[2].name == "Bar"
        assert table.primary_index[1].name == "Foo"
        assert table.primary_index[2].name == "Bar"
        assert table.by.id[1].name == "Foo"
        assert table.by.id[2].name == "Bar"
        
        with pytest.raises(PrimaryIndexError, match=r"primary index already exists"):
            table.primary_index_on("name")
    
    def test_unique_index(self) -> None:
        table = Table[MyObject]()
        
        table.add(MyObject(1, "Foo"))
        
        # TODO
        
        

