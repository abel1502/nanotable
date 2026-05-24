from __future__ import annotations
import typing

from nanotable.index import UniqueIndex
from nanotable.transaction import Transaction
from nanotable.field import FieldGetter


class Table[Elem, Indexes = _IndexDirectoryProxy[Elem]]:
    __slots__ = ("contents", "getfield", "indexes")
    
    contents: list[Elem]
    getfield: FieldGetter[Elem]
    indexes: dict[str, UniqueIndex[Elem]]
    
    def __init__(self, getfield: FieldGetter[Elem]):
        self.contents = []
        self.getfield = getfield
        self.indexes = {}
    
    # TODO: Create index
    
    @property
    def by(self) -> Indexes:
        return _IndexDirectoryProxy(self)
    
    def add(self, elem: Elem) -> None:
        with Transaction() as tx:
            self.contents.append(elem)
            tx.add_undo(self.contents.pop)
            
            for index in self.indexes.values():
                index.add(elem, getfield=self.getfield)
                tx.add_undo(lambda: index.remove(elem, getfield=self.getfield))
    
    def remove(self, elem: Elem) -> None:
        self.contents.remove(elem)
        
        for index in self.indexes.values():
            index.remove(elem, getfield=self.getfield)


class _IndexDirectoryProxy[Elem]:
    __slots__ = ("table",)
    
    table: Table[Elem, typing.Any]
    
    def __init__(self, table: Table[Elem, typing.Any]):
        self.table = table
    
    def __getattr__(self, name: str) -> _IndexProxy[Elem]:
        index = self.table.indexes.get(name, None)
        
        if index is None:
            raise AttributeError(f"Table has no index on {name!r}")
        
        return _IndexProxy(self.table, index)


class _IndexProxy[Elem]:
    __slots__ = ("table", "index")
    
    table: Table[Elem, typing.Any]
    index: UniqueIndex[Elem]
    
    def __init__(
        self,
        table: Table[Elem, typing.Any],
        index: UniqueIndex[Elem],
    ):
        self.table = table
        self.index = index
    
    def __getitem__(self, key: typing.Any) -> Elem:
        return self.index.get(key)
    
    def get[Default](self, key: typing.Any, default: Default) -> Elem | Default:
        return self.index.get(key, default)

    def __delitem__(self, key: typing.Any):
        self.table.remove(key)
