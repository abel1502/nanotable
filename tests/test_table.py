from __future__ import annotations
import typing
import dataclasses

import pytest

import nanotable.table
from nanotable.table import Table


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
        

