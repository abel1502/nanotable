from __future__ import annotations
import typing


class UniqueIndex[Key, Elem]:
    __slots__ = ("_lookup", "key_field", "sentinel", "required")
    
    _lookup: dict[Key, Elem]
    key_field: str
    sentinel: object
    required: bool
    
    def __init__(self, key_field: str, *, none_as_value: bool = False, required: bool = True):
        self._lookup = {}
        self.key_field = key_field
        self.sentinel = object() if none_as_value else None
        self.required = required
    
    def add(self, elem: Elem):
        key = getattr(elem, self.key_field, self.sentinel)
        
        if key is self.sentinel:
            if self.required:
                raise ValueError(f"Element {elem!r} has no {self.key_field!r} field which is required")
            return
        
        self._lookup[key] = elem
    
    def discard(self, elem: Elem, *, missing_ok: bool = False):
        key = getattr(elem, self.key_field, self.sentinel)
        
        if key is self.sentinel:
            if self.required:
                raise ValueError(f"Element {elem!r} has no {self.key_field!r} field which is required")
            return
        
        if missing_ok:
            self._lookup.pop(key, None)
        else:
            self._lookup.pop(key)
    
    def get(self, key: Key) -> Elem:
        result = self._lookup.get(key, self.sentinel)
        
        if result is self.sentinel:
            raise KeyError(f"Key {key!r} not found in index by {self.key_field!r}")
        
        return result

