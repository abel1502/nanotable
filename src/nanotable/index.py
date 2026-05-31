from __future__ import annotations
import typing
from abc import ABC, abstractmethod
import itertools

from nanotable.field import FieldGetter, MISSING, typeof_MISSING
from nanotable.errors import ConflictError
from nanotable.safety import disable_safety_checks, verify_immutable_key


# TODO: Factor out the code for storing stuff in a dict into a separate subclass?
class Index[
    Obj,
    Result = typing.Any,
    Key = typing.Any,
](ABC, typing.Mapping[Key, Result]):
    """
    The base class for all indexes.
    
    Largely provides a default implementation. While this is known to impact flexibility,
    it also offers guarantees to the user. If you wish to write a custom index and cannot
    figure out a way to make the typing work with inheriting from Index, create an
    issue on GitHub with an explanation of your use case and I'll consider generalizing
    this base class for you.
    """
    
    __slots__ = (
        "_lookup",
        "name",
        "getfield",
        "none_means_empty",
        "required",
    )
    
    _lookup: typing.MutableMapping[Key, Result]
    name: str
    getfield: FieldGetter[Obj]
    none_means_empty: bool
    required: bool
    
    def __init__(
        self,
        name: str,
        getfield: FieldGetter[Obj],
        *,
        none_means_empty: bool = True,
        required: bool = False,
    ):
        """
        :param name: The name of the index. Used for error messages.
        :param getfield: A `FieldGetter` to use for this index. For any object,
            it should return the indexed field's value or `MISSING`. Used to switch
            between mapping item, object attribute and other definitions of a field.
        :param none_means_empty: If `False`, `None` is treated as a regular value.
            If `True`, `None` is treated the same as the lack of the indexed field.
            Defaults to `True`.
        :param required: If `True`, all objects must have a value for the indexed field.
            If `False`, objects without a value for the indexed field are ignored.
            Defaults to `False`.
        """
        
        self._lookup = self._init_lookup()
        self.name = name
        self.getfield = getfield
        self.none_means_empty = none_means_empty
        self.required = required
    
    @classmethod
    def _init_lookup(cls) -> typing.MutableMapping[Key, Result]:
        """
        Index-specific implementation for creating the underlying storage. Normally a `dict`.
        """
        
        return {}
    
    def register(self, elem: Obj) -> None:
        """
        Adds an element to the index.
        
        :param elem: The element to add.
        
        :raises ValueError: If the element has no value for the index field and it is required.
        :raises ConflictError: If the element already exists in the index.
        """
        
        key = self.getfield(elem)
        
        if key is None and self.none_means_empty:
            key = MISSING
        
        if key is MISSING:
            if self.required:
                self._no_required_field(elem)
            return
        
        key = typing.cast(Key, key)

        self._register(key, elem)
    
    @abstractmethod
    def _register(self, key: Key, elem: Obj) -> None:
        """
        Index-specific implementation for `register`.
        
        :param key: The key to add. Guaranteed to match the field of `elem`.
        :param elem: The element to add.
        
        :raises ConflictError: If the element already exists in the index.
        """
    
    def unregister(self, elem: Obj, *, missing_ok: bool = False) -> None:
        """
        Removes an element from the index.
        
        :param elem: The element to remove.
        :param missing_ok: If `False`, the element must exist in the index. Defaults to `False`.
        
        :raises ValueError: If the element has no value for the index field and it is required.
        :raises KeyError: If `missing_ok` is `False` and the element does not exist in the index.
        """
        
        key = self.getfield(elem)
        
        if key is None and self.none_means_empty:
            key = MISSING
        
        if key is MISSING:
            if self.required:
                self._no_required_field(elem)
            return
        
        key = typing.cast(Key, key)
        
        if key in self._lookup:
            self._unregister(key, elem)
        elif not missing_ok:
            raise KeyError(f"Key {key!r} not found in index on {self.name!r}")
    
    @abstractmethod
    def _unregister(self, key: Key, elem: Obj) -> None:
        """
        Index-specific implementation for `unregister`.
        
        :param key: The key to remove. Guaranteed to match the field of `elem`. Guaranteed to be in the index.
        :param elem: The element to remove.
        """
    
    def unregister_all(self) -> None:
        """
        Removes all elements from the index.
        """
        
        if not disable_safety_checks:
            for key, result in self.items():
                for obj in self.result_items(result):
                    verify_immutable_key(key, self.getfield(obj), obj, self.name)
        
        self._lookup.clear()
    
    def _no_required_field(self, elem: Obj) -> None:
        error_msg: str = f"Element {elem!r} has no field for the required index on {self.name!r}."
        
        if isinstance(elem, typing.Mapping) and self.name in elem:
            raise ValueError(
                f"{error_msg} The element appears to have a mapping item named {self.name!r} instead. "
                f"Consider passing `of_dicts=True` to the table constructor, or `getfield_item` as "
                f"`getfield` to the index constructor.",
            )
        elif hasattr(elem, self.name):
            raise ValueError(
                f"{error_msg} The element appears to have an object attribute named {self.name!r} instead. "
                f"Consider passing `of_objects=True` to the table constructor, or `getfield_attr` as "
                f"`getfield` to the index constructor.",
            )
        
        raise ValueError(error_msg)
    
    @typing.overload
    def get(self, key: Key, /) -> Result:
        """
        Retrieves the element(s) with the given key.
        
        :param key: The key to look up.
        
        :returns: The element(s) with the given key.
        
        :raises KeyError: If the key is not found in the index.
        """
    
    @typing.overload
    def get[Default](self, key: Key, default: Default, /) -> Result | Default:
        """
        Retrieves the element(s) with the given key, or `default` if the key is not found in the index.
        
        :param key: The key to look up.
        :param default: The value to return if the key is not found in the index.
        
        :returns: The element(s) with the given key, or `default` if the key is not found in the index.
        """
    
    def get(self, key, *args):
        if len(args) > 1:
            raise TypeError(f"get() has no overload with {len(args) + 1} positional arguments")
        
        result = self._lookup.get(key, MISSING)
        
        if result is MISSING:
            if len(args) == 0:
                result = self._get_default(key)
            else:
                result = self._lookup.get(key, args[0])
            
        elif not disable_safety_checks:
            for obj in self.result_items(result):
                verify_immutable_key(key, self.getfield(obj), obj, self.name)
        
        return result
    
    def _get_default(self, key: Key) -> Result:
        """
        Index-specific implementation for the behavior of `get` when the key is not in the lookup table.
        
        Defaults to raising a `KeyError`.
        
        :param key: The key to look up.
        
        :returns: The element(s) associated with the given key.
        
        :raises KeyError: If the index decides to treat the absence of the key as an error.
        """
        
        raise KeyError(f"Key {key!r} not found in index on {self.name!r}")
    
    def _get_slice(self, keys: slice[Key | None, Key | None, None]) -> typing.Iterable[Obj]:
        """
        Index-specific implementation for the behavior of `__getitem__` when the key is a slice.
        
        Defaults to raising a `TypeError`.
        
        :param keys: The slice to look up.
        
        :returns: The elements matching the lookup.
        
        :raises TypeError: If the index does not support slicing.
        """
        
        raise TypeError(f"Slicing not supported for {type(self).__name__}")
    
    @typing.overload
    def __getitem__(self, keys: slice[Key | None, Key | None, None]) -> typing.Iterable[Obj]:
        ...  # Note: Supports ranged queries, raises an exception on non-sorted indexes
    
    @typing.overload
    def __getitem__(self, key: Key) -> Result:
        ...

    def __getitem__(self, key: Key | slice[Key | None, Key | None, None]):
        if isinstance(key, slice):
            return self._get_slice(key)
        
        return self.get(key)
    
    def __contains__(self, key: object) -> bool:
        return key in self._lookup
    
    def __len__(self) -> int:
        return len(self._lookup)
    
    def __iter__(self) -> typing.Iterator[Key]:
        return iter(self._lookup)
    
    @typing.override
    def keys(self) -> typing.KeysView[Key]:
        """
        Returns the keys of the objects registered in the index.
        The order is unspecified.
        """
        
        return self._lookup.keys()
    
    @typing.override
    def values(self) -> typing.ValuesView[Result]:
        """
        Returns the objects registered in the index.
        The order is unspecified.
        """
        
        return self._lookup.values()
    
    @typing.override
    def items(self) -> typing.ItemsView[Key, Result]:
        """
        Returns the key-object pairs for the objects registered in the index.
        The order is unspecified.
        """
        
        return self._lookup.items()
    
    def __del__(self) -> None:  # pragma: no cover # A destructor like this is impossible to test naturally
        try:
            if disable_safety_checks:
                return
            
            for key, result in self.items():
                for obj in self.result_items(result):
                    verify_immutable_key(key, self.getfield(obj), obj, self.name)
        except:
            # Nothing is guaranteed for a destructor, so we can't guarantee anything either
            # In particular, I encountered situations where the index had no `_lookup` attribute
            # in __del__, which it had just prior.
            pass
    
    @abstractmethod
    def result_items(self, result: Result) -> typing.Iterable[Obj]:
        """
        Unpacks a results into a sequence of individual objects.
        """


class UniqueIndex[Obj, Key = typing.Any](Index[Obj, Obj, Key]):
    """
    A unique index lets you look up the single element with a certain value of one of the fields.
    """
    
    @typing.override
    def _register(self, key: Key, elem: Obj) -> None:
        if key in self._lookup:
            old_elem = self._lookup[key]
            raise ConflictError(f"Duplicate value {key!r} for the unique index on {self.name!r} (existing object: {old_elem!r}, new object: {elem!r})")
        
        self._lookup[key] = elem
    
    @typing.override
    def _unregister(self, key: Key, elem: Obj) -> None:
        self._lookup.pop(key, None)
    
    @typing.override
    def result_items(self, result: Obj) -> typing.Iterable[Obj]:
        return [result]


# TODO: instead of list[Obj], use Group[Obj]
class MultiIndex[Obj, Key = typing.Any](Index[Obj, list[Obj], Key]):
    """
    A multi-index is an index that lets you look up all elements
    with a certain value of one of their fields.
    It is essentially the opposite of UniqueIndex.
    
    When an index has no elements matching a certain key, the result in an empty list,
    not a `KeyError`.
    """
    
    @typing.override
    def _register(self, key: Key, elem: Obj) -> None:
        if key not in self._lookup:
            self._lookup[key] = []
        
        self._lookup[key].append(elem)
    
    @typing.override
    def _unregister(self, key: Key, elem: Obj) -> None:
        self._lookup[key].remove(elem)
        
        if not self._lookup[key]:
            self._lookup.pop(key, None)
    
    @typing.override
    def result_items(self, result: list[Obj]) -> typing.Iterable[Obj]:
        return result
    
    @typing.override
    def _get_default(self, key: Key) -> list[Obj]:
        return []


__all__ = [
    "Index",
    "UniqueIndex",
    "MultiIndex",
]


try:
    from sortedcontainers import SortedDict  # type: ignore[import-not-found]
    
    if typing.TYPE_CHECKING:
        from sortedcontainers import SortedKeysView, SortedValuesView, SortedItemsView  # type: ignore[import-not-found]
    
    
    class _SortedIndexMixin[Obj, Result = typing.Any, Key = typing.Any](Index[Obj, Result, Key]):
        _lookup: SortedDict[Key, Result]
        
        @classmethod
        @typing.override
        def _init_lookup(cls) -> SortedDict[Key, Result]:
            return SortedDict()
        
        def get_range(
            self,
            *,
            low: Key | None = None,
            high: Key | None = None,
            low_inclusive: bool = True,
            high_inclusive: bool = True,
            reverse: bool = False,
        ) -> typing.Iterator[Obj]:
            """
            Retrieves all elements whose keys fall in the range from `low` to `high`.
            
            :param low: The lower bound of the range.
                If `None`, the lower bound is effectively the lowest possible key.
            :param high: The upper bound of the range.
                If `None`, the upper bound is effectively the highest possible key.
            :param low_inclusive: Whether the lower bound is inclusive.
                Ignored if `low` is `None`. Defaults to `True`.
            :param high_inclusive: Whether the upper bound is inclusive.
                Ignored if `high` is `None`. Defaults to `True`.
            :param reverse: Whether to iterate over the elements in reverse order.
                `low` should still be less than or equal to `high`, else you will get an empty result.
            
            :returns: An iterator over the elements whose keys fall in the range `[low:high]`.
            """
            
            # Need the type annotation to help mypy consistently pick the correct overload
            resolve_key: typing.Callable[[Key], typing.Iterable[Obj]] = lambda key: self.result_items(self[typing.cast(Key, key)])
            
            return itertools.chain.from_iterable(map(resolve_key, self._lookup.irange(
                low,
                high,
                inclusive=(low_inclusive, high_inclusive),
                reverse=reverse,
            )))

        @typing.override
        def _get_slice(self, keys: slice[Key | None, Key | None, None]) -> typing.Iterable[Obj]:
            if keys.step is not None:
                raise TypeError("SortedUniqueIndex range query may only include `low:high`, a step is meaningless")
            
            return self.get_range(
                low=keys.start,
                high=keys.stop,
                low_inclusive=True,
                high_inclusive=False,
            )
        
        @typing.override
        def keys(self) -> SortedKeysView[Key]:
            """
            Returns the keys of the objects registered in the index, in sorted order.
            """
            
            return self._lookup.keys()
        
        @typing.override
        def values(self) -> SortedValuesView[Result]:
            """
            Returns the ovjects registered in the index, in sorted order of their keys.
            """
            
            return self._lookup.values()
        
        @typing.override
        def items(self) -> SortedItemsView[Key, Result]:
            """
            Returns the key-object pairs for the objects registered in the index, in sorted order of their keys.
            """
            
            return self._lookup.items()
    
    
    class SortedUniqueIndex[Obj, Key = typing.Any](_SortedIndexMixin[Obj, Obj, Key], UniqueIndex[Obj, Key]):
        """
        A variant of UniqueIndex that also maintains the sorted order of
        the keys, enabling efficient range queries.
        """
    
    
    class SortedMultiIndex[Obj, Key = typing.Any](_SortedIndexMixin[Obj, list[Obj], Key], MultiIndex[Obj, Key]):
        """
        A variant of MultiIndex that also maintains the sorted order of
        the keys, enabling efficient range queries.
        
        .. Note::
            The order of the elements with the same value of the indexed field
            returned for any ranged query is unspecified.
        """
    
    
    __all__ += [
        "SortedUniqueIndex",
        "SortedMultiIndex",
    ]
except ModuleNotFoundError:
    pass
