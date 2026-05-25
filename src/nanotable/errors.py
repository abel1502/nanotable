from __future__ import annotations
import typing


class ValidationError(Exception):
    """
    An exception signaling that an invariant was violated.
    """
    
