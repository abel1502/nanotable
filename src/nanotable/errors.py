from __future__ import annotations
import typing


class ValidationError(Exception):
    """
    An exception signaling that an invariant was violated.
    """


class PrimaryIndexError(Exception):
    """
    An exception signaling that the primary index already exists.
    """


__all__ = [
    "ValidationError",
    "PrimaryIndexError",
]
