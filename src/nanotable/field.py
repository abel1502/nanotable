from __future__ import annotations
import typing


class FieldGetter[Obj, Field](typing.Protocol):  # no cov
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


def attr_getter[Obj, Field, Default](obj: Obj, key: str, default: Default) -> Field | Default:
    return getattr(obj, key, default)


def dict_getter[Field, Default](obj: dict[str, Field], key: str, default: Default) -> Field | Default:
    return obj.get(key, default)


__all__ = [
    "FieldGetter",
    "attr_getter",
    "dict_getter",
]

