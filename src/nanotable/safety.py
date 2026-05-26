from __future__ import annotations
import typing
import pathlib
import warnings


# Set this to True to disable checking and warning about indexed fields being modified.
# This provides a small performance improvement, but makes potential bugs very hard to detect.
disable_safety_checks: bool = False


PACKAGE_ROOT = pathlib.Path(__file__).parent


class IndexedFieldChangedWarning(Warning):
    pass


def verify_immutable_key(
    old: typing.Any,
    new: typing.Any,
    obj: typing.Any,
    field_name: str,
):
    if disable_safety_checks or old == new:
        return
    
    warnings.warn(
        f"An indexed field {field_name!r} was changed on {obj!r} from {old!r} to {new!r}! "
        f"The table is now in an inconsistent state. Use `Table.rekey` for changing indexed fields safely.",
        IndexedFieldChangedWarning,
        skip_file_prefixes=(str(PACKAGE_ROOT),),
    )


__all__ = [
    "disable_safety_checks",
    "IndexedFieldChangedWarning",
    "verify_immutable_key",
]
