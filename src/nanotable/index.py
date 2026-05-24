from __future__ import annotations
import typing

from nanotable.field import FieldGetter, MISSING


class UniqueIndex[Elem]:
    """
    A unique index lets you look up the single element with a certain value of the `key_field` attribute.
    """
    
    __slots__ = ("_lookup", "key_field", "sentinel", "required")
    
    _lookup: dict[typing.Any, Elem]
    key_field: str
    sentinel: object
    required: bool
    
    def __init__(self, key_field: str, *, none_as_value: bool = False, required: bool = True):
        """
        :param key_field: The name of the field to index by.
        :param none_as_value: If `True`, `None` is treated as a regular value.
            If `False`, `None` is treated the same as the lack of the `key_field` attribute.
            Defaults to `False`.
        :param required: If `True`, all objects must have a value for `key_field`.
            If `False`, objects without a value for `key_field` are ignored.
            Defaults to `True`.
        """
        
        self._lookup = {}
        self.key_field = key_field
        self.sentinel = object() if none_as_value else None
        self.required = required
    
    # TODO: Store getfield as a member
    def add(self, elem: Elem, *, getfield: FieldGetter[Elem]) -> None:
        """
        Adds an element to the index.
        
        :param elem: The element to add.
        :param getfield: A function to get the value of the `key_field` attribute. Defaults to `getattr`.
        
        :raises ValueError: If `required` is `True` and the element has no value for `key_field`.
        :raises KeyError: If the element already exists in the index.
        """
        
        key = getfield(elem, self.key_field)
        if key is MISSING:
            key = self.sentinel
        
        if key is self.sentinel:
            if self.required:
                raise ValueError(f"Element {elem!r} has no {self.key_field!r} field which is required")
            return

        if key in self._lookup:
            raise KeyError(f"Key {key!r} already exists in index by {self.key_field!r}")
        
        self._lookup[key] = elem
    
    def remove(self, elem: Elem, *, missing_ok: bool = False, getfield: FieldGetter[Elem]) -> None:
        """
        Removes an element from the index.
        
        :param elem: The element to remove.
        :param missing_ok: If `False`, the element must exist in the index. Defaults to `False`.
        
        :raises ValueError: If `required` is `True` and the element has no value for `key_field`.
        :raises KeyError: If `missing_ok` is `False` and the element does not exist in the index.
        """
        
        key = getfield(elem, self.key_field)
        if key is MISSING:
            key = self.sentinel
        
        if key is self.sentinel:
            if self.required:
                raise ValueError(f"Element {elem!r} has no {self.key_field!r} field which is required")
            return
        
        if not missing_ok and key not in self._lookup:
            raise KeyError(f"Key {key!r} not found in index by {self.key_field!r}")
        
        self._lookup.pop(key, None)
    
    @typing.overload
    def get(self, key: typing.Any, /) -> Elem:
        """
        Returns the element with the given key.
        
        :param key: The key to look up.
        
        :raises KeyError: If the key is not found in the index.
        """
    
    @typing.overload
    def get[Default](self, key: typing.Any, default: Default, /) -> Elem | Default:
        """
        Returns the element with the given key, or `default` if the key is not found in the index.
        
        :param key: The key to look up.
        :param default: The value to return if the key is not found in the index.
        """
    
    def get(self, key, *args):
        if len(args) == 1:
            return self._lookup.get(key, args[0])
        
        if len(args) != 0:
            raise TypeError(f"get() has no overload with {len(args) + 1} positional arguments")
        
        result = self._lookup.get(key, self.sentinel)
        
        if result is self.sentinel:
            raise KeyError(f"Key {key!r} not found in index by {self.key_field!r}")
        
        return result


__all__ = [
    "UniqueIndex",
]
