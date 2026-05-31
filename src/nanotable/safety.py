from __future__ import annotations
import typing

from nanotable.errors import warn, IndexedFieldChangedWarning


# Set this to True to disable checking and warning about indexed fields being modified.
# This provides a small performance improvement, but makes potential bugs very hard to detect.
disable_safety_checks: bool = False


def verify_immutable_key(
    old: typing.Any,
    new: typing.Any,
    obj: typing.Any,
    index_name: str,
):
    if disable_safety_checks or old == new:
        return
    
    warn(
        f"The value used in the index on {index_name!r} was changed on {obj!r} from {old!r} to {new!r}! "
        f"The table is now in an inconsistent state. Use `Table.rekey` for changing indexed fields safely.",
        IndexedFieldChangedWarning,
    )


__all__ = [
    "disable_safety_checks",
    "verify_immutable_key",
]
