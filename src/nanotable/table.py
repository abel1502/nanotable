from __future__ import annotations
import typing
from contextlib import contextmanager
from functools import partial

from nanotable.index import Index, UniqueIndex
from nanotable.transaction import Transaction
from nanotable.field import FieldGetterFactory, FieldGetter, getfield_attr, getfield_item, MISSING
from nanotable.errors import PrimaryIndexError, FeatureError


class Table[Elem, Indexes = _IndexDirectoryProxy[Elem]]:
    """
    A `Table` is a generalization of a `dict`, something similar to an SQL table.
    
    A `Table` stores regular Python objects and allows you to look them up based on certain properties.
    
    Under the hood, it uses several `dict`s (and sometimes a `list`) to store the data and
    provide efficient access to it both in terms of memory and time.
    
    TODO: List methods
    
    ## TEMPORARY brainstorming: (TODO: Remove)
    
    - A table is a collection of elements.
    - Duplicates are not expressly forbidden.
    - Elements have fields in some sense.
    - A table can have indexes for lookup based on these fields.
    - Indexes are notified of changes to the table.
    - Indexes maintain internal state and provide lookups faster than a linear scan.
    - Indexes may impose constraints on the indexed fields (hashable, unique, comparable, etc.).
    - Tables and indexes must be as performant as an improvised data structure
      built of `dict`s, `list`s and other standard containers for the specific task,
      except possibly a small overhead term corresponding to the added abstraction
      layers where inevitable.
    
    - Does a table allow duplicates? Yes.
    - Is a table ordered?
      - In general, I don't think I need to preserve insertion order. Maybe for consistency with `dict`?
      - If multiple values returned from an index (`.get_many()` for a collection of keys?,
        `.get` on multi-indexes, `.get_range()` on sorted indexes, ...) are to be wrapped in a table,
        order would be significant. The upside to returning a table would be inclusion of stuff like
        `filter` (or `where` or `select` or `query`, idk). But table's stateful functionality, like
        indexes, would be useless there. Perhaps a separate storage abstraction?
    
    - Let's say a separate storage abstraction, okay. What are the alternatives?
      - `list`. Arbitrary order. Allows duplicates. Slow.
      - `SortedList`. Order of increasing elements (or of some property of them). Allows duplicates. Fast.
      - `set`. No order. No duplicates. Fast. Requires hashability.
      - `SortedSet`. Order of increasing elements (or of some property of them). No duplicates. Fast. Requires comparability.
      - `UniqueIndex(required=True)` (primary key index). No order (can be tightened to insertion order if need be).
        No duplicates or primary key collisions. Fast. Requires a hashable primary key.
      - `SortedUniqueIndex(required=True)` (sorted primary key index). Order of increasing primary keys.
        No duplicates or primary key collisions. Fast. Requires a comparable primary key.
      - More alternatives?
    - Can I think of an interface for a wrapper around any of these, allowing to take advantage of the strengths of all of these? "Group".
      - Do I want a storage to be convenient when used standalone? Probably yes.
      - Maybe the mutable interface is (documented as) package-private? As in, for a user this is supposed to be a powerful view.
      - In general, a sequence of items. Sometimes also a mapping which is partially contradictory.
        - Maybe drop the index-backed variants?
        - Or reimplement them with an external index (one they don't own and only query)?
          That deprives the group of convenient primary-index access.
    """
    
    __slots__ = (
        "_contents",
        "_getfield_factory",
        "_indexes",
    )
    
    # TODO: instead of list[Elem], use Group[Elem]?
    _contents: list[Elem] | UniqueIndex[Elem]
    _getfield_factory: FieldGetterFactory[Elem]
    _indexes: dict[str, Index[Elem]]
    
    def __init__(
        self,
        *,
        of_objects: bool = False,
        of_dicts: bool = False,
        getfield_factory: FieldGetterFactory[Elem] | None = None,
    ):
        """
        Creates an empty table.
        
        :param of_objects: If `True`, the table stores objects. If `of_dicts` and `getfield` aren't set, this defaults to `True`.
        :param of_dicts: If `True`, the table stores dictionaries.
        :param getfield: A `FieldGetter` to use for this table. Used to switch between mapping item, object attribute and other definitions of a field.
        """
        
        if not of_objects and not of_dicts and getfield_factory is None:
            of_objects = True
        
        getfield_type_error = TypeError("You must specify either `of_objects`, `of_dicts` or a custom `getfield_factory` function when creating a table")
        
        if of_objects:
            if of_dicts or getfield_factory is not None:
                raise getfield_type_error
            getfield_factory = typing.cast(FieldGetterFactory[Elem], getfield_attr)
        elif of_dicts:
            if of_objects or getfield_factory is not None:
                raise getfield_type_error
            getfield_factory = typing.cast(FieldGetterFactory[Elem], getfield_item)
        # elif getfield_factory is None:
        #     raise getfield_type_error
        
        assert getfield_factory is not None
        
        self._contents = []
        self._getfield_factory = getfield_factory
        self._indexes = {}
    
    def primary_index_on(
        self,
        name: str,
        getfield: FieldGetter[Elem] | None = None,
        *,
        none_means_empty: bool = True,
        sorted: bool = False,
    ) -> typing.Self:
        """
        Creates a new primary index on a specific field.
        A table can only have one primary index.
        
        .. Note::
            While not obligatory, a primary index is recommended where applicable.
            Without one, the table has to store all of its elements in a `list` (since in the general case the elements might not be hashable),
            so certain operations may take linear time. This includes `Table.remove`, `Table.add` with `overwrite=True`, and possibly more.
        
        :param name: The name of the field to index by.
        :param getfield: A `FieldGetter` retrieving the associated field.
            Defaults to the table's default `getfield` function for the speficied field.
        :param none_means_empty: If `False`, `None` is treated as a regular value.
            If `True`, `None` is treated the same as the lack of the indexed field.
            Defaults to `True`.
        
        :returns: The table instance for convenient chaining.
        
        :raises PrimaryIndexError: If a primary index couldn't be created.
        """
        
        if self.has_primary_index:
            raise PrimaryIndexError(
                f"Cannot create new primary index on {name!r} because a primary index already exists on {self.primary_index.name!r}",
            )
        
        if name in self._indexes:
            raise PrimaryIndexError(
                f"Cannot create new primary index on {name!r} because another index already exists on {name!r}",
            )
        
        kind: type[UniqueIndex[Elem]] = UniqueIndex
        
        if sorted:
            try:
                from nanotable.index import SortedUniqueIndex
            except ImportError:
                raise FeatureError("sorted")
            
            kind = SortedUniqueIndex
        
        if getfield is None:
            getfield = self._getfield_factory(name)
        
        index: UniqueIndex[Elem] = kind(
            name,
            getfield,
            none_means_empty=none_means_empty,
            required=True,
        )
        
        for item in self._contents:
            index.register(item)
        
        self._contents = index
        self._indexes[name] = index
        
        return self
    
    def index_on(
        self,
        name: str,
        kind: type[Index] = UniqueIndex,
        # TODO: Support inferring index kind from several flags?
        getfield: FieldGetter[Elem] | None = None,
        *,
        none_means_empty: bool = True,
        required: bool = False,
        **kwargs,
    ) -> typing.Self:
        """
        Creates a new index on a specific field.
        
        :param name: The name of the field to index by. This will also be the name of the index.
        :param kind: The type of index to create. Defaults to UniqueIndex. TODO: List available types.
        :param getfield: A `FieldGetter` retrieving the associated field.
            Defaults to the table's default `getfield` function for the speficied field.
        :param none_means_empty: If `True`, a `None` value for the field is treated the same as the absence of the field.
            If `False`, `None` is treated as a regular value.
            Defaults to `True`.
        :param required: If `True`, all objects must have a value for the field.
            If `False`, objects without a value for the field are ignored.
            Defaults to `False`.
        :param kwargs: Other keyword arguments to the index constructor.
        
        :returns: The table instance for convenient chaining.
        
        :raises KeyError: If an index with this name already exists.
        """
        
        if not issubclass(kind, Index):
            raise TypeError(f"Index type {kind} must be a subclass of Index")
        
        if name in self._indexes:
            raise KeyError(
                f"Cannot create new index on {name!r} because another index with this name already exists",
            )
        
        if getfield is None:
            getfield = self._getfield_factory(name)
        
        self._indexes[name] = kind(
            name,
            getfield,
            none_means_empty=none_means_empty,
            required=required,
            **kwargs,
        )
        
        return self
    
    # TODO: drop_index?
    
    @property
    def has_primary_index(self) -> bool:
        """
        Whether this table has a primary index.
        """
        
        return isinstance(self._contents, UniqueIndex)
    
    @property
    def primary_index(self) -> UniqueIndex[Elem]:
        """
        The primary index of the table, if any.
        
        :raises PrimaryIndexError: If the table has no primary index.
        """
        
        if not self.has_primary_index:
            raise PrimaryIndexError("Table has no primary index")
        
        return typing.cast(UniqueIndex[Elem], self._contents)
    
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
        
        :raises ConflictError: If `overwrite` is `False` and the element has collisions on any indexed field.
        """
        
        with Transaction() as tx:
            if not self.has_primary_index:
                typing.cast(list[Elem], self._contents).append(elem)
                tx.add_undo(typing.cast(list[Elem], self._contents).pop)
            
            for index in self._indexes.values():
                if overwrite:
                    key = index.getfield(elem)
                    if key in index:
                        for other_elem in list(index.result_items(index[key])):
                            self.remove(other_elem)
                            tx.add_undo(partial(self.add, other_elem))
                
                index.register(elem)
                tx.add_undo(partial(index.unregister, elem))
    
    def remove(self, elem: Elem, *, missing_ok: bool = False) -> None:
        """
        Remove an element from the table.
        
        :param elem: The element to remove.
        :param missing_ok: If `False`, the element must exist in the table.
        
        :raises KeyError: If `missing_ok` is `False` and the element does not exist in the table.
        """
        
        # TODO: Also wrap in a transaction? Shouldn't normally fail
        
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
    
    def extend(self, items: typing.Iterable[Elem], *, overwrite: bool = False) -> None:
        """
        Adds multiple elements to the table.
        
        :param items: The elements to add.
        :param overwrite: If `True`, overwrite the elements that already exist in the table.
        """
        
        for item in items:
            self.add(item)
    
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
    
    def rekey_on(self, obj: Elem, *fields: str) -> typing.Generator[None, None, None]:
        """
        A context manager that allows to change values of indexed fields in a safe manner.
        
        This is a slightly more performant but more fragile version of `Table.rekey`.
        Instead of removing `obj` from the table fully, it only unregisters it
        from the indexes on specified `fields`. Accordingly, it is only safe to change
        the indexed fields passed as arguments to `rekey_on` in the `with` block of
        this function.
        
        .. Note::
            See the documentation for `Table.rekey` for why this is needed.
        
        :param obj: The object whose fields you want to change.
        :param fields: The fields whose values you want to change.
        
        :returns: A context manager (to be used in a `with` block).
        
        :raises KeyError: If the object is not in the table.
        """
        
        for field in fields:
            self._indexes[field].unregister(obj)
        
        yield
        
        for field in fields:
            self._indexes[field].register(obj)
        
    
    def __iter__(self) -> typing.Iterator[Elem]:
        return iter(self.items())
    
    def __len__(self) -> int:
        return len(self._contents)
    
    @typing.overload
    def __getitem__(self, keys: slice[typing.Any | None, typing.Any | None, None]) -> typing.Iterable[Elem]:
        """
        Looks up elements by a range of primary keys.
        
        .. Note::
            Only available with a sorted primary index!
        
        :param keys: The range of primary keys to look up.
        
        :returns: The sequence of matching elements.
        
        :raises PrimaryIndexError: If the table has no primary index.
        """
    
    @typing.overload
    def __getitem__(self, key: typing.Any) -> Elem:
        """
        Looks up an element by its primary key.
        
        :param key: The primary key to look up.
        
        :returns: The element with the given primary key.
        
        :raises PrimaryIndexError: If the table has no primary index.
        """
    
    def __getitem__(self, key: typing.Any | slice):
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
            key = self.primary_index.getfield(item)
            
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
