from __future__ import annotations
import typing
from abc import ABC, abstractmethod
import warnings

from nanotable.field import FieldGetter, MISSING, typeof_MISSING
from nanotable.errors import ValidationError
from nanotable.safety import disable_safety_checks, verify_immutable_key


# TODO: Factor out the code for storing stuff in a dict into a separate subclass. OrderedIndex (or SortedIndex, however I might call that) probably wouldn't use a dict
class Index[Obj, Result = typing.Any, Key = typing.Any](ABC, typing.Mapping[Key, Result]):
    __slots__ = (
        "_lookup",
        "on_field",
        "getfield",
        "none_means_empty",
        "required",
    )
    
    _lookup: dict[Key, Result]
    on_field: str
    getfield: FieldGetter
    none_means_empty: bool
    required: bool
    
    def __init__(
        self,
        on_field: str,
        getfield: FieldGetter,
        *,
        none_means_empty: bool = True,
        required: bool = False,
    ):
        """
        :param on_field: The name of the field to index by.
        :param getfield: A `FieldGetter` to use for this index. Used to switch
            between mapping item, object attribute and other definitions of a field.
        :param none_means_empty: If `False`, `None` is treated as a regular value.
            If `True`, `None` is treated the same as the lack of the `on_field` attribute.
            Defaults to `True`.
        :param required: If `True`, all objects must have a value for `on_field`.
            If `False`, objects without a value for `on_field` are ignored.
            Defaults to `False`.
        """
        
        self._lookup = {}
        self.on_field = on_field
        self.getfield = getfield
        self.none_means_empty = none_means_empty
        self.required = required
    
    def register(self, elem: Obj) -> None:
        """
        Adds an element to the index.
        
        :param elem: The element to add.
        
        :raises ValueError: If the element has no value for the index field and it is required.
        :raises ValidationError: If registering the element would violate some of the index invariants.
        """
        
        key = self.getfield(elem, self.on_field)
        
        if key is None and self.none_means_empty:
            key = MISSING
        
        if key is MISSING:
            if self.required:
                raise ValueError(f"Element {elem!r} has no {self.on_field!r} field which is required")
            return
        
        key = typing.cast(Key, key)

        self._register(key, elem)
    
    @abstractmethod
    def _register(self, key: Key, elem: Obj) -> None:
        """
        Index-specific implementation for `register`.
        
        :param key: The key to add. Guaranteed to match the field of `elem`.
        :param elem: The element to add.
        
        :raises ValidationError: If registering the element would violate some of the index invariants.
        """
    
    def unregister(self, elem: Obj, *, missing_ok: bool = False) -> None:
        """
        Removes an element from the index.
        
        :param elem: The element to remove.
        :param missing_ok: If `False`, the element must exist in the index. Defaults to `False`.
        
        :raises ValueError: If the element has no value for the index field and it is required.
        :raises KeyError: If `missing_ok` is `False` and the element does not exist in the index.
        """
        
        key = self.getfield(elem, self.on_field)
        
        if key is None and self.none_means_empty:
            key = MISSING
        
        if key is MISSING:
            if self.required:
                raise ValueError(f"Element {elem!r} has no {self.on_field!r} field which is required")
            return
        
        key = typing.cast(Key, key)
        
        if key in self._lookup:
            self._unregister(key, elem)
        elif not missing_ok:
            raise KeyError(f"Key {key!r} not found in index by {self.on_field!r}")
    
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
            for key, obj in self.items():
                verify_immutable_key(key, self.getfield(obj, self.on_field), obj, self.on_field)
        
        self._lookup.clear()
    
    @typing.overload
    def get(self, key: typing.Any, /) -> Result:
        """
        Retrieves the element with the given key.
        
        :param key: The key to look up.
        
        :returns: The element with the given key.
        
        :raises KeyError: If the key is not found in the index.
        """
    
    @typing.overload
    def get[Default](self, key: typing.Any, default: Default, /) -> Result | Default:
        """
        Retrieves the element with the given key, or `default` if the key is not found in the index.
        
        :param key: The key to look up.
        :param default: The value to return if the key is not found in the index.
        
        :returns: The element with the given key, or `default` if the key is not found in the index.
        """
    
    def get(self, key, *args):
        if len(args) == 1:
            return self._lookup.get(key, args[0])
        
        if len(args) != 0:
            raise TypeError(f"get() has no overload with {len(args) + 1} positional arguments")
        
        result = self._lookup.get(key, MISSING)
        
        if result is MISSING:
            raise KeyError(f"Key {key!r} not found in index on {self.on_field!r}")
        
        if not disable_safety_checks:
            verify_immutable_key(key, self.getfield(result, self.on_field), result, self.on_field)
        
        return result

    def __getitem__(self, key: Key) -> Result:
        return self.get(key)
    
    def __contains__(self, key: object) -> bool:
        return key in self._lookup
    
    def __len__(self) -> int:
        return len(self._lookup)
    
    def __iter__(self) -> typing.Iterator[Key]:
        return iter(self._lookup)
    
    @typing.override
    def keys(self) -> typing.KeysView[Key]:
        return self._lookup.keys()
    
    @typing.override
    def values(self) -> typing.ValuesView[Result]:
        return self._lookup.values()
    
    @typing.override
    def items(self) -> typing.ItemsView[Key, Result]:
        return self._lookup.items()
    
    def __del__(self) -> None:
        if disable_safety_checks:
            return
        
        for key, obj in self.items():
            verify_immutable_key(key, self.getfield(obj, self.on_field), obj, self.on_field)


class UniqueIndex[Obj, Key = typing.Any](Index[Obj, Obj, Key]):
    """
    A unique index lets you look up the single element with a certain value of one of the fields.
    """
    
    @typing.override
    def _register(self, key: Key, elem: Obj) -> None:
        if key in self._lookup:
            old_elem = self._lookup[key]
            raise ValidationError(f"Duplicate value {key!r} for unique-indexed field {self.on_field!r} (existing object: {old_elem!r}, new object: {elem!r})")
        
        self._lookup[key] = elem
    
    @typing.override
    def _unregister(self, key: Key, elem: Obj) -> None:
        self._lookup.pop(key, None)


class PrimaryIndex[Obj, Key = typing.Any](UniqueIndex[Obj, Key]):
    """
    A primary index is a special kind of unique index that also acts as the primary storage for the table's entries.
    """
    
    def __init__(
        self,
        on_field: str,
        getfield: FieldGetter,
        *,
        none_means_empty: bool = True,
    ):
        super().__init__(
            on_field,
            getfield,
            none_means_empty=none_means_empty,
            required=True,
        )
    
    def all(self) -> typing.Iterable[Obj]:
        return self.values()


# TODO: MultiIndex with duplicates allowed


# TODO: OrderedIndex with `[low:high]` syntax


__all__ = [
    "Index",
    "UniqueIndex",
    "PrimaryIndex",
]
