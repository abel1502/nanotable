from __future__ import annotations
import typing


class ValidationError(Exception):
    """
    An exception signaling that an invariant was violated.
    """


class PrimaryIndexError(Exception):
    """
    An exception signaling a problem with the table's primary index.
    """


class FeatureError(Exception):  # pragma: no cover # The coverage report doesn't include tests with disabled options
    """
    An exception signaling that an extra necessary for a certain feature isn't installed
    """
    
    def __init__(self, feature_name: str):
        super().__init__(
            f"You need to install nanotable[{feature_name}] to use this feature",
        )


__all__ = [
    "ValidationError",
    "PrimaryIndexError",
    "FeatureError",
]
