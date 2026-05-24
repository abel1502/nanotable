from __future__ import annotations
import typing

from typing_extensions import Sentinel


MISSING = Sentinel("MISSING")


# Can't put `MISSING` in type annotations because neither mypy nor pylance understand it. This will have to do
type typeof_MISSING = Sentinel


type FieldGetter[Obj] = typing.Callable[[Obj, str], typing.Any | typeof_MISSING]


def attr_getter(obj: object, key: str) -> typing.Any | typeof_MISSING:
    return getattr(obj, key, MISSING)


def dict_getter(obj: dict[str, typing.Any], key: str) -> typing.Any | typeof_MISSING:
    return obj.get(key, MISSING)


__all__ = [
    "MISSING",
    "typeof_MISSING",
    "FieldGetter",
    "attr_getter",
    "dict_getter",
]

