from __future__ import annotations
import typing

import pytest

import nanotable


def test_exports() -> None:
    exports = nanotable.__all__
    
    assert "Table" in exports
    
    assert "Storage" in exports
    assert "WrapperStorage" in exports
    assert "ListStorage" in exports
    assert "MultiListStorage" in exports
    assert "SetStorage" in exports
    assert "OrderedSetStorage" in exports
    assert "IndexViewStorage" in exports
    
    assert "Index" in exports
    assert "UniqueIndex" in exports
    assert "MultiIndex" in exports
    
    assert "FieldGetter" in exports
    assert "FieldGetterFactory" in exports
    assert "getfield_attr" in exports
    assert "getfield_item" in exports
    assert "MISSING" in exports
    assert "typeof_MISSING" in exports
    
    assert "ConflictError" in exports
    assert "UnfinishedTableError" in exports
    assert "FeatureError" in exports
    assert "IndexedFieldChangedWarning" in exports
    assert "UnsupportedOperationWarning" in exports
    
    assert "__version__" in exports


def test_exports_with_sorted() -> None:
    pytest.importorskip("sortedcontainers")
    
    exports = nanotable.__all__
    
    assert "SortedUniqueIndex" in exports
    assert "SortedMultiIndex" in exports

