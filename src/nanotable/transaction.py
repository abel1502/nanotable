from __future__ import annotations
import typing


class Transaction:
    """
    A transaction lets you carry out multiple operations with the ability
    to roll all of them back at the same time.
    
    `Transaction` should be used as a context manager:
    
    ```python
    with Transaction() as tx:
        do_thing_1()
        tx.add_undo(undo_thing_1)
        do_thing_2()
        tx.add_undo(lambda: undo_thing_2(parameter=123))
        ...
        if all_is_bad:
            rollback()
        tx.commit()  # or nothing
    ```
    
    When you call `commit()`, the transaction is considered successful and all
    undo steps are discarded.
    When you call `rollback(), it is considered failed and the undo steps are
    executed in the reverse order of registration.
    
    If you don't call `commit()` or `rollback()`, an exception causes an automatic
    rollback and a successful termination of the block causes an automatic commit
    at the end of the `with` block.
    
    Once a transaction is committed or rolled back, it is reset to the intial
    state (all undo steps are discarded) and can be used again.
    """
    
    __slots__ = ("_stack",)
    
    _stack: list[typing.Callable[[]]]
    
    def __init__(self):
        self._stack = []
    
    def __enter__(self) -> Transaction:
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
    
    def add_undo(self, handler: typing.Callable[[]]):
        """
        Push a new step to the undo stack
        
        :param handler: The callback undoing the preceding operation
        """
        
        self._stack.append(handler)
    
    def commit(self):
        """
        Closes the transaction as successful.
        
        Clears the undo stack without executing any. The transaction
        can be used again after this.
        """
        
        self._stack = []

    def rollback(self):
        """
        Closes the transaction as failed.
        
        Executes the undo steps in reverse order. The transaction
        can be used again after this.
        """
        
        errors: list[Exception] = []
        
        while self._stack:
            handler = self._stack.pop()
            
            try:
                handler()
            except Exception as e:
                errors.append(e)
        
        if errors:
            raise ExceptionGroup(f"Failed to rollback transaction", errors)


__all__ = [
    "Transaction",
]
