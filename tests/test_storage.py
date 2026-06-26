from __future__ import annotations
import typing

import pytest

import nanotable.storage
from nanotable.storage import Storage, ListStorage, MultiListStorage, SetStorage, OrderedSetStorage, IndexViewStorage, DummyStorage
from nanotable.index import Index, UniqueIndex, MultiIndex
from nanotable.field import getfield_item
from nanotable.errors import ConflictError, UnfinishedTableError, UnsupportedOperationWarning


def test_exports() -> None:
    exports = nanotable.storage.__all__
    
    assert "Storage" in exports
    assert "WrapperStorage" in exports
    assert "ListStorage" in exports
    assert "MultiListStorage" in exports
    assert "SetStorage" in exports
    assert "OrderedSetStorage" in exports
    assert "IndexViewStorage" in exports
    assert "DummyStorage" in exports


class StorageFactory[Obj = typing.Any](typing.Protocol):
    def __call__(self, default: typing.Iterable[Obj] = (), /) -> Storage[Obj]:
        ...


type ContainerFactory[Obj] = typing.Callable[[typing.Iterable[Obj]], typing.Collection[Obj]]


@pytest.mark.parametrize("factory", [
    ListStorage,
    MultiListStorage,
    SetStorage,
    OrderedSetStorage,
    # IndexViewStorage tested separately
    # DummyStorage tested separately
])
class TestAnyStorage:
    def test_default_constructor(self, factory: StorageFactory[object]) -> None:
        storage = factory()
        
        assert isinstance(storage, Storage)
        assert len(storage) == 0
        assert list(storage) == []
        assert 123 not in storage
        assert None not in storage
    
    @pytest.mark.parametrize("container_factory", [
        list,
        tuple,
        set,
        frozenset,
        dict.fromkeys,
    ])
    def test_defaults_constructor(
        self,
        factory: StorageFactory[int],
        container_factory: ContainerFactory[int],
    ) -> None:
        initials = container_factory([123, 456])
        storage = factory(initials)
        
        assert isinstance(storage, Storage)
        assert len(storage) == 2
        assert set(storage) == set(initials)
        assert 123 in storage
        assert 456 in storage
        assert 890 not in storage
        assert "foo" not in storage
        assert None not in storage

    def test_mutation(self, factory: StorageFactory[int]) -> None:
        storage = factory()
        
        assert not storage
        
        storage.add(123)
        
        assert len(storage) == 1
        assert 123 in storage
        assert list(storage) == [123]
        
        storage.remove(123)
        
        assert len(storage) == 0
        assert 123 not in storage
        assert list(storage) == []
    
    def test_multi_mutation(self, factory: StorageFactory[int]) -> None:
        storage = factory()
        
        assert not storage
        
        storage.add_many([123, 456])
        
        assert len(storage) == 2
        assert 123 in storage
        assert 456 in storage
        assert set(storage) == {123, 456}
        
        storage.remove_many([123, 456])
        
        assert len(storage) == 0
        assert 123 not in storage
        assert 456 not in storage
        assert list(storage) == []
    
    def test_missing_ok(self, factory: StorageFactory[int]) -> None:
        storage = factory([123])
        
        assert len(storage) == 1
        assert 123 in storage
        assert list(storage) == [123]
        
        with pytest.raises(KeyError):
            storage.remove(456)
        
        storage.remove(456, missing_ok=True)
        
        assert len(storage) == 1
        assert 123 in storage
        assert list(storage) == [123]

    def test_clear(self, factory: StorageFactory[int]) -> None:
        storage = factory([123, 456])
        
        assert len(storage) == 2
        assert 123 in storage
        assert 456 in storage
        assert set(storage) == {123, 456}
        
        storage.clear()
        
        assert len(storage) == 0
        assert 123 not in storage
        assert 456 not in storage
        assert list(storage) == []
    
    def test_no_duplicates(self, factory: StorageFactory[int]) -> None:
        if factory == MultiListStorage:
            return
        
        if factory == ListStorage:
            with pytest.raises(ConflictError):
                factory([123, 123])
        else:
            assert list(factory([123, 123])) == [123]
        
        storage = factory([123, 456])
        
        with pytest.raises(ConflictError):
            storage.add(123)
    
    def test_allow_duplicates(self, factory: StorageFactory[int]) -> None:
        if factory != MultiListStorage:
            return
        
        assert list(factory([123, 123])) == [123, 123]
        
        storage = factory([123, 456])
        storage.add(123)
        
        assert list(storage) == [123, 456, 123]
        
        storage.add_many([123, 456])
        
        assert list(storage) == [123, 456, 123, 123, 456]
    
    def test_eq(self, factory: StorageFactory[int]) -> None:
        assert factory([123]) == factory([123])
        assert factory([123]) != factory([456])
        
        if factory != ListStorage:
            assert factory([123]) != ListStorage([123])


def test_initialization_duplicates() -> None:
    with pytest.raises(ConflictError):
        ListStorage([123, 123])
    
    assert list(MultiListStorage([123, 123])) == [123, 123]
    
    assert list(SetStorage([123, 123])) == [123]
    assert list(OrderedSetStorage([123, 123])) == [123]


# TODO: Test insertion order


def test_dummy_storage() -> None:
    with pytest.raises(TypeError):
        # Shouldn't accept initial items
        DummyStorage([1, 2, 3])  # type: ignore
    
    storage = DummyStorage[int]()
    
    with pytest.raises(UnfinishedTableError):
        len(storage)
    
    with pytest.raises(UnfinishedTableError):
        iter(storage)
    
    with pytest.raises(UnfinishedTableError):
        1 in storage
    
    with pytest.raises(UnfinishedTableError):
        storage.add(1)
    
    with pytest.raises(UnfinishedTableError):
        storage.remove(1)
    
    with pytest.raises(UnfinishedTableError):
        storage.add_many([])
    
    with pytest.raises(UnfinishedTableError):
        storage.remove_many([])
    
    with pytest.raises(UnfinishedTableError):
        storage.clear()
    
    assert storage == DummyStorage[int]()
    assert storage != ListStorage[int]()


class TestIndexViewStorage:
    def test_accepted_indexes(self) -> None:
        IndexViewStorage(UniqueIndex("foo", getfield_item("foo"), none_means_empty=False, required=True))
        IndexViewStorage(UniqueIndex("foo", getfield_item("foo"), none_means_empty=True, required=True))
        IndexViewStorage(MultiIndex("foo", getfield_item("foo"), none_means_empty=False, required=True))
        IndexViewStorage(MultiIndex("foo", getfield_item("foo"), none_means_empty=True, required=True))
        
        with pytest.raises(TypeError, match=r"required"):
            IndexViewStorage(UniqueIndex("foo", getfield_item("foo"), none_means_empty=False, required=False))
        
        with pytest.raises(TypeError, match=r"required"):
            IndexViewStorage(UniqueIndex("foo", getfield_item("foo"), none_means_empty=True, required=False))
        
        with pytest.raises(TypeError, match=r"required"):
            IndexViewStorage(MultiIndex("foo", getfield_item("foo"), none_means_empty=False, required=False))
        
        with pytest.raises(TypeError, match=r"required"):
            IndexViewStorage(MultiIndex("foo", getfield_item("foo"), none_means_empty=True, required=False))
        
        with pytest.raises(TypeError, match=r"Index"):
            IndexViewStorage(ListStorage())  # type: ignore

    def test_operations_unique(self) -> None:
        index = UniqueIndex("id", getfield_item("id"), required=True)
        storage = IndexViewStorage(index)
        
        assert index.num_objects() == 0
        assert len(storage) == 0
        assert list(storage) == []
        assert {"id": 1} not in storage
        assert 123 not in storage
        assert None not in storage
        
        storage.add({"id": 1})
        
        assert index
        assert storage
        
        assert index.num_objects() == 1
        assert len(storage) == 1
        assert list(storage) == [{"id": 1}]
        assert {"id": 1} in storage
        assert {"id": 1, "extra": "foo"} not in storage
        assert 123 not in storage
        assert None not in storage
        
        with pytest.raises(ConflictError):
            storage.add({"id": 1})
        
        with pytest.raises(ConflictError):
            storage.add({"id": 1, "extra": "foo"})
        
        with pytest.raises(KeyError):
            storage.remove({"id": 1, "extra": "foo"})
        
        assert len(storage) == 1
        
        storage.remove({"id": 1, "extra": "foo"}, missing_ok=True)
        
        assert len(storage) == 1
        
        storage.remove({"id": 1})
        
        assert index.num_objects() == 0
        assert len(storage) == 0
        assert list(storage) == []
        
        storage.remove({"id": 1}, missing_ok=True)
        
        assert index.num_objects() == 0
        assert len(storage) == 0
        assert list(storage) == []
    
    def test_bulk_operations_unique(self) -> None:
        index = UniqueIndex("id", getfield_item("id"), required=True)
        storage = IndexViewStorage(index)
        
        storage.add_many([{"id": 1}, {"id": 2, "extra": "foo"}])
        
        assert index.num_objects() == 2
        assert len(storage) == 2
        assert sorted(storage, key=lambda x: x["id"]) == [{"id": 1}, {"id": 2, "extra": "foo"}]
        
        with pytest.raises(ConflictError):
            storage.add_many([{"id": 1}])
        
        with pytest.raises(ConflictError):
            storage.add_many([{"id": 2}])
        
        with pytest.raises(KeyError):
            storage.remove_many([{"id": 1}, {"id": 2}])
        
        assert index.num_objects() == 1
        assert len(storage) == 1
        assert list(storage) == [{"id": 2, "extra": "foo"}]
        
        storage.remove_many([{"id": 1}, {"id": 2}], missing_ok=True)
        
        assert index.num_objects() == 1
        assert len(storage) == 1
        
        storage.remove_many([{"id": 1}, {"id": 2, "extra": "foo"}], missing_ok=True)
        
        assert index.num_objects() == 0
        assert len(storage) == 0
        
        storage.add_many([{"id": 1}, {"id": 2}])
        
        assert index.num_objects() == 2
        assert len(storage) == 2
        
        storage.clear()
        
        assert index.num_objects() == 0
        assert len(storage) == 0
        assert list(storage) == []
    
    def test_multi_index(self) -> None:
        index = MultiIndex("id", getfield_item("id"), required=True)
        storage = IndexViewStorage(index)
        
        assert index.num_objects() == 0
        assert len(storage) == 0
        assert list(storage) == []
        assert {"id": 1} not in storage
        assert 123 not in storage
        assert None not in storage
        
        storage.add({"id": 1, "name": "foo"})
        
        assert index.num_objects() == 1
        assert len(storage) == 1
        assert list(storage) == [{"id": 1, "name": "foo"}]
        assert {"id": 1, "name": "foo"} in storage
        assert {"id": 1} not in storage
        
        storage.add({"id": 1, "name": "bar"})
        
        assert index.num_objects()
        assert len(storage) == 2
        assert sorted(storage, key=lambda x: x["name"]) == [{"id": 1, "name": "bar"}, {"id": 1, "name": "foo"}]
        
        storage.add({"id": 1, "name": "foo"})
        
        assert index.num_objects() == 3
        assert len(storage) == 3
        assert sorted(storage, key=lambda x: x["name"]) == [{"id": 1, "name": "bar"}, {"id": 1, "name": "foo"}, {"id": 1, "name": "foo"}]
    
    def test_writethrough_off(self) -> None:
        index = UniqueIndex("id", getfield_item("id"), required=True)
        storage = IndexViewStorage(index)
        
        assert storage.writethrough
        
        storage.writethrough = False
        
        assert not storage.writethrough
        
        storage.add({"id": 1})
        
        assert index.num_objects() == 0
        assert len(storage) == 0
        
        storage.remove({"id": 1})
        
        assert index.num_objects() == 0
        assert len(storage) == 0
        
        storage.add_many([{"id": 1}, {"id": 2}])
        
        assert index.num_objects() == 0
        assert len(storage) == 0
        
        storage.remove_many([{"id": 1}, {"id": 2}])
        
        assert index.num_objects() == 0
        assert len(storage) == 0
        
        storage.clear()
        
        assert index.num_objects() == 0
        assert len(storage) == 0

    # TODO: Test insertion order

