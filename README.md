# nanotable

[![PyPI - Version](https://img.shields.io/pypi/v/nanotable.svg)](https://pypi.org/project/nanotable)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/nanotable.svg)](https://pypi.org/project/nanotable)

[TODO: Code coverage report]

*This is a work in progress. Star/follow this repository to be notified of the first release.*

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

-----

## Installation

```console
pip install nanotable
```

## Usage

A basic usage example is given below:

```python
from nanotable import Table, dict_getter

table = Table(of_dicts=True)\
    .index_on("name", required=True)\
    .index_on("phone")

table.add({"name": "John Doe", "phone": "123-456-7890", "age": 25})
table.add({"name": "Jane Doe", "phone": "987-654-3210", "age": 26})
table.add({"name": "Barrack Obama", "age": "idk"})

table.by.name["John Doe"]  # {"name": "John Doe", "phone": "123-456-7890", "age": 25}
table.by.phone["987-654-3210"]  # {"name": "Jane Doe", "phone": "987-654-3210", "age": 26}

table.remove(table.by.name["Barrack Obama"])
```

You can store any kind of object in the table. Specify `of_dicts=True` or `getfield=dict_getter`
to use mappings (`dict` or anything with `obj[key]` item access); `of_objects=True` or
`getfield=attr_getter` to use objects with attributes (`obj.key` access); or
any function with the signature `(obj, key: str) -> Any | MISSING` as `getfield`.

### Typing

The library is fully type-annotated. To make use of this, at the bare minimum
you can specify the type of the objects you want to store in the table:

```python
table = Table[Person](of_objects=True)
# or
table = Table[dict[str, Any]](of_objects=True)
```

To add static typing to your indexes, you need to define a type with all of them:

```python
class MyIndexes(Protocol):
    name: UniqueIndex[Person, str]
    phone: UniqueIndex[Person, str]

table = Table[Person, MyIndexes](of_objects=True)
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
