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

table = Table(getfield=dict_getter).index_on("name").index_on("phone", required=False)

table.add({"name": "John Doe", "phone": "123-456-7890", "age": 25})
table.add({"name": "Jane Doe", "phone": "987-654-3210", "age": 26})
table.add({"name": "Barrack Obama", "age": "idk"})

table.by.name["John Doe"]  # {"name": "John Doe", "phone": "123-456-7890", "age": 25}
table.by.phone["987-654-3210"]  # {"name": "Jane Doe", "phone": "987-654-3210", "age": 26}

table.remove(table.by.name["Barrack Obama"])
```

TODO: typed example

TODO: warn about mutation and `rekey`

## License

`nanotable` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
See the [LICENSE.txt](LICENSE.txt) for details.

© 2026 abel1502
