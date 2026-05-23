from __future__ import annotations
import typing


class FieldGetter[Obj, Field](typing.Protocol):
    """
    Signature: `(obj: Obj, key: str, default: Default) -> Field | Default`
    
    Retrieves the field `key` of type `Field` from `obj` of type `Obj`, or returns the `default` value.

    Shouldn't raise any exceptions under normal conditions.
    """
    
    def __call__[Default](
        self,
        obj: Obj,
        key: str,
        default: Default,
    ) -> Field | Default:
        ...


__all__ = [
    "FieldGetter",
]

