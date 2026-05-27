from __future__ import annotations
import typing

from typing_extensions import Sentinel


MISSING = Sentinel("MISSING")


# Can't put `MISSING` in type annotations because neither mypy nor pylance understand it. This will have to do
type typeof_MISSING = Sentinel


type FieldGetter[Obj] = typing.Callable[[Obj], typing.Any | typeof_MISSING]


type FieldGetterFactory[Obj] = typing.Callable[[str], FieldGetter[Obj]]


def getfield_attr(key: str) -> FieldGetter[object]:
    def getter(obj: object) -> typing.Any | typeof_MISSING:
        return getattr(obj, key, MISSING)
    
    return getter


def getfield_item(key: str) -> FieldGetter[typing.Mapping[str, typing.Any]]:
    def getter(obj: typing.Mapping[str, typing.Any]) -> typing.Any | typeof_MISSING:
        if not isinstance(obj, typing.Mapping):
            return MISSING
        
        return obj.get(key, MISSING)
    
    return getter


__all__ = [
    "MISSING",
    "typeof_MISSING",
    "FieldGetter",
    "FieldGetterFactory",
    "getfield_attr",
    "getfield_item",
]

