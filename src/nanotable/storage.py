from __future__ import annotations
import typing
from abc import ABC, abstractmethod

from nanotable.index import Index
from nanotable.errors import ConflictError, warn, UnsupportedOperationWarning


class Storage[Obj](ABC, typing.Collection[Obj]):
    """
    The base class for all storage implementations.
    
    A storage defines the semantics of how the elements of a table are stored
    (whether a specific order is preserved, whether duplicates are allowed, etc.)
    and what notion of identity they use.
    """
    
    @abstractmethod
    def __iter__(self) -> typing.Iterator[Obj]:
        """
        Iterates over the elements in storage. Part of the `Collection` interface.
        
        :returns: An iterator over the elements in storage.
        """
    
    @abstractmethod
    def __len__(self) -> int:
        """
        Returns the number of elements in storage. Part of the `Collection` interface.
        
        :returns: The number of elements in storage.
        """
    
    @abstractmethod
    def __contains__(self, obj: object) -> bool:
        """
        Returns whether an element is in storage. Part of the `Collection` interface.
        
        :returns: `True` if the element is in storage.
        """
    
    @abstractmethod
    def add(self, obj: Obj, *, overwrite: bool = False) -> None:
        """
        Adds an element to storage.
        
        :param obj: The element to add.
        :param overwrite: If `True`, overwrite the element if it already exists in storage.
        
        :raises ConflictError: If `overwrite` is `False` and the element already exists in storage.
        """
    
    def add_many(self, objs: typing.Iterable[Obj], *, overwrite: bool = False) -> None:
        """
        Adds multiple elements to storage. The default implementation simply calls `add` for each element.
        
        :param objs: The elements to add.
        :param overwrite: If `True`, overwrite the elements that already exist in storage.
        
        :raises ConflictError: If `overwrite` is `False` and the elements already exist in storage.
        """
        
        for obj in objs:
            self.add(obj, overwrite=overwrite)
    
    @abstractmethod
    def remove(self, obj: Obj, *, missing_ok: bool = False) -> None:
        """
        Removes an element from storage.
        
        :param obj: The element to remove.
        :param missing_ok: If `False`, the element must exist in storage.
        
        :raises KeyError: If `missing_ok` is `False` and the element does not exist in storage.
        """
    
    def remove_many(self, objs: typing.Iterable[Obj], *, missing_ok: bool = False) -> None:
        """
        Removes multiple elements from storage. The default implementation simply calls `remove` for each element.
        
        :param objs: The elements to remove.
        :param missing_ok: If `False`, the elements must exist in storage.
        
        :raises KeyError: If `missing_ok` is `False` and the elements do not exist in storage.
        """
        
        for obj in objs:
            self.remove(obj, missing_ok=missing_ok)
    
    @abstractmethod
    def clear(self) -> None:
        """
        Removes all elements from storage.
        """


class WrapperStorage[Obj, Impl: typing.Collection[typing.Any]](Storage[Obj]):
    """
    A utility base class for a storage that wraps another collection.
    
    You still need to subclass this and implement `add` and `remove`
    before you can use it.
    """
    
    _impl: Impl
    
    def __init__(self, impl: Impl) -> None:
        self._impl = impl
    
    @typing.override
    def __iter__(self) -> typing.Iterator[Obj]:
        return iter(self._impl)

    @typing.override
    def __len__(self) -> int:
        return len(self._impl)
    
    @typing.override
    def __contains__(self, obj: object) -> bool:
        return obj in self._impl


class ListStorage[Obj](WrapperStorage[Obj, list[Obj]]):
    """
    Stores objects in a `list`.
    
    - Preserves insertion order.
    - Does not allow duplicates.
    - Object identity is based on equality.
    - Presence checks, `add(overwrite=False)`, and `remove` are linear time.
    """
    
    def __init__(self, initial: typing.Iterable[Obj] = ()) -> None:
        val: list[Obj] = []
        
        for obj in initial:
            if obj in val:
                raise ConflictError(f"Duplicate element {obj!r} among initial elements")
            
            val.append(obj)
        
        super().__init__(val)
    
    @typing.override
    def add(self, obj: Obj, *, overwrite: bool = False) -> None:
        if not overwrite and obj in self._impl:
            raise ConflictError(f"Element {obj!r} already exists in storage")
        
        self._impl.append(obj)
    
    @typing.override
    def remove(self, obj: Obj, *, missing_ok: bool = False) -> None:
        if not missing_ok and obj not in self._impl:
            raise KeyError(f"Element {obj!r} does not exist in storage")
        
        self._impl.remove(obj)
    
    @typing.override
    def clear(self) -> None:
        self._impl.clear()


class MultiListStorage[Obj](WrapperStorage[Obj, list[Obj]]):
    """
    Stores objects in a `list`, but allows duplicates.
    
    - Preserves insertion order.
    - Removal removes the first occurrence.
    - Allows duplicates.
    - Object identity is based on equality.
    - Presence checks and `remove` are linear time.
    - `add(overwrite=True)` is not implemented. It will issue a warning and behave like `add(overwrite=False)`.
    """
    
    def __init__(self, initial: typing.Iterable[Obj] = ()) -> None:
        super().__init__(list(initial))
    
    @typing.override
    def add(self, obj: Obj, *, overwrite: bool = False) -> None:
        if overwrite:
            warn(
                "Overwriting elements is not well-defined for MultiListStorage. `overwrite=True` will be ignored. "
                "If you wish to define a semantic for overwriting elements, consider subclassing `MultiListStorage`.",
                UnsupportedOperationWarning,
            )
        self._impl.append(obj)
    
    @typing.override
    def remove(self, obj, *, missing_ok = False):
        if not missing_ok and obj not in self._impl:
            raise KeyError(f"Element {obj!r} does not exist in storage")
        
        self._impl.remove(obj)
    
    @typing.override
    def clear(self) -> None:
        self._impl.clear()


class SetStorage[Obj](WrapperStorage[Obj, set[Obj]]):
    """
    Stores objects in a `set`.
    
    - Order is unspecified.
    - Does not allow duplicates.
    - Object identity is based on equality.
    - Requires objects to be hashable.
    - All operations are constant time. (Except iteration and the like, obviously)
    """
    
    def __init__(self, initial: typing.Iterable[Obj] = ()) -> None:
        super().__init__(set(initial))
    
    @typing.override
    def add(self, obj: Obj, *, overwrite: bool = False) -> None:
        if not overwrite and obj in self._impl:
            raise ConflictError(f"Element {obj!r} already exists in storage")
        
        self._impl.add(obj)
    
    @typing.override
    def remove(self, obj: Obj, *, missing_ok: bool = False) -> None:
        if not missing_ok and obj not in self._impl:
            raise KeyError(f"Element {obj!r} does not exist in storage")
        
        self._impl.discard(obj)
    
    @typing.override
    def clear(self) -> None:
        self._impl.clear()


class OrderedSetStorage[Obj](WrapperStorage[Obj, dict[Obj, None]]):
    """
    Stores objects in a `dict` with `None` keys. Makes use of the fact
    `dict`s preserve insertion order to implement a makeshift ordered set.
    
    - Insertion order is preserved.
    - Does not allow duplicates.
    - Object identity is based on equality.
    - Requires objects to be hashable.
    - All operations are constant time. (Except iteration and the like, obviously)
    """
    
    def __init__(self, initial: typing.Iterable[Obj] = ()) -> None:
        super().__init__(dict.fromkeys(initial))
    
    @typing.override
    def add(self, obj: Obj, *, overwrite: bool = False) -> None:
        if not overwrite and obj in self._impl:
            raise ConflictError(f"Element {obj!r} already exists in storage")
        
        self._impl[obj] = None
    
    @typing.override
    def remove(self, obj: Obj, *, missing_ok: bool = False) -> None:
        if not missing_ok and obj not in self._impl:
            raise KeyError(f"Element {obj!r} does not exist in storage")
        
        del self._impl[obj]
    
    @typing.override
    def clear(self) -> None:
        self._impl.clear()


class IndexViewStorage[Obj](Storage[Obj]):
    """
    Does not actually store objects. Instead exposes the objects
    accounted for by an index. Wraps an index created with `required=True`.
    `UniqueIndex` and subclasses are recommended, but any `Index` is supported.
    
    - Order may or may not be preserved depending on the underlying index.
    - Duplicates may or may not be allowed depending on the underlying index.
    - Object identity is based on the indexed field.
    - Time complexity depends on the underlying index.
      For `UniqueIndex` and subclasses, all operations are constant time. (Except iteration and the like, obviously).
      Notably, for `MultiIndex` and other similar kinds, `len()` and `obj in storage` can be linear time.
    - All mutating operations are no-ops. Relies on the index itself being modified instead.
    - Special integration with `Table`: when this is used as the table's storage, the index is automatically
      exposed in the table's `.by`.
    """
    
    index: Index[Obj]
    
    def __init__(self, index: Index[Obj]) -> None:
        if not index.required:
            raise TypeError("Only a `required=True` index may be used as a storage backend. Otherwise objects without the indexed field couldn't be accounted for.")

        self.index = index
    
    @typing.override
    def __len__(self) -> int:
        return self.index.num_objects()
    
    @typing.override
    def __iter__(self) -> typing.Iterator[Obj]:
        return iter(self.index.objects())
    
    @typing.override
    def __contains__(self, obj: object) -> bool:
        return self.index.getfield(typing.cast(Obj, obj)) in self.index
    
    @typing.override
    def add(self, obj: Obj, *, overwrite: bool = False) -> None:
        """
        No-op. Modify the contents of the underlying index instead.
        """
    
    @typing.override
    def add_many(self, objs: typing.Iterable[Obj], *, overwrite: bool = False) -> None:
        """
        No-op. Modify the contents of the underlying index instead.
        """
    
    @typing.override
    def remove(self, obj: Obj, *, missing_ok: bool = False) -> None:
        """
        No-op. Modify the contents of the underlying index instead.
        """
    
    @typing.override
    def remove_many(self, objs: typing.Iterable[Obj], *, missing_ok: bool = False) -> None:
        """
        No-op. Modify the contents of the underlying index instead.
        """
    
    @typing.override
    def clear(self) -> None:
        """
        No-op. Modify the contents of the underlying index instead.
        """


__all__ = [
    "Storage",
    "WrapperStorage",
    "ListStorage",
    "MultiListStorage",
    "SetStorage",
    "OrderedSetStorage",
    "IndexViewStorage",
]


# TODO: SortedListStorage and SortedSetStorage
