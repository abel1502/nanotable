from __future__ import annotations
import typing
from contextlib import contextmanager
from functools import partial

from nanotable.index import Index, UniqueIndex
from nanotable.transaction import Transaction
from nanotable.field import FieldGetter


class Table[Elem, Indexes = _IndexDirectoryProxy[Elem]]:
    __slots__ = (
        "_contents",
        "_getfield",
        "_indexes",
    )
    
    _contents: list[Elem]
    _getfield: FieldGetter[Elem]
    _indexes: dict[str, Index[Elem]]
    
    # TODO: Dedicated primary index, which could let us get rid of a contents list.
    # TODO: Construct from initial elements? Maybe not, if we want to build the "schema" first...
    # TODO: Maybe replace `getfield` with `store_mappings` and `store_objects`? If both, pick depending on `isinstance(..., typing.Mapping)`
    def __init__(self, getfield: FieldGetter[Elem]):
        """
        TODO
        """
        
        self._contents = []  # TODO: Remove and rely on a primary index. Cannot guarantee the order anyway -- for example, when recovering from an error during `add`
        self._getfield = getfield
        self._indexes = {}
    
    def index_on(
        self,
        field: str,
        kind: type[Index] = UniqueIndex,
        *,
        primary: bool = False,
        none_means_empty: bool = False,
        required: bool = False,
        **kwargs,
    ) -> typing.Self:
        """
        Creates a new index on a specific field.
        
        :param field: The name of the field to index by. This will also be the name of the index.
        :param kind: The type of index to create. Defaults to UniqueIndex. TODO: List available types.
        :param primary: TODO
        :param none_means_empty: If `True`, a `None` value for the field is treated the same as the absence of the field.
        :param required: If `True`, all objects must have a value for the field.
        :param kwargs: Other keyword arguments to the index constructor.
        
        :returns: The table instance for convenient chaining.
        """
        
        if not issubclass(kind, Index):
            raise TypeError(f"Index type {kind} must be a subclass of Index") 
        
        self._indexes[field] = kind(
            field,
            self._getfield,
            none_means_empty=none_means_empty,
            required=required,
            **kwargs,
        )
        
        return self
    
    @property
    def by(self) -> Indexes:
        """
        Use this to access the indexes.
        
        For example, `table.by.first_name` gives you the index on the `first_name` field.
        
        The index must first be created with `Table.index_on`.
        
        :returns: A proxy object with the indexes as attributes.
        """
        
        return typing.cast(Indexes, _IndexDirectoryProxy(self._indexes))
    
    def add(self, elem: Elem, *, overwrite: bool = False) -> None:
        """
        TODO
        """
        
        with Transaction() as tx:
            self._contents.append(elem)
            tx.add_undo(self._contents.pop)
            
            for index in self._indexes.values():
                if overwrite:
                    key = self._getfield(elem, index.on_field)
                    if key in index:
                        old = index[key]
                        self.remove(old)
                        tx.add_undo(partial(self.add, old))
                
                index.register(elem)
                tx.add_undo(partial(index.unregister, elem))
    
    def remove(self, elem: Elem, *, missing_ok: bool = False) -> None:
        """
        TODO
        """
        
        # TODO: Also make a transaction? Shouldn't normally fail
        
        if not missing_ok and elem not in self:
            raise KeyError(f"Attempting to remove {elem!r} which is not in the table")
        
        self._contents.remove(elem)
        
        for index in self._indexes.values():
            index.unregister(elem)
    
    # TODO: Also need to issue warnings when changes in indexed attributes are detected! Check when using an index and in a table's `__del__`.
    # And document that they are supposed to be immutable except with `rekey`.
    @contextmanager
    def rekey(self, obj: Elem) -> typing.Generator[None, None, None]:
        """
        A context manager that allows to change values of indexed fields in a safe manner.
        This is a simple wrapper around removing the object from the table and adding it back.
        
        .. Note::
            If you change an indexed field without this or equivalent precautions, the table will
            enter an inconsistent state! Since there is no real way to catch this in the general
            case, while the package will warn you when it detects this happening, it is up to you
            to make sure to avoid this.
        
        :param obj: The object whose fields you want to change.
        
        :returns: A context manager (to be used in a `with` block).
        
        :raises KeyError: If the object is not in the table.
        """
        
        self.remove(obj)
        yield
        self.add(obj)
    
    def __iter__(self) -> typing.Iterator[Elem]:
        return iter(self._contents)
    
    def __contains__(self, item: object) -> bool:
        return item in self._contents


class _IndexDirectoryProxy[Elem]:
    __slots__ = ("_indexes",)
    
    _indexes: dict[str, Index[Elem]]
    
    def __init__(self, indexes: dict[str, Index[Elem]]):
        self._indexes = indexes
    
    def __getattr__(self, name: str) -> Index[Elem]:
        try:
            return self._indexes[name]
        except KeyError:
            raise AttributeError(f"Table has no index on {name!r}") from None


__all__ = [
    "Table",
]
