# Statica

![Tests](https://github.com/mkrd/statica/actions/workflows/test.yml/badge.svg)
![Coverage](https://github.com/mkrd/statica/blob/main/assets/coverage.svg?raw=true)


Statica is a Python library for defining and validating structured data with type annotations and constraints. It provides an easy-to-use framework for creating type-safe models with comprehensive validation for both types and constraints.

## Why Statica?

Statica was created to address the need for a lightweight, flexible, and dependency-free alternative to libraries like pydantic. 
While pydantic is a powerful tool for data validation and parsing, Statica offers some distinct advantages in specific situations:

1. **Lightweight**: Statica does not rely on any third-party dependencies, making it ideal for projects where minimizing external dependencies is a priority.
2. **Customizable Validation**: Statica allows fine-grained control over type and constraint validation through customizable field descriptors (`Field`) and error classes.
3. **Ease of Use**: With its simple, Pythonic design, Statica is intuitive for developers already familiar with Python's `dataclasses` and type hinting. It avoids much of the magic that pydantic employs.
4. **Performance**: For use cases where performance, especially memory usage, is critical, Statica avoids some of the overhead introduced by the advanced features of pydantic.

## Features

- **Type Validation**: Automatically validates types for attributes based on type hints.
- **Constraint Validation**: Define constraints like minimum/maximum length, value ranges, and more.
- **Customizable Error Handling**: Use custom exception classes for type and constraint errors.
- **Flexible Field Descriptors**: Add constraints, casting, and other behaviors to your fields.
- **Optional Fields**: Support for optional fields with default values.
- **Automatic Initialization**: Automatically generate constructors (`__init__`) for your models.
- **String Manipulation**: Strip whitespace from string fields if needed.
- **Casting**: Automatically cast values to the desired type.

## Installation

You can install Statica via pip:

```bash
pip install statica
```

## Getting Started

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

## Advanced Usage

### Short Syntax for Fields

You can use simple type annotations without explicitly defining `Field` descriptors:

```python
class ShortSyntax(Statica):
    name: str

short = ShortSyntax(name="Test")
print(short.name)  # Output: "Test"
```

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

## Contributing

We welcome contributions to Statica! To contribute:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Write tests for your changes.
4. Submit a pull request.

## License

Statica is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

## Acknowledgments

Statica was built to simplify data validation and provide a robust and simple framework for type-safe models in Python, inspired by `pydantic` and `dataclasses`.

