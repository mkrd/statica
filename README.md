Statica
========================================================================================

![Tests](https://git.budgetflow.cc/mkrd/statica/actions/workflows/test.yml/badge.svg)
![Coverage](https://git.budgetflow.cc/mkrd/statica/raw/branch/main/assets/coverage.svg)


Statica is a Python library for defining and validating structured data with type annotations and constraints. It provides an easy-to-use framework for creating type-safe models with comprehensive validation for both types and constraints.


Why Statica?
----------------------------------------------------------------------------------------

Statica was created to address the need for a lightweight, flexible, and dependency-free alternative to Pydantic.
While pydantic is a powerful tool for data validation and parsing, Statica offers some distinct advantages in specific situations:

1. **Lightweight**: Statica has zero dependencies, making it ideal for projects where minimizing external dependencies is a priority.
2. **Performance**: For use cases where performance is critical. Pydantic needs `3x` more memory than Statica for the same models.
3. **Ease of Use**: With its simple, Pythonic design, Statica is intuitive for developers already familiar with Python's `dataclasses` and type hinting. It avoids much of the magic and complexity of Pydantic.
4. **Customizable**: Statica allows fine-grained control over type and constraint validation through customizable fields and error classes.


Features
----------------------------------------------------------------------------------------

- **Type Validation**: Automatically validates types for attributes based on type hints, including
  `tuple`, `frozenset`, `Literal`, `Optional`, `Any`, and abstract containers such as `Sequence`,
  `Mapping`, and `Set`.
- **Constraint Validation**: Define constraints like minimum/maximum length, value ranges, and more.
- **Custom & Cross-Field Validation**: Per-field validators plus an overridable `__post_init__` hook
  for cross-field and conditional checks.
- **Full Error Paths**: Errors report the full location, e.g. `User.address.street: expected type 'str', got 'int'`.
- **Serialization & Coercion**: Built-in coercion for `datetime`, `date`, `time`, `UUID`, `Decimal`,
  and `Enum`, with extensible codecs and per-field serialization hooks.
- **Frozen Models**: Opt into immutable, hashable models with `frozen=True`.
- **Value Semantics**: Value-based equality and optional ordering, configured per class.
- **Default Field Values**: Set default values for fields that are used when not explicitly provided.
- **Customizable Error Handling**: Use custom exception classes for type and constraint errors.
- **Flexible Field Descriptors**: Add constraints, casting, and other behaviors to your fields.
- **Optional Fields**: Support for optional fields with default values.
- **Automatic Initialization**: Automatically generate constructors (`__init__`) for your models.
- **String Manipulation**: Strip whitespace from string fields if needed.
- **Casting**: Automatically cast values to the desired type.
- **Field Aliasing**: Support for field aliases for parsing and serialization.


Installation
----------------------------------------------------------------------------------------

You can install Statica via pip:

```bash
pip install statica
```


Getting Started
----------------------------------------------------------------------------------------

### Basic Usage

Define a model with type annotations and constraints:

```python
from statica.core import Statica, Field

class Payload(Statica):
    name: str = Field(min_length=3, max_length=50, strip_whitespace=True)
    description: str | None = Field(max_length=200)
    num: int | float
    float_num: float | None
```

Instantiate the model using a dictionary:

```python
data = {
    "name": "Test Payload",
    "description": "A short description.",
    "num": 42,
    "float_num": 3.14,
}

payload = Payload.from_map(data)
print(payload.name)  # Output: "Test Payload"
```

Or instantiate directly:

```python
payload = Payload(
    name="Test",
    description="This is a test description.",
    num=42,
    float_num=3.14,
)
```

### Validation

Statica automatically validates attributes based on type annotations and constraints:

```python
from statica.core import ConstraintValidationError, TypeValidationError

try:
    payload = Payload(name="Te", description="Valid", num=42)
except ConstraintValidationError as e:
    print(e)  # Output: "name: length must be at least 3"

try:
    payload = Payload(name="Test", description="Valid", num="Invalid")
except TypeValidationError as e:
    print(e)  # Output: "num: expected type 'int | float', got 'str'"
```

### Optional Fields

Fields annotated with `| None` are optional and default to `None`:

```python
class OptionalPayload(Statica):
    name: str | None

payload = OptionalPayload()
print(payload.name)  # Output: None
```

### Default Field Values

You can specify default values for fields in two ways:

#### Using Field() with default parameter

```python
class User(Statica):
    name: str
    age: int = Field(default=25)
    active: bool = Field(default=True)

# Using direct initialization
user = User(name="John")
print(user.name)    # Output: "John"
print(user.age)     # Output: 25
print(user.active)  # Output: True

# Using from_map
user = User.from_map({"name": "Jane"})
print(user.age)     # Output: 25 (default used)

# Explicit values override defaults
user = User(name="Bob", age=30, active=False)
print(user.age)     # Output: 30
```

#### Direct assignment (without Field)

You can also assign default values directly to fields without using `Field()`:

```python
class Config(Statica):
    name: str
    timeout: float = 30.0      # Direct assignment
    retries: int = 3           # Direct assignment
    debug: bool = False        # Direct assignment

config = Config(name="server")
print(config.timeout)  # Output: 30.0
print(config.retries)   # Output: 3
print(config.debug)     # Output: False

# Works with from_map too
config = Config.from_map({"name": "api-server"})
print(config.timeout)  # Output: 30.0 (default used)
```

Both approaches work identically and can be mixed within the same class. Use `Field(default=...)` when you need additional constraints or options, and direct assignment for simple defaults.

#### Validation and Safety

Default values are validated against any constraints you've defined:

```python
class Config(Statica):
    timeout: float = Field(default=30.0, min_value=1.0, max_value=120.0)
    retries: int = Field(default=3, min_value=1)

config = Config()  # Uses defaults: timeout=30.0, retries=3
```

For mutable default values (like lists, dicts, sets), Statica automatically creates copies to prevent shared state issues:

```python
class UserProfile(Statica):
    name: str
    tags: list[str] = Field(default=[])  # or tags: list[str] = []

user1 = UserProfile(name="Alice")
user2 = UserProfile(name="Bob")

user1.tags.append("admin")
print(user1.tags)  # Output: ["admin"]
print(user2.tags)  # Output: [] (not affected)
```

### Field Constraints

You can specify constraints and options on fields:

- **Default Values**: `default` (using `Field()`) or direct assignment
- **String Constraints**: `min_length`, `max_length`, `strip_whitespace`
- **Numeric Constraints**: `min_value`, `max_value`
- **Casting**: `cast_to`
- **Aliasing**: `alias`

```python
class StringTest(Statica):
    name: str = Field(min_length=3, max_length=5, strip_whitespace=True)

class IntTest(Statica):
    num: int = Field(min_value=1, max_value=10, cast_to=int)

class DefaultTest(Statica):
    # Using Field() for defaults with constraints
    status: str = Field(default="active")
    priority: int = Field(default=1, min_value=1, max_value=5)

    # Direct assignment for simple defaults
    timeout: float = 30.0
    retries: int = 3
```

### Custom Error Classes

You can define custom error classes for type and constraint validation:

```python
class CustomError(Exception):
    pass

class CustomPayload(Statica):
    constraint_error_class = CustomError

    num: int = Field(min_value=1, max_value=10)

try:
    payload = CustomPayload(num=0)
except CustomError as e:
    print(e)  # Output: "num: must be at least 1"
```

Or, define a BaseClass which configures the error classes globally:

```python
from statica.core import Statica, ConstraintValidationError, TypeValidationError

class BaseClass(Statica):
    constraint_error_class = ConstraintValidationError
    type_error_class = TypeValidationError

class CustomPayload(BaseClass):
    num: int = Field(min_value=1, max_value=10)

try:
    payload = CustomPayload(num=0)
except ConstraintValidationError as e:
    print(e)  # Output: "num: must be at least 1"
```


Aliasing
----------------------------------------------------------------------------------------

Statica supports field aliasing, allowing you to map different field names for parsing and serialization.
This is particularly useful when working with external APIs that use different naming conventions.

Use the `alias` parameter to define an alternative name for both parsing and serialization:

```python
class User(Statica):
    full_name: str = Field(alias="fullName")
    age: int = Field(alias="userAge", default=25)

# Parse data with aliases
data = {"fullName": "John Doe"}  # userAge not provided, uses default
user = User.from_map(data)
print(user.full_name)  # Output: "John Doe"
print(user.age)        # Output: 25

# Serialize back with aliases (uses the alias for serialization by default)
result = user.to_dict()
print(result)  # Output: {"fullName": "John Doe", "userAge": 25}

# Serialize without aliases
result_no_alias = user.to_dict(with_aliases=False)
print(result_no_alias)  # Output: {"full_name": "John Doe", "age": 25}

```

Advanced Usage
----------------------------------------------------------------------------------------

### Custom Initialization

Statica automatically generates an `__init__` method based on type annotations, ensuring that all required fields are provided during initialization.

### Casting

You can automatically cast input values to the desired type:

```python
class CastingExample(Statica):
    num: int = Field(cast_to=int)

instance = CastingExample(num="42")
print(instance.num)  # Output: 42
```


Supported Types
----------------------------------------------------------------------------------------

Statica validates a wide range of type annotations, including nested and generic types:

```python
from typing import Any, Literal, Optional
from collections.abc import Sequence, Mapping

class Example(Statica):
    a: tuple[int, str]          # fixed-length tuple
    b: tuple[int, ...]          # variadic tuple
    c: frozenset[int]           # frozenset
    d: Sequence[int]            # abstract containers (Sequence, Mapping, Set, Collection)
    e: Mapping[str, int]
    f: Literal["r", "w"]        # literal values
    g: Optional[int]            # Optional / typing.Union / X | Y
    h: Any                      # accepts anything
```

Abstract containers (`Sequence`, `Mapping`, `Set`, `Collection`, `Container`, and their `Mutable*`
variants) validate their items but leave the value unchanged. `str`/`bytes` are rejected for abstract
container annotations, and bare `Iterable`/`Iterator`/`Generator` are not supported because validating
them would consume the iterable.

### Recursive models

Models may reference themselves (or each other) using string forward references. The annotation is
resolved lazily, so self-referential and mutually-referential models work as long as they are defined
at module scope:

```python
class Category(Statica):
    name: str
    children: list["Category"] = Field(default=[])

tree = Category.from_map({
    "name": "root",
    "children": [{"name": "a", "children": [{"name": "a1"}]}, {"name": "b"}],
})
```

Error paths follow the recursion, e.g. `Category.children[0].children[0].name: ...`.


Class Configuration
----------------------------------------------------------------------------------------

Models are configured with class keyword arguments:

```python
class CustomerModel(
    Statica,
    init=True,    # generate __init__ (default True; set False to write your own)
    frozen=True,  # immutable + hashable (default False)
    eq=True,      # value-based equality (default True)
    order=True,   # generate <, <=, >, >= (default False)
):
    id: int
    name: str
```

These options are inherited by subclasses unless overridden, so a shared base can configure them once:

```python
class BaseModel(Statica, frozen=True):
    pass

class User(BaseModel):  # also frozen
    id: int
```

Note: because a type checker cannot see that `frozen` is inherited at runtime, restate `frozen=True`
on subclasses if you want static frozen-consistency checks to pass.

### Frozen models

`frozen=True` blocks attribute assignment after initialization and makes the model hashable:

```python
class Point(Statica, frozen=True):
    x: int
    y: int

p = Point(x=1, y=2)
p.x = 5            # raises FrozenInstanceError
{p}                # hashable, usable in sets and as dict keys
```

Hashing mirrors `dataclasses`: `frozen=True, eq=True` models are hashable; the default
(`frozen=False, eq=True`) model is unhashable; and `eq=False` models keep identity hashing.


Custom and Cross-Field Validation
----------------------------------------------------------------------------------------

Provide a per-field validator that may transform the value or reject it. It runs last, after type and
constraint checks:

```python
def normalize_email(value: str) -> str:
    if "@" not in value:
        raise ValueError("invalid email")
    return value.lower()

class Account(Statica):
    email: str = Field(validator=normalize_email)
```

For cross-field or conditional validation, define `__post_init__`; it runs at the end of
initialization (including `from_map`):

```python
class DateRange(Statica):
    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start > self.end:
            raise ValueError("start must be <= end")
```


Serialization and Type Coercion
----------------------------------------------------------------------------------------

`datetime`, `date`, `time`, `UUID`, `Decimal`, and `Enum` fields are decoded from their JSON-friendly
representation on input and encoded back on `to_dict`. Coercion applies recursively inside containers:

```python
from datetime import datetime
from uuid import UUID

class Event(Statica):
    when: datetime
    id: UUID
    stamps: list[datetime]

event = Event.from_map({
    "when": "2020-01-02T03:04:05",
    "id": "12345678-1234-5678-1234-567812345678",
    "stamps": ["2021-01-01T00:00:00"],
})

event.to_dict()  # {"when": "2020-01-02T03:04:05", "id": "1234...", "stamps": ["2021-01-01T00:00:00"]}
```

`to_dict` also recurses into nested models and containers of models. Register custom codecs via the
config, or override serialization for a single field:

```python
from statica import Codec, StaticaConfig

config = StaticaConfig.create(codecs={MyType: Codec(decode=MyType.parse, encode=str)})

class Model(Statica, config=config):
    value: int = Field(serializer=lambda v: f"#{v}")  # per-field output hook
```


Error Context
----------------------------------------------------------------------------------------

Validation errors report the full path to the offending value, including nested models, list and
tuple indices, and mapping keys:

```python
class Street(Statica):
    name: str

class User(Statica):
    street: Street

User.from_map({"street": {"name": 123}})
# TypeValidationError: User.street.name: expected type 'str', got 'int'
```


Design Decisions
----------------------------------------------------------------------------------------

- [Inheritance over Decorators](docs/decision-inheritance-over-decorators.md)
- [Class Configuration and Value Semantics](docs/decision-class-configuration.md)


Contributing
----------------------------------------------------------------------------------------

We welcome contributions to Statica! To contribute:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Write tests for your changes.
4. Submit a pull request.


License
----------------------------------------------------------------------------------------

Statica is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.


Acknowledgments
----------------------------------------------------------------------------------------

Statica was built to simplify data validation and provide a robust and simple framework for type-safe models in Python, inspired by `pydantic` and `dataclasses`.
