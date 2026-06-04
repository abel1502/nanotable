from __future__ import annotations
import typing
import warnings
import pathlib
import functools


class ConflictError(Exception):
    """
    An exception signaling that a new element conflicts with one already present.
    """


class UnfinishedTableError(Exception):
    """
    An exception signaling that the table was used before its construction was complete.
    """


class FeatureError(Exception):
    """
    An exception signaling that an extra necessary for a certain feature isn't installed
    """
    
    def __init__(self, feature_name: str):
        super().__init__(
            f"You need to install nanotable[{feature_name}] to use this feature",
        )


PACKAGE_ROOT = pathlib.Path(__file__).parent


@functools.wraps(warnings.warn)
def warn(msg: str, category: typing.Type[Warning] = UserWarning, **kwargs: typing.Any) -> None:
    """
    A wrapper around `warnings.warn` that issues warnings pointing to the user code referencing `nanotable`.
    """
    
    warnings.warn(
        msg,
        category,
        **kwargs, 
        skip_file_prefixes=(str(PACKAGE_ROOT),),
    )


class IndexedFieldChangedWarning(Warning):
    """
    A warning signaling that the value of an indexed field has changed.
    """


class UnsupportedOperationWarning(Warning):
    """
    A warning signaling that a certain operation is unsupported and a possibly unintuitive fallback will be used.
    """


__all__ = [
    "ConflictError",
    "UnfinishedTableError",
    "FeatureError",
    "warn",
    "IndexedFieldChangedWarning",
    "UnsupportedOperationWarning",
]
