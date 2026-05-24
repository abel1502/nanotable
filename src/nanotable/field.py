from __future__ import annotations
import typing

from typing_extensions import Sentinel


MISSING = Sentinel("MISSING")


# Not putting `| MISSING` in the return type because neither mypy nor pylance understand it. This will have to do
type FieldGetter[Obj] = typing.Callable[[Obj, str], typing.Any | Sentinel]


def attr_getter(obj: object, key: str) -> typing.Any | Sentinel:
    return getattr(obj, key, MISSING)


def dict_getter(obj: dict[str, typing.Any], key: str) -> typing.Any | Sentinel:
    return obj.get(key, MISSING)


__all__ = [
    "MISSING",
    "FieldGetter",
    "attr_getter",
    "dict_getter",
]

