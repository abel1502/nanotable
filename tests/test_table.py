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
    
    def test_of_objects_by_default(self) -> None:
        table = Table[MyObject]()\
            .primary_index_on("id")
        
        table.add(MyObject(1, "Foo"))

        assert table[1].name == "Foo"
        
        with pytest.raises(ValueError, match=r"[\'\"]id[\'\"]"):
            table.add({"id": 2, "name": "Bar"})  # type: ignore

    def test_primary_index(self) -> None:
        table = Table[MyObject]()
        
        table.add(MyObject(1, "Foo"))
        
        assert not table.has_primary_index
        
        with pytest.raises(PrimaryIndexError):
            table[1]
        
        table.primary_index_on("id")
        
        assert table.has_primary_index
        
        assert table[1].name == "Foo"
        assert table.primary_index[1].name == "Foo"
        assert table.by.id[1].name == "Foo"
        
        with pytest.raises(ValueError, match=r"[\'\"]id[\'\"]"):
            table.add({"id": 2, "name": "Bar"})

