
Class Configuration and Value Semantics
----------------------------------------------------------------------------------------

Statica configures models through class keyword arguments rather than a separate decorator or a
config object per option:

```python
class CustomerModel(Statica, init=False, frozen=True, eq=False, order=False):
    id: int
    name: str
```

This mirrors `typing.dataclass_transform` (PEP 681) and keeps configuration next to the class
definition. The metaclass already accepted `config=` this way, so `init`/`frozen`/`eq`/`order` reuse
the same mechanism instead of introducing a second one.


Why these defaults?
----------------------------------------------------------------------------------------

The runtime defaults match `dataclasses` so the behavior is unsurprising to Python developers:

- `init=True`: a keyword-only `__init__` is generated. Set `init=False` to write your own.
- `frozen=False`: models are mutable by default.
- `eq=True`: models compare by value. This changed in 2.0 (previously identity).
- `order=False`: comparison operators are opt-in, since ordering requires every field to be mutually
  orderable and is rarely wanted.

Hashing follows the `dataclasses` rules exactly:

| `eq`   | `frozen` | `__hash__`                     |
|--------|----------|--------------------------------|
| True   | True     | derived from the field values  |
| True   | False    | `None` (unhashable)            |
| False  | any      | identity hash (inherited)      |

A consequence is that the *default* model (`eq=True, frozen=False`) is unhashable, just like a plain
`@dataclass`. Use `frozen=True` for hashable models.


Inheritance of options
----------------------------------------------------------------------------------------

Unlike `dataclasses`, where every class re-declares its configuration, Statica inherits `config`,
`init`, `frozen`, `eq`, and `order` from the nearest base when a subclass does not restate them. This
makes a shared base practical:

```python
class BaseModel(Statica, frozen=True):
    pass

class User(BaseModel):  # inherits frozen=True at runtime
    id: int
```

Trade-off: `dataclass_transform` cannot express that `frozen` is inherited, so a type checker assumes
subclasses are non-frozen and flags a frozen-consistency error. Restate `frozen=True` on the subclass
if you rely on static checking. Field inheritance itself (a subclass seeing its base's fields in
`__init__`, `from_map`, `to_dict`, and equality) is always collected across the MRO.


Immutability implementation
----------------------------------------------------------------------------------------

Frozen models generate `__setattr__`/`__delattr__` that raise `FrozenInstanceError` (an
`AttributeError` subclass, mirroring `dataclasses.FrozenInstanceError`). The generated `__init__`
writes validated values straight to `__dict__`, so initialization still runs full validation while
bypassing the mutation guard. This keeps validation in a single place (the field descriptor's
`validate` method) rather than duplicating it.
