# nanotable

[![PyPI - Version](https://img.shields.io/pypi/v/nanotable.svg)](https://pypi.org/project/nanotable)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/nanotable.svg)](https://pypi.org/project/nanotable)

Nanotable is meant to bridge the gap between simple collections, such as `list` and `dict`,
and full-on database tables. It lets you store a set of objects, index it by
several keys, and more! The project draws inspiration from [littletable](https://github.com/ptmcg/littletable),
but is a completely original implementation. Its goal is to avoid feature bloat
and maintain performance on par with built-in collections.

-----

## Installation

```console
pip install nanotable
```

## Usage

A basic usage example is given below:

```python
from nanotable import Table, dict_getter

table = Table(getfield=dict_getter)\
    .index_on("name", required=True)\
    .index_on("phone")

table.add({"name": "John Doe", "phone": "123-456-7890", "age": 25})
table.add({"name": "Jane Doe", "phone": "987-654-3210", "age": 26})
table.add({"name": "Barrack Obama", "age": "idk"})

table.by.name["John Doe"]  # {"name": "John Doe", "phone": "123-456-7890", "age": 25}
table.by.phone["987-654-3210"]  # {"name": "Jane Doe", "phone": "987-654-3210", "age": 26}

table.remove(table.by.name["Barrack Obama"])
```

You can store any kind of object in the table. Specify `getfield=dict_getter`
to use mappings (`dict` or anything with `obj[key]` item access), or
`getfield=attr_getter` to use objects with attributes (`obj.key` access).
You may also define your own `getfield` function with the signature `(obj, key: str) -> Any | MISSING`.

### Typing

The library is fully type-annotated. To make use of this, at the bare minimum
you can specify the type of the objects you want to store in the table:

```python
table = Table[Person](getfield=attr_getter)
# or
table = Table[dict[str, Any]](getfield=dict_getter)
```

To add static typing to your indexes, you need to define a type with all of them:

```python
class MyIndexes(Protocol):
    name: UniqueIndex[Person, str]
    phone: UniqueIndex[Person, str]

table = Table[Person, MyIndexes](getfield=attr_getter)
table.index_on("name", required=True)
table.index_on("phone")
```

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

Nanotable is also not thread-safe. When using a `Table` from multiple threads
at once, use a synchronization primitive such as a `threading.Lock` to ensure
that only one thread can interact with the table at a time. Multithreaded
read-only access should theoretically be fine.

## License

Nanotable is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
See the [LICENSE.txt](LICENSE.txt) for details.

© 2026 abel1502
