from __future__ import annotations
import typing

import pytest
from pytest_mock import MockerFixture  # TODO: Use unittest.mock directly? Would enable hypothesis as well

import nanotable.transaction
from nanotable.transaction import Transaction


def test_exports() -> None:
    exports = nanotable.transaction.__all__
    
    assert "Transaction" in exports


class MyError(Exception):
    pass


def throw(x: Exception):
    raise x


class TestTransaction:
    def test_explicit_commit(self) -> None:
        with Transaction() as tx:
            tx.add_undo(lambda: pytest.fail("undo function was called"))
            tx.commit()
        
        assert not tx._stack


    def test_implicit_commit(self) -> None:
        with Transaction() as tx:
            tx.add_undo(lambda: pytest.fail("undo function was called"))

        assert not tx._stack


    def test_empty(self) -> None:
        with Transaction() as tx:
            pass
        
        assert not tx._stack


    def test_explicit_rollback(self, mocker: MockerFixture) -> None:
        cb = mocker.stub(name="undo function")
        
        with Transaction() as tx:
            tx.add_undo(cb)
            tx.rollback()
        
        cb.assert_called_once()
        assert not tx._stack


    def test_auto_rollback(self, mocker: MockerFixture) -> None:
        cb = mocker.stub(name="undo function")
        
        with pytest.raises(MyError):
            with Transaction() as tx:
                tx.add_undo(cb)
                raise MyError()
        
        cb.assert_called_once()
        assert not tx._stack


    def test_order(self, mocker: MockerFixture) -> None:
        cb = mocker.stub()
        
        with Transaction() as tx:
            tx.add_undo(lambda: cb(1))
            tx.add_undo(lambda: cb(2))
            tx.add_undo(lambda: cb(3))
            tx.rollback()
        
        assert cb.mock_calls == [
            mocker.call(3),
            mocker.call(2),
            mocker.call(1),
        ]


    def test_undo_error_group(self) -> None:
        with Transaction() as tx:
            tx.add_undo(lambda: throw(MyError(1)))
            tx.add_undo(lambda: throw(MyError(2)))
            tx.add_undo(lambda: throw(MyError(3)))
        
            with pytest.RaisesGroup(MyError, MyError, MyError) as exc_info:
                tx.rollback()
            
            assert [e.args[0] for e in exc_info.value.exceptions] == [3, 2, 1]
            assert exc_info.value.__cause__ is None


    def test_undo_error_group_with_cause(self) -> None:
        with pytest.RaisesGroup(MyError, MyError, MyError) as exc_info:
            with Transaction() as tx:
                tx.add_undo(lambda: throw(MyError(1)))
                tx.add_undo(lambda: throw(MyError(2)))
                tx.add_undo(lambda: throw(MyError(3)))
                
                raise RuntimeError("original exception")
        
        assert [e.args[0] for e in exc_info.value.exceptions] == [3, 2, 1]
        
        assert isinstance(exc_info.value.__context__, RuntimeError)
        assert exc_info.value.__context__.args == ("original exception",)

