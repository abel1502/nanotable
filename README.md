# nanotable

[![PyPI - Version](https://img.shields.io/pypi/v/nanotable.svg)](https://pypi.org/project/nanotable)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/nanotable.svg)](https://pypi.org/project/nanotable)
[![codecov](https://codecov.io/gh/abel1502/nanotable/graph/badge.svg?token=ZVUHGZZMKZ)](https://codecov.io/gh/abel1502/nanotable)

Nanotable is meant to bridge the gap between simple collections, such as `list` and `dict`,
and full-on database tables. It lets you store a set of objects, index it by
several keys, and more! It's fast, memory-efficient, and well-tested.
The project draws inspiration from [littletable](https://github.com/ptmcg/littletable),
but is a completely original implementation. Its goal is to avoid feature bloat
and maintain performance on par with built-in collections.

There are several situations where you might want to use Nanotable:

- When you'd otherwise use a `dict` from an object's field to the object itself.
  Nanotable does that for you, and also provides additional features, such
  as checking for the existence of an element with a simple `in` check;
  hanging the value of the key field with `Table.rekey`, or catching
  accidental changes to the key field automatically.

- When you'd otherwise use a `bidict`. That's a great library in its own right,
  but Nanotable provides some additional functionality such as storing extra
  non-hashable metadata along your objects (also see the previous point).

- When you'd otherwise use a database. Nanotable spares you the computational
  and mental overhead. You probably have already written your own domain-specific
  version of Nanotable at some point in your life -- now you can use a well-tested
  library instead.

## Installation

```console
pip install nanotable
```

To install with all extras features, instead use:

```console
pip install nanotable[all]
```

## Usage

A basic usage example is given below:

```python
from nanotable import Table

table = Table(of_dicts=True)\
    .primary_index_on("name")\
    .index_on("phone")

table.add({"name": "John Doe", "phone": "123-456-7890", "age": 25})
table.add({"name": "Jane Doe", "phone": "987-654-3210", "age": 26})
table.add({"name": "Barrack Obama", "age": "idk"})

table.at["Jane Doe"]  # {"name": "Jane Doe", "phone": "987-654-3210", "age": 26}
table.by.name["John Doe"]  # Same as above
table.by.phone["987-654-3210"]  # {"name": "Jane Doe", "phone": "987-654-3210", "age": 26}

table.remove(table.by.name["Barrack Obama"])
```

You can store any kind of object in the table. Specify `of_dicts=True` or `getfield_factory=getfield_item`
to use mappings (`dict` or anything with `obj[key]` item access); `of_objects=True` or
`getfield_factory=getfield_attr` to use objects with attributes (`obj.key` access); or
any function with the signature `(obj: Any, key: str) -> Any | MISSING` as `getfield_factory`.
You can also specify `of=MyType` to have the table infer either `of_objects` or `of_dicts`
based on the anticipated element type.

Check out the documentation for `nanotable.Table` to see all the methods supported
by tables.

### Typing

The library is fully type-annotated. To make use of this, at the bare minimum
you can specify the type of the objects you want to store in the table:

```python
table = Table[Person](of_objects=True)
# or
table = Table[dict[str, Any]](of_dicts=True)
```

To add static typing to your indexes, you need to define a type with all of them:

```python
class MyIndexes(Protocol):
    name: UniqueIndex[Person, str]
    phone: UniqueIndex[Person, str]

# The first template parameter is the object type;
# The second template parameter is protocol for `by`;
# The third template parameter is the primary index type.
table = Table[Person, MyIndexes, UniqueIndex[Person, str]](of_objects=True)
table.primary_index_on("name", required=True)
table.index_on("phone")
```

### Indexes

Indexes are used to provide fast and efficient lookup of elements by the
value of one of the fields. All indexes must inherit from `nanotable.Index`.
If you wish to implement your own, consult the documentation of that class
to see which methods you need to implement.

Broadly, the interface of an index consists of:
- `register`, which adds an element to the index
- `unregister`, which removes an element from the index
- `get`, which returns the element or elements corresponding to the key
  (the type of the result depends on the specific index, but it is always
  semantically equivalent to a collection of stored objects, and can be
  transformed to a list with `result_items`).
- `[]` item lookup, which is a shortcut for `get` and the most frequent operation
  you will likely perform while using an index.
- More utility methods, which you can find by exploring the index documentation.

Any index can be required or not, which is controlled by the `required`
boolean parameter. A required index will raise an error when encounering an
object with no value for its field. If an index is not required, it will
simply ignore such objects. By default, `None` will be considered missing, but
you may override this by setting `none_means_empty=False`, in which case `None`
will be treated as a regular value.

An index has a name, which should correspond to the field it indexes. However,
indexes rely on a customizable `getfield` function to extract the field value,
which allows indexes on properties that would not be considered fields in a
conventional way: for example, a tuple of several fields, or a nested field.
In this case the name should convey the same information to a human, but it
is important not to treat it as a source of truth. `getfield` is a function
with the signature `(obj: Any) -> Any | MISSING`. When defining your own `getfield`,
remember to return `nanotable.MISSING` instead of `None` or raising exceptions
when the provided object does not have the required fields (for example when
it's of the wrong type).

Any `required=True` index can be used as a primary index for a table, though
a `UniqueIndex` (or one of its subclasses) is recommended.

Nanotable provides the following types of indexes out of the box:

- `nanotable.UniqueIndex`. Requires that no two elements in the table share
  the same value for the index field. Lookups return the only element with the
  specified value, or raise a `KeyError` if there is none. The values of the
  indexed field must be hashable.

- `nanotable.MultiIndex`. Supports duplicate values for the index field.
  Lookups return a `list` of all elements with a given value for the index field,
  including potentially an empty list. The values of the
  indexed field must be hashable.

With the `sorted` extra installed (`pip install nanotable[sorted]`), you will
also have access to the following indexes:

- `nanotable.SortedUniqueIndex`. Has the same requirements as `UniqueIndex`,
  but maintains elements in sorted order of their indexed field. Beside
  single-item lookups, provides efficient range lookups with `get_range` and
  `[low:high]`. The values of the indexed field must be hashable and comparable.

- `nanotable.SortedMultiIndex`. Has the same requirements as `MultiIndex`,
  but maintains elements in sorted order of their indexed field. Beside
  `list` lookups, provides efficient range lookups with `get_range` and
  `[low:high]`. The values of the indexed field must be hashable and comparable.

### Storage

Storage is what holds the elements of the table. In a sense, it simply abstracts
a collection with a consistent interface. All storage implementations
must inherit from `nanotable.Storage`. If you wish to implement your own,
consult the documentation of that class and `nanotable.WrapperStorage` to see
which methods you need to implement.

If your table uses a primary index, it does not need a storage and will
use the index for that purpose. (Unlike a conventional database, since Python
already stores objects by-reference, our indexes have access to the objects
themselves rather than indexes to the storage). Note that this is the only
difference between a primary and a regular index. If you want to use a
custom storage, you do not need to (and cannot) specify a primary index.

Nanotable provides the following types of storage out of the box:

- `nanotable.ListStorage`. Stores items in a `list`, prohibiting duplicates.
  Preserves insertion order. Linear time for mutation and presence checks.

- `nanotable.MultiListStorage`. Stores items in a `list` but allows duplicates.
  Preserves insertion order. Linear time for mutation and presence checks.

- `nanotable.SetStorage`. Stores items in a `set`, prohibiting duplicates.
  Does not preserve insertion order. O(1) time for mutation and presence checks.
  Requires objects to be hashable.

- `nanotable.OrderedSetStorage`. Stores items in a `dict` with `None`-values,
  essentially emulating a set but making use of Python 3.6+ `dict`'s ordered
  nature. Preserves insertion order. O(1) time for mutation and presence checks.
  Requires objects to be hashable.

- `nanotable.IndexViewStorage`. Relies on some kind of index to store items.
  Semantics depend on index semantics, but for all built-in indexes, the
  performance is O(1) time for mutation and presence checks. This is used
  automatically when you define a primary index for a table.

### Caveats

Indexed fields must be hashable, like with the built-in `dict`. This already
imposes the restriction that they must be immutable (which is why you can't
use, for example, a `list` as a `dict` key -- see [here](https://docs.python.org/3/faq/design.html#why-must-dictionary-keys-be-immutable) to learn why).
With Nanotable, however, comes the additional restriction that the value of the
indexed field itself **mustn't be changed**. For a `dict` this obviously isn't
a concern since it stores keys and values separately, inaccessible to the user.
Nanotable will try to detect this happening and warn you, but this unfortunately cannot be done reliably.
If you wish to change an indexed field, the correct way to do that is to
remove it from the table, change the field and re-add it. Nanotable provides
a helper that does this for you:

```python
with table.rekey(obj):
    obj.field = new_value
```

If a field is not indexed, this is unnecessary.

If you are certain that your code never modifies an indexed field of an object
in a `Table`, you can disable the checks that issue the warning by setting
`nanotable.safety.disable_safety_checks` to `False`. This provides a small
performance improvement, with the downside that any potential bugs will be
almost impossible to catch and will show up as subtly wrong results. It is
recommended that you keep the safety checks on unless you know what you're
doing.

Nanotable is also not thread-safe. When using a `Table` from multiple threads
at once, use a synchronization primitive such as a `threading.Lock` to ensure
that only one thread can interact with the table at a time. Multithreaded
read-only access should theoretically be fine.

## License

Nanotable is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
See the [LICENSE.txt](LICENSE.txt) for details.

© 2026 abel1502
