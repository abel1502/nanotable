from __future__ import annotations
import typing
from contextlib import contextmanager
from functools import partial

from nanotable.index import UniqueIndex
from nanotable.transaction import Transaction
from nanotable.field import FieldGetter


class Table[Elem, Indexes = _IndexDirectoryProxy[Elem]]:
    __slots__ = (
        "_contents",
        "_getfield",
        "_indexes",
        "by",
    )
    
    _contents: list[Elem]
    _getfield: FieldGetter[Elem]
    _indexes: dict[str, UniqueIndex[Elem]]
    
    by: Indexes
    
    # TODO: Dedicated primary index, which could let us get rid of a contents list.
    # TODO: Construct from initial elements? Maybe not, if we want to build the "schema" first...
    # TODO: Maybe replace `getfield` with `store_mappings` and `store_objects`? If both, pick depending on `isinstance(..., typing.Mapping)`
    def __init__(self, getfield: FieldGetter[Elem]):
        self._contents = []  # TODO: Remove and rely on a primary index. Cannot guarantee the order anyway -- for example, when recovering from an error during `add`
        self._getfield = getfield
        self._indexes = {}  # TODO: Unify with `by`
        
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
    
    def add(self, elem: Elem, *, overwrite: bool = False) -> None:
        with Transaction() as tx:
            self._contents.append(elem)
            tx.add_undo(self._contents.pop)
            
            for index in self._indexes.values():
                key = self._getfield(elem, index.key_field)
                
                if overwrite and key in index:
                    old = index[key]
                    self.remove(old)
                    tx.add_undo(partial(self.add, old))
                
                index.register(key, elem)
                tx.add_undo(partial(index.unregister, key, elem))
    
    def remove(self, elem: Elem, *, missing_ok: bool = False) -> None:
        # TODO: Also make a transaction? Shouldn't normally fail
        
        if not missing_ok and elem not in self._contents:
            raise KeyError(f"Attempting to remove {elem!r} which is not in the table")
        
        self._contents.remove(elem)
        
        for index in self._indexes.values():
            index.unregister(self._getfield(elem, index.key_field), elem)
    
    # TODO: Also need to issue warnings when changes in indexed attributes are detected! Check when using an index and in a table's `__del__`.
    # And document that they are supposed to be immutable except with `rekey`.
    # TODO:
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
    
    def __getattr__(self, name: str) -> typing.Mapping[typing.Any, Elem]:
        try:
            return self.table._indexes[name]
        except KeyError:
            raise AttributeError(f"Table has no index on {name!r}") from None
