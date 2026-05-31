from __future__ import annotations
import typing
import types
from contextlib import contextmanager
from functools import partial
import copy

from nanotable.index import Index, UniqueIndex
from nanotable.transaction import Transaction
from nanotable.storage import Storage, DummyStorage, IndexViewStorage
from nanotable.field import FieldGetterFactory, FieldGetter, getfield_attr, getfield_item, MISSING
from nanotable.errors import ConflictError, FeatureError


class Table[Elem, Indexes = _IndexDirectoryProxy[Elem], PrimaryIndex: Index[typing.Any] = Index[Elem]]:
    """
    A `Table` stores a collection of Python objects and indexes on them.
    It provides the functionality similar to a database + ORM, but without the associated
    overhead and fully within the Python interpreter.
    
    ### Storage
    
    The way a table stores its elements is defined by the chosen `Storage` subclass.
    It controls whether the objects are unordered, retain the insertion order or
    sorted; whether duplicates are allowed; if one of the fields acts as a primary
    key; and so on. Check out `nanotable.storage` for existing implementations or
    if you want to implement your own.
    
    If your table has at least one `required` index, you might not need a storage at all.
    In this case you can use an `IndexViewStorage`, which will make the chosen index act
    as the source of truth and the de-facto primary key for the table. You can also
    forego the storage parameter and simply use the `primary_key_on` method instead.
    
    ### Indexes
    
    Indexes provide a lookup for objects based on a certain property (usually referred to as a field).
    The semantics of an index are defined by the chosen `Index` subclass.
    In general, an index contains a `dict`, from the field value to the matching object or objects,
    which is updates every time an object is added or removed. Check out the `index_on` method for
    how to create an index for a table, and the `nanotable.index` module for existing implementations
    or if you want to implement your own.
    
    While normally a field is either an object attribute or a mapping item, you can use a custom
    function to define an ephemeral field. For example, this could be used to create an index
    on a pair of fields, or a nested field. See the `getfield` parameter in `index_on` for more details.
    Note, however, that it is generally recommended to define a `@property` on the object instead, where
    possible, for better clarity.
    
    ### Interface
    
    TODO: List key methods
    """
    
    __slots__ = (
        "_contents",
        "_getfield_factory",
        "_indexes",
    )
    
    _contents: Storage[Elem]
    _getfield_factory: FieldGetterFactory[Elem]
    _indexes: dict[str, Index[Elem]]
    
    def __init__(
        self,
        storage: Storage[Elem] | None = None,
        *,
        of: typing.Type[Elem] | None = None,
        of_objects: bool = False,
        of_dicts: bool = False,
        getfield_factory: FieldGetterFactory[Elem] | None = None,
    ):
        """
        Creates a table.
        
        The table can store arbitrary objects, so it needs to be instructed how to access their fields.
        The two most common configurations are object attributes (`foo.bar`), enabled with `of_objects=True`, and mapping items
        (`foo["bar"]`), enabled via `of_dicts=True`. `Table` can infer one of these two based on the intended type of its
        elements, provided via the `of` argument (if it is a `typing.Mapping`, `of_dicts` will be set to `True`;
        otherwise, `of_objects` will be set to `True`). Finally, you may specify an explicit `getfield_factory` to use.
        `of_objects=True` is equivalent to `getfield_factory=getfield_attr`, `of_dicts=True` is equivalent to
        `getfield_factory=getfield_item`. All four of `of`, `of_objects`, `of_dicts` and `getfield_factory` are mutually
        exclusive. If you don't specify anything, `of_objects` is assumed by default, but it is recommended to specify
        something explicitly for better compatibility with future versions of the library.
        
        You may specify the kind of storage the table will use to keep track of its elements with the `storage` argument.
        Different storage implementations have different semantics (element order, duplicates, etc.) and different
        performance tradeoffs. See `nanotable.storage` for the existing implementations and for help with creating your own.
        Make sure to understand the limitations of the chosen storage type before using it.
        
        If you don't specify `storage`, you must call `primary_index_on` to define a primary index before using the table.
        This will also create an `IndexViewStorage` for you. This is the recommended configuration for most cases,
        as it affords the best performance and memory efficiency. 
          
        :param storage: The storage to use. If not specified, you must call `primary_index_on` before using the table.
        :param of: The type of the objects intended to be stored in the table. If set, used to infer `of_objects` or `of_dicts`.
        :param of_objects: If `True`, the table stores objects.
        :param of_dicts: If `True`, the table stores dictionaries.
        :param getfield: A `FieldGetter` to use for this table. Used to switch between mapping item, object attribute and other definitions of a field.
        """
        
        if of is None and not of_objects and not of_dicts and getfield_factory is None:
            of_objects = True
        
        getfield_type_error = TypeError("You must specify one and only one of `of_objects`, `of_dicts` or a custom `getfield_factory` function when creating a table")
        
        if of is not None:
            if of_objects or of_dicts or getfield_factory is not None:
                raise getfield_type_error
            if isinstance(of, types.GenericAlias):
                of = of.__origin__
            if not isinstance(of, type):
                raise TypeError(f"`of` must be a type, not {type(of)}")
            if issubclass(of, typing.Mapping):
                getfield_factory = typing.cast(FieldGetterFactory[Elem], getfield_item)
            else:
                getfield_factory = typing.cast(FieldGetterFactory[Elem], getfield_attr)
        if of_objects:
            if of is not None or of_dicts or getfield_factory is not None:
                raise getfield_type_error
            getfield_factory = typing.cast(FieldGetterFactory[Elem], getfield_attr)
        elif of_dicts:
            if of is not None or of_objects or getfield_factory is not None:
                raise getfield_type_error
            getfield_factory = typing.cast(FieldGetterFactory[Elem], getfield_item)
        # elif getfield_factory is None:
        #     raise getfield_type_error
        
        assert getfield_factory is not None
        
        if storage is None:
            storage = DummyStorage()
        
        if not isinstance(storage, Storage):
            raise TypeError(f"storage must be an instance of Storage, not {type(storage)}")
        
        self._contents = storage
        self._getfield_factory = getfield_factory
        self._indexes = {}
        
        self._accommodate_primary_index()
    
    def _accommodate_primary_index(self) -> None:
        """
        Special handling to expose the primary index via `by`
        and to prevent duplicate updates.
        """
        
        if not isinstance(self._contents, IndexViewStorage):
            return
        
        self._contents.writethrough = False
        self._indexes[self._contents.index.name] = self._contents.index
    
    def primary_index_on(
        self,
        name: str,
        getfield: FieldGetter[Elem] | None = None,  # TODO: Rename to just field and accept strings. Parse them to handle nested fields and tuples?
        *,
        none_means_empty: bool = True,
        sorted: bool = False,
    ) -> typing.Self:
        """
        Creates a new primary index on a specific field.
        
        A primary index is a required unique index which is also used as the table's primary storage.
        If you specified a custom `storage` when creating the table, you don't need `primary_index_on`
        and should just use `index_on` for the same effect.
        
        .. Note::
            The primary index does not technically have to be unique, but a non-unique primary index
            involves significant performance tradeoffs (down to linear time for some operations).
            This function cannot create a non-unique primary index. If you really want to do so
            for some reason, use the `storage` parameter of the table constructor to pass
            `IndexViewStorage(MultiIndex(...))` instead.
        
        :param name: The name of the field to index by.
            TODO: Explain that it may be an actual field name or a description of what `getfield` does
            TODO Support a tuple which is automatically converted to `"foo_and_bar_and_baz"`?
        :param getfield: A `FieldGetter` retrieving the associated field.
            Defaults to the table's default `getfield` function for the speficied field.
        :param none_means_empty: If `False`, `None` is treated as a regular value.
            If `True`, `None` is treated the same as the lack of the indexed field.
            Defaults to `True`.
        
        :returns: The table instance for convenient chaining.
        
        :raises ConflictError: If the table already has a primary index or another custom storage configured.
        :raises ConflictError: If a different index with the same name already exists.
        """
        
        if not isinstance(self._contents, DummyStorage):
            custom_storage_desc = f"a custom storage of type {type(self._contents).__name__}"
            if isinstance(self._contents, IndexViewStorage):
                custom_storage_desc = f"another primary index on {self._contents.index.name!r}"
            
            raise ConflictError(
                f"Cannot create a primary index because the table already has {custom_storage_desc}",
            )
        
        if name in self._indexes:
            raise ConflictError(
                f"Cannot create a primary index on {name!r} because another index with that name already exists",
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
        
        self._contents = IndexViewStorage(index)
        self._accommodate_primary_index()
        
        return self
    
    def index_on(
        self,
        name: str,
        kind: type[Index] = UniqueIndex,  # TODO: Support inferring index kind from several flags?
        getfield: FieldGetter[Elem] | None = None,  # TODO: Rename to just field and accept strings. Parse them to handle nested fields and tuples?
        *,
        none_means_empty: bool = True,
        required: bool = False,
        **kwargs,
    ) -> typing.Self:
        """
        Creates a new index on a specific field.
        
        :param name: The name of the field to index by. This will also be the name of the index.
            TODO: Explain that it may be an actual field name or a description of what `getfield` does
            TODO Support a tuple which is automatically converted to `"foo_and_bar_and_baz"`?
        :param kind: The type of index to create. Defaults to UniqueIndex. See `nanotable.index` for the available index types.
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
    def at(self) -> PrimaryIndex:
        """
        Directly accesses the primary index, if one is configured.
        
        :raises TypeError: If the table has no primary index.
        """
        
        if not isinstance(self._contents, IndexViewStorage):
            raise TypeError(
                "This table has no primary index. Use `table.by.my_field` to access a specific index instead",
            )
        
        return typing.cast(PrimaryIndex, self._contents.index)
    
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
        
        .. Note::
            If `overwrite` is `True`, and an error happens while registering `elem`
            with one of the indexes, the order of the elements can be changed.
            Keep this in mind if you rely on the strict insertion order.
        
        :param elem: The element to add.
        :param overwrite: If `True`, overwrite the element if it already exists in the table.
        
        :raises ConflictError: If `overwrite` is `False` and the element has collisions on any indexed field.
        """
        
        with Transaction() as tx:
            self._contents.add(elem)
            tx.add_undo(partial(self._contents.remove, elem))
            
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
        
        .. Note::
            If an error happens while unregistering `elem` from one of
            the indexes, the order of the elements can be changed.
            Keep this in mind if you rely on the strict insertion order.
        
        :param elem: The element to remove.
        :param missing_ok: If `False`, the element must exist in the table.
        
        :raises KeyError: If `missing_ok` is `False` and the element does not exist in the table.
        """
        
        if not missing_ok and elem not in self:
            raise KeyError(f"Attempting to remove {elem!r} which is not in the table")
        
        with Transaction() as tx:
            self._contents.remove(elem)
            tx.add_undo(partial(self._contents.add, elem))
            
            for index in self._indexes.values():
                index.unregister(elem)
                tx.add_undo(partial(index.register, elem))

    def clear(self) -> None:
        """
        Removes all elements from the table.
        """
        
        self._contents.clear()
        
        for index in self._indexes.values():
            index.unregister_all()
    
    def extend(self, items: typing.Iterable[Elem], *, overwrite: bool = False) -> None:
        """
        Adds multiple elements to the table.
        
        :param items: The elements to add.
        :param overwrite: If `True`, overwrite the elements that already exist in the table.
        """
        
        for item in items:
            self.add(item, overwrite=overwrite)
    
    # TODO: transaction / backup / something? Maybe just a copy implementation? Or does deepcopy work out of the box?
    
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
        """
        Returns an iterable over the elements of the table.
        
        The order depends on the choice of storage. Unless you know otherwise,
        assume the order is unspecified.
        
        For a table with a unique primary key, the order will be the same as the insertion order.
        
        :returns: An iterable over the elements of the table.
        """
        
        return iter(self._contents)
    
    def __len__(self) -> int:
        return len(self._contents)
    
    def __contains__(self, item: object) -> bool:
        """
        Checks if the item is an element of the table.
        
        :param item: The element to check for.
        
        :returns: `True` if the item is in the table.
        """
        
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
