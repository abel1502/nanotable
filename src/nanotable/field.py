from __future__ import annotations
import typing


# TODO: Replace with a more general "object kind descriptor"?
class FieldGetter[Obj](typing.Protocol):  # no cov
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
    ) -> typing.Any | Default:
        ...


def attr_getter[Obj, Default](obj: Obj, key: str, default: Default) -> typing.Any | Default:
    return getattr(obj, key, default)


def dict_getter[Default](obj: dict[str, typing.Any], key: str, default: Default) -> typing.Any | Default:
    return obj.get(key, default)


__all__ = [
    "FieldGetter",
    "attr_getter",
    "dict_getter",
]

