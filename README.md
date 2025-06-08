Statica
========================================================================================

![Tests](https://github.com/mkrd/statica/actions/workflows/test.yml/badge.svg)
![Coverage](https://github.com/mkrd/statica/blob/main/assets/coverage.svg?raw=true)


Statica is a Python library for defining and validating structured data with type annotations and constraints. It provides an easy-to-use framework for creating type-safe models with comprehensive validation for both types and constraints.


Why Statica?
----------------------------------------------------------------------------------------

Statica was created to address the need for a lightweight, flexible, and dependency-free alternative to libraries like Pydantic.
While pydantic is a powerful tool for data validation and parsing, Statica offers some distinct advantages in specific situations:

1. **Lightweight**: Statica has zero dependencies, making it ideal for projects where minimizing external dependencies is a priority.
2. **Performance**: For use cases where performance is critical. Pydantic needs `3x` more memory than Statica for the same models.
3. **Ease of Use**: With its simple, Pythonic design, Statica is intuitive for developers already familiar with Python's `dataclasses` and type hinting. It avoids much of the magic and complexity of Pydantic.
4. **Customizable**: Statica allows fine-grained control over type and constraint validation through customizable fields and error classes.


Features
----------------------------------------------------------------------------------------

- **Type Validation**: Automatically validates types for attributes based on type hints.
- **Constraint Validation**: Define constraints like minimum/maximum length, value ranges, and more.
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

### Field Constraints

You can specify constraints on fields:

- **String Constraints**: `min_length`, `max_length`, `strip_whitespace`
- **Numeric Constraints**: `min_value`, `max_value`
- **Casting**: `cast_to`

```python
class StringTest(Statica):
    name: str = Field(min_length=3, max_length=5, strip_whitespace=True)

class IntTest(Statica):
    num: int = Field(min_value=1, max_value=10, cast_to=int)
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

### Basic Aliases

Use the `alias` parameter to define an alternative name for both parsing and serialization:

```python
class User(Statica):
    full_name: str = Field(alias="fullName")
    age: int = Field(alias="userAge")

# Parse data with aliases
data = {"fullName": "John Doe", "userAge": 30}
user = User.from_map(data)
print(user.full_name)  # Output: "John Doe"
print(user.age)        # Output: 30

# Serialize back with aliases
result = user.to_dict()
print(result)  # Output: {"fullName": "John Doe", "userAge": 30}
```

### Separate Parsing and Serialization Aliases

You can define different aliases for parsing and serialization:

```python
class APIModel(Statica):
    user_name: str = Field(
        alias_for_parsing="userName",
        alias_for_serialization="username"
    )
    user_id: int = Field(alias_for_parsing="userId")

# Parse from camelCase API response
api_data = {"userName": "alice", "userId": 123}
model = APIModel.from_map(api_data)

# Serialize to snake_case for internal use
internal_data = model.to_dict()
print(internal_data)  # Output: {"username": "alice", "user_id": 123}
```

### Alias Priority

When multiple alias types are defined, the priority is:
1. `alias_for_parsing` for parsing operations
2. `alias_for_serialization` for serialization operations
3. `alias` as a fallback for both operations

```python
class PriorityExample(Statica):
    field_name: str = Field(
        alias="generalAlias",
        alias_for_parsing="parseAlias",
        alias_for_serialization="serializeAlias"
    )

# Uses alias_for_parsing
instance = PriorityExample.from_map({"parseAlias": "value"})

# Uses alias_for_serialization
result = instance.to_dict()
print(result)  # Output: {"serializeAlias": "value"}
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
