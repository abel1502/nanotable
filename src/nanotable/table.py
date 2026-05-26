from __future__ import annotations
import typing
from contextlib import contextmanager
from functools import partial

from nanotable.index import Index, PrimaryIndex, UniqueIndex
from nanotable.transaction import Transaction
from nanotable.field import FieldGetter, attr_getter, dict_getter, MISSING
from nanotable.errors import PrimaryIndexError


class Table[Elem, Indexes = _IndexDirectoryProxy[Elem]]:
    """
    A `Table` is a generalization of a `dict`, something similar to an SQL table.
    
    A `Table` stores regular Python objects and allows you to look them up based on certain properties.
    
    Under the hood, it uses several `dict`s (and sometimes a `list`) to store the data and
    provide efficient access to it both in terms of memory and time.
    
    TODO: List methods
    """
    
    __slots__ = (
        "_contents",
        "_getfield",
        "_indexes",
    )
    
    _contents: list[Elem] | PrimaryIndex[Elem]
    _getfield: FieldGetter[Elem]
    _indexes: dict[str, Index[Elem]]
    
    def __init__(
        self,
        *,
        of_objects: bool = False,
        of_dicts: bool = False,
        getfield: FieldGetter[Elem] | None = None,
    ):
        """
        TODO
        
        :param of_objects: If `True`, the table stores objects. Defaults to `False`.
        :param of_dicts: If `True`, the table stores dictionaries. Defaults to `False`.
        :param getfield: A `FieldGetter` to use for this table. Used to switch between mapping item, object attribute and other definitions of a field.
        """
        
        # TODO: Default to of_objects, or to trying one then the other?
        
        getfield_type_error = TypeError("You must specify either `of_objects`, `of_dicts` or a custom `getfield` function when creating a table")
        
        if of_objects:
            if of_dicts or getfield is not None:
                raise getfield_type_error
            getfield = typing.cast(FieldGetter[Elem], attr_getter)
        elif of_dicts:
            if of_objects or getfield is not None:
                raise getfield_type_error
            getfield = typing.cast(FieldGetter[Elem], dict_getter)
        elif getfield is None:
            raise getfield_type_error
        
        self._contents = []
        self._getfield = getfield
        self._indexes = {}
    
    def primary_index_on(
        self,
        field: str,
        *,
        none_means_empty: bool = True,
    ) -> typing.Self:
        """
        Creates a new primary index on a specific field.
        A table can only have one primary index.
        
        .. Note::
            While not obligatory, a primary index is recommended where applicable.
            Without one, the table has to store all of its elements in a `list` (since in the general case the elements might not be hashable),
            so certain operations may take linear time. This includes `Table.remove`, `Table.add` with `overwrite=True`, and possibly more.
        
        :param field: The name of the field to index by.
        :param none_means_empty: If `False`, `None` is treated as a regular value.
            If `True`, `None` is treated the same as the lack of the `on_field` attribute.
            Defaults to `True`.
        
        :returns: The table instance for convenient chaining.
        
        :raises PrimaryIndexError: If a primary index already exists.
        """
        
        if self.has_primary_index:
            raise PrimaryIndexError(
                f"Cannot create new primary index on {field!r} because a primary index already exists on {self.primary_index.on_field!r}",
            )
        
        index: PrimaryIndex[Elem] = PrimaryIndex(field, self._getfield, none_means_empty=none_means_empty)
        
        for item in self._contents:
            index.register(item)
        
        self._contents = index
        
        return self
    
    def index_on(
        self,
        field: str,
        kind: type[Index] = UniqueIndex,
        *,
        none_means_empty: bool = True,
        required: bool = False,
        **kwargs,
    ) -> typing.Self:
        """
        Creates a new index on a specific field.
        
        :param field: The name of the field to index by. This will also be the name of the index.
        :param kind: The type of index to create. Defaults to UniqueIndex. TODO: List available types.
        :param primary: Marks the index
        :param none_means_empty: If `True`, a `None` value for the field is treated the same as the absence of the field.
            If `False`, `None` is treated as a regular value.
            Defaults to `True`.
        :param required: If `True`, all objects must have a value for the field.
            If `False`, objects without a value for the field are ignored.
            Defaults to `False`.
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
    def has_primary_index(self) -> bool:
        """
        Whether this table has a primary index.
        """
        
        return isinstance(self._contents, PrimaryIndex)
    
    @property
    def primary_index(self) -> PrimaryIndex[Elem]:
        """
        The primary index of the table, if any.
        
        :raises PrimaryIndexError: If the table has no primary index.
        """
        
        if not self.has_primary_index:
            raise PrimaryIndexError("Table has no primary index")
        
        return typing.cast(PrimaryIndex[Elem], self._contents)
    
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
        Adds an element to the table.
        
        :param elem: The element to add.
        :param overwrite: If `True`, overwrite the element if it already exists in the table.
        """
        
        with Transaction() as tx:
            if not self.has_primary_index:
                typing.cast(list[Elem], self._contents).append(elem)
                tx.add_undo(typing.cast(list[Elem], self._contents).pop)
            
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
        Remove an element from the table.
        
        :param elem: The element to remove.
        :param missing_ok: If `False`, the element must exist in the table.
        
        :raises KeyError: If `missing_ok` is `False` and the element does not exist in the table.
        """
        
        # TODO: Also make a transaction? Shouldn't normally fail
        
        if not missing_ok and elem not in self:
            raise KeyError(f"Attempting to remove {elem!r} which is not in the table")
        
        if not self.has_primary_index:
            typing.cast(list[Elem], self._contents).remove(elem)
        
        for index in self._indexes.values():
            index.unregister(elem)

    def clear(self) -> None:
        """
        Removes all elements from the table.
        """
        
        if not self.has_primary_index:
            typing.cast(list, self._contents).clear()
        
        for index in self._indexes.values():
            index.unregister_all()
    
    # TODO: extend
    
    # TODO: transaction / backup / something?
    
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
    
    # TODO: rekey_on() which only removes from and re-adds to specific indexes
    
    def __iter__(self) -> typing.Iterator[Elem]:
        return iter(self.items())
    
    def __len__(self) -> int:
        return len(self._contents)
    
    def __getitem__(self, key: typing.Any) -> Elem:
        """
        Looks up an element by its primary key.
        
        :param key: The primary key to look up.
        
        :returns: The element with the given primary key.
        
        :raises PrimaryIndexError: If the table has no primary index.
        """
        
        if not self.has_primary_index:
            raise PrimaryIndexError("Table has no primary index")
        
        return self.primary_index[key]
    
    def __contains__(self, item: object) -> bool:
        """
        Checks if the item is an element of the table, OR if an element with the specified primary key is in the table, if a table has a primary key defined.
        
        .. Note::
            If you only want to check the primary key, use `x in table.primary_index`.
            
            If you only want to check for the object presence, use `x in table.values()` (linear time, not recommended).
        
        :param item: The element or the primary key to check for.
        
        :returns: `True` if the item / the item with the given key is in the table.
        """
        
        if self.has_primary_index:
            if item in self.primary_index:
                return True
            
            item = typing.cast(Elem, item)
            key = self._getfield(item, self.primary_index.on_field)
            
            return key in self.primary_index and self.primary_index[key] == item
        
        return item in self._contents
    
    def items(self) -> typing.Iterable[Elem]:
        """
        Returns an iterable over the elements of the table. The order is unspecified.
        
        .. Note::
            The order will match the insertion order in many cases, but this is not guaranteed.
            In particular, if a `Table.add` call with `overwrite=True` fails, when restoring the
            table to the original state, it may bring some elements to the end (since it removes
            them initially, then adds them back during cleanup).
        
        :returns: An iterable over the elements of the table.
        """
        
        if self.has_primary_index:
            return self.primary_index.values()
        
        # TODO: ListView or something
        return iter(self._contents)


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
