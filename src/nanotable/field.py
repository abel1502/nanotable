from __future__ import annotations
import typing
import enum


# Apparently the best way to keep the type checker happy until 3.15 and standard library `sentinel`
class Missing(enum.Enum):
    MISSING = 0


MISSING = Missing.MISSING


type FieldGetter[Obj] = typing.Callable[[Obj, str], typing.Any | type[Missing]]


def attr_getter(obj: object, key: str) -> typing.Any | type[Missing]:
    return getattr(obj, key, MISSING)


def dict_getter(obj: dict[str, typing.Any], key: str) -> typing.Any | type[Missing]:
    return obj.get(key, MISSING)


__all__ = [
    "MISSING",
    "FieldGetter",
    "attr_getter",
    "dict_getter",
]

