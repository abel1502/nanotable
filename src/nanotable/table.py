from __future__ import annotations
import typing
from contextlib import contextmanager

from nanotable.index import UniqueIndex
from nanotable.transaction import Transaction
from nanotable.field import FieldGetter


class Table[Elem, Indexes = _IndexDirectoryProxy[Elem]]:
    __slots__ = (
        "_contents",
        "_getfield",
        "_indexes",
        "_by",
    )
    
    _contents: list[Elem]
    _getfield: FieldGetter[Elem]
    _indexes: dict[str, UniqueIndex[Elem]]
    
    by: Indexes
    
    # TODO: Dedicated primary index, which could let us get rid of a contents list.
    def __init__(self, getfield: FieldGetter[Elem]):
        self._contents = []
        self._getfield = getfield
        self._indexes = {}
        
        self.by = typing.cast(Indexes, _IndexDirectoryProxy(self))
    
    def index_on(
        self,
        key_field: str,
        *,
        none_as_value: bool = False,
        required: bool = True,
    ) -> typing.Self:
        # TODO: Only create unique indexes for now
        self._indexes[key_field] = UniqueIndex(key_field, none_as_value=none_as_value, required=required)
        return self
    
    def add(self, elem: Elem) -> None:
        with Transaction() as tx:
            self._contents.append(elem)
            tx.add_undo(self._contents.pop)
            
            for index in self._indexes.values():
                index.register(self._getfield(elem), elem)
                tx.add_undo(lambda: index.unregister(self._getfield(elem), elem))
    
    def remove(self, elem: Elem) -> None:
        # TODO: Also make a transaction? Shouldn't normally fail
        
        self._contents.remove(elem)
        
        for index in self._indexes.values():
            index.unregister(self._getfield(elem), elem)
    
    # TODO: Also need to issue warnings when changes in indexed attributes are detected!
    # And document that they are supposed to be immutable except with `rekey`.
    @contextmanager
    def rekey(self, obj: Elem) -> typing.Generator[None, None, None]:
        self.remove(obj)
        yield
        self.add(obj)


class _IndexDirectoryProxy[Elem]:
    __slots__ = ("table",)
    
    table: Table[Elem, typing.Any]
    
    def __init__(self, table: Table[Elem, typing.Any]):
        self.table = table
    
    def __getattr__(self, name: str) -> _IndexProxy[Elem]:
        index = self.table._indexes.get(name, None)
        
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
        self.table.remove(self[key])
