from __future__ import annotations
import typing
import dataclasses

import pytest

import nanotable.table
from nanotable.table import Table
from nanotable.storage import MultiListStorage
import nanotable.index
from nanotable.index import UniqueIndex, MultiIndex
from nanotable.field import getfield_attr, getfield_item, MISSING
import nanotable.safety
from nanotable.errors import ConflictError, FeatureError, UnfinishedTableError, IndexedFieldChangedWarning


def test_exports() -> None:
    exports = nanotable.table.__all__
    
    assert "Table" in exports

@dataclasses.dataclass()
class MyObject:
    id: int
    name: str
    something_incomprehensible: typing.Any = None


class TestTable:
    def test_no_index(self) -> None:
        table = Table(storage=MultiListStorage(), of=MyObject)
        
        table.add(MyObject(1, "Foo"))
        table.add(MyObject(2, "Bar", something_incomprehensible=lambda x: x(x)))
        
        assert len(table) == 2
        
        table.add(MyObject(1, "Foo"))
        assert len(table) == 3
        
        table.remove(MyObject(1, "Foo"))
        assert len(table) == 2
        
        table.add(MyObject(1, "Foo"))
        assert len(table) == 3
        
        table.remove(MyObject(1, "Foo"))
        assert len(table) == 2
        
        with pytest.raises(KeyError):
            table.remove(MyObject(123, "..."))
        
        table.remove(MyObject(123, "..."), missing_ok=True)
        assert len(table) == 2
        
        table.clear()
        assert len(table) == 0
        
        table.extend([MyObject(1, "Foo"), MyObject(2, "Bar")])
        
        assert sorted(table, key=lambda obj: obj.id) == [MyObject(1, "Foo"), MyObject(2, "Bar")]
    
    def test_getfield_options(self) -> None:
        t = Table[typing.Any]()
        assert t._getfield_factory is getfield_attr
        
        t = Table(of=dict)
        assert t._getfield_factory is getfield_item
        
        t = Table(of=dict[str, typing.Any])
        assert t._getfield_factory is getfield_item
        
        t = Table(of=MyObject)
        assert t._getfield_factory is getfield_attr
        
        t = Table(of_objects=True)
        assert t._getfield_factory is getfield_attr
        
        t = Table(of_dicts=True)
        assert t._getfield_factory is getfield_item
        
        t = Table(getfield_factory=lambda name: lambda obj: 123)
        assert t._getfield_factory("foo")(None) == 123
        
        with pytest.raises(TypeError):
            Table(of=dict, of_dicts=True)
        
        with pytest.raises(TypeError):
            Table(of_objects=True, of_dicts=True)
        
        with pytest.raises(TypeError):
            Table(of_objects=True, getfield_factory=getfield_attr)
        
        with pytest.raises(TypeError):
            Table(of_dicts=True, getfield_factory=getfield_item)
        
        with pytest.raises(TypeError, match=r"must be a type"):
            Table(of="dict")  # type: ignore
    
    def test_storage_option(self) -> None:
        Table(of=dict, storage=MultiListStorage())
        Table(MultiListStorage(), of=dict)
        
        with pytest.raises(TypeError, match=r"Storage"):
            Table({}, of=dict)  # type: ignore
    
    def test_primary_index_collision(self) -> None:
        table = Table[MyObject]().index_on("id")
        
        with pytest.raises(ConflictError, match=r"another index with that name already exists"):
            table.primary_index_on("id")
        
        table = Table[MyObject]().primary_index_on("id")
        
        with pytest.raises(ConflictError, match=r"another primary index"):
            table.primary_index_on("name")
        
        table = Table[MyObject](MultiListStorage())
        
        with pytest.raises(ConflictError, match=r"custom storage"):
            table.primary_index_on("id")

    def test_primary_index(self) -> None:
        table = Table[MyObject]()
        
        obj = MyObject(1, "Foo")
        
        with pytest.raises(UnfinishedTableError, match=r"primary_index_on"):
            table.add(obj)
        
        with pytest.raises(UnfinishedTableError, match=r"primary_index_on"):
            len(table)
        
        table.primary_index_on("id")
        
        table.add(obj)
        
        assert len(table) == 1
        assert obj in table
        assert table.at[1] == obj
        
        table.add(MyObject(2, "Bar"))
        
        assert len(table) == 2
        assert table.at[1].name == "Foo"
        assert table.at[2].name == "Bar"
        assert table.by.id[1].name == "Foo"
        assert table.by.id[2].name == "Bar"
        assert sorted(table, key=lambda obj: obj.id) == [MyObject(1, "Foo"), MyObject(2, "Bar")]
    
    def test_unique_index(self) -> None:
        table = Table(MultiListStorage(), of=MyObject).index_on("id")
        
        assert isinstance(table.by.id, UniqueIndex)
        
        table.add(MyObject(1, "Foo"))
        table.add(MyObject(2, "Bar"))
        
        assert len(table) == 2
        assert table.by.id[1].name == "Foo"
        assert table.by.id[2].name == "Bar"
        
        with pytest.raises(KeyError):
            table.by.id[3]
        
        with pytest.raises(NotImplementedError):
            table.by.id[1:3]
        
        with pytest.raises(TypeError, match=r"no primary index"):
            table.at[1]
        
        with pytest.raises(ConflictError):
            table.add(MyObject(2, "Baz"))
        
        assert len(table) == 2
        assert table.by.id[2].name == "Bar"
        
        table.add(MyObject(2, "Baz"), overwrite=True)
        
        assert len(table) == 2
        assert table.by.id[2].name == "Baz"
        
        obj = typing.cast(MyObject, table.by.id[2])
        with table.rekey(obj):
            obj.id = 123
        
        assert len(table) == 2
        assert table.by.id[123].name == "Baz"
        assert 2 not in table.by.id
        assert sorted(table, key=lambda obj: obj.id) == [MyObject(1, "Foo"), MyObject(123, "Baz")]
        
        table.clear()
        assert len(table) == 0
        assert 1 not in table.by.id
        assert 2 not in table.by.id
    
    def test_missing_index(self) -> None:
        table = Table(of=MyObject).primary_index_on("id")
        
        table.add(MyObject(1, "Foo"))
        
        with pytest.raises(AttributeError):
            table.by.name
        
        with pytest.raises(AttributeError):
            table.by.nonexistent
    
    def test_bad_index_creation(self) -> None:
        table = Table(of=MyObject).primary_index_on("id")
        
        with pytest.raises(KeyError, match=r"already exists"):
            table.index_on("id", MultiIndex)
        
        with pytest.raises(TypeError, match=r"Index"):
            table.index_on("id", MultiListStorage)  # type: ignore
    
    def test_extend_non_atomic(self) -> None:
        # TODO: Do I want to make it atomic?
        
        table = Table(of=MyObject).primary_index_on("id").index_on("name")
        
        table.add(MyObject(1, "Foo"))
        table.add(MyObject(2, None))
        
        assert len(table) == 2
        
        with pytest.raises(ConflictError):
            table.extend([MyObject(3, "Baz"), MyObject(2, "Bar")])
        
        assert len(table) == 3
        assert table.by.name["Baz"].id == 3
        assert "Bar" not in table.by.name
        
        table.extend([MyObject(3, "Baz"), MyObject(4, "Bar")], overwrite=True)
        
        assert len(table) == 4
        assert "Bar" in table.by.name
        assert "Baz" in table.by.name
    
    def test_custom_primary_getfield(self) -> None:
        # TODO: Support catching AttributeError/KeyError in getfield and translating it to MISSING?
        table = Table(of=MyObject).primary_index_on(
            "id_and_name",
            getfield=lambda obj: (obj.id, obj.name) if isinstance(obj, MyObject) else MISSING,
        )
        
        table.add(MyObject(1, "Foo"))
        table.add(MyObject(1, "Bar"))
        
        assert len(table) == 2
        assert table.at[(1, "Foo")] == MyObject(1, "Foo")
        assert table.by.id_and_name[(1, "Foo")] == MyObject(1, "Foo")
    
    def test_custom_getfield(self) -> None:
        # TODO: See test_custom_primary_getfield
        table = Table(MultiListStorage(), of=MyObject).index_on(
            "id_and_name",
            kind=MultiIndex,
            getfield=lambda obj: (obj.id, obj.name) if isinstance(obj, MyObject) else MISSING,
        )
        
        table.add(MyObject(1, "Foo"))
        table.add(MyObject(1, "Foo", 12345))
        
        assert len(table) == 2
        assert table.by.id_and_name[(1, "Foo")] == [MyObject(1, "Foo"), MyObject(1, "Foo", 12345)]
    
    def test_rekey(self) -> None:
        table = Table(of=MyObject).primary_index_on("id").index_on(
            "id_and_name",
            getfield=lambda obj: (obj.id, obj.name) if isinstance(obj, MyObject) else MISSING,
        )
        
        table.add(MyObject(1, "Foo"))
        table.add(MyObject(2, "Bar"))
        
        assert len(table) == 2
        
        obj = typing.cast(MyObject, table.at[2])
        with table.rekey(obj):
            obj.id = 123
        
        assert len(table) == 2
        assert table.at[1].name == "Foo"
        assert 2 not in table.at
        assert table.at[123].name == "Bar"
        assert table.by.id_and_name[(1, "Foo")] == MyObject(1, "Foo")
        assert table.by.id_and_name[(123, "Bar")] == MyObject(123, "Bar")
        
        with table.rekey_on(obj, "id", "id_and_name"):
            obj.id = 456
        
        assert len(table) == 2
        assert table.at[1].name == "Foo"
        assert 2 not in table.at
        assert 123 not in table.at
        assert table.at[456].name == "Bar"
        assert table.by.id_and_name[(1, "Foo")] == MyObject(1, "Foo")
        assert table.by.id_and_name[(456, "Bar")] == MyObject(456, "Bar")
    
    @pytest.mark.parametrize("disable_safety", [False, True])
    def test_rekey_on_safety(
        self,
        recwarn: pytest.WarningsRecorder,
        monkeypatch: pytest.MonkeyPatch,
        disable_safety: bool,
    ) -> None:
        table = Table(of=MyObject).primary_index_on("id").index_on(
            "id_and_name",
            getfield=lambda obj: (obj.id, obj.name) if isinstance(obj, MyObject) else MISSING,
        )
        
        table.add(MyObject(1, "Foo"))
        table.add(MyObject(2, "Bar"))
        
        obj = typing.cast(MyObject, table.at[2])
        
        if disable_safety:
            monkeypatch.setattr(nanotable.safety, "disable_safety_checks", True)
            with table.rekey_on(obj, "id"):
                # Forgetting id_and_name
                obj.id = 123
            assert len(recwarn) == 0
        else:
            with pytest.warns(IndexedFieldChangedWarning):
                # Forgetting id_and_name
                with table.rekey_on(obj, "id"):
                    obj.id = 123
        
        # Table is now in an inconsistent state -- silently discard everything
        # to avoid warning in destructor (since we can't catch and silence it)
        monkeypatch.setattr(nanotable.safety, "disable_safety_checks", True)
        table.clear()
    
    def test_sorted_primary_index(self):
        has_sorted: bool
        try:
            import sortedcontainers
            has_sorted = True
            del sortedcontainers
        except ImportError:
            has_sorted = False
        
        if not has_sorted:
            with pytest.raises(FeatureError, match=r"nanotable\[sorted\]"):
                Table(of=MyObject).primary_index_on("id", sorted=True)
            return
        
        table = Table(of=MyObject).primary_index_on("id", sorted=True)
        assert isinstance(table.by.id, nanotable.index.SortedUniqueIndex)
        
        table.add(MyObject(1, "Foo"))
        table.add(MyObject(3, "Baz"))
        table.add(MyObject(2, "Bar"))
        
        assert list(table.at) == [1, 2, 3]
        
        assert list(table) == [MyObject(1, "Foo"), MyObject(2, "Bar"), MyObject(3, "Baz")]

