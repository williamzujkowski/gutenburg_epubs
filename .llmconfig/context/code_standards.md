# Code Standards Context

This document provides key contextual information about the project's coding standards for reference when generating or modifying code.

## Python Style Guide Summary

- **Base Standard:** PEP 8 with Black formatting (88 character line length)
- **Naming Conventions:**
  - Variables, functions, methods: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_SNAKE_CASE`
  - Private attributes/methods: `_leading_underscore`
- **Type Annotations:** Required for all function parameters and return values
- **Docstrings:** Google-style format with type information

## Error Handling Practices

- Define and use custom exception classes in `exceptions.py`
- Catch specific exceptions rather than broad exception types
- Include context information in exception messages
- Use structured logging for error reporting
- Design for graceful degradation when possible

## Data Pipeline Standards

- Validate inputs at the entry points of each component
- Handle missing or malformed data gracefully
- Provide clear error messages for data validation failures
- Design for idempotent operations where possible
- Include detailed logging at key processing stages

## Testing Philosophy

- Use hypothesis-based tests for core functionality
- Include regression tests for known edge cases
- Use property-based testing for data transformation logic
- Mock external dependencies in unit tests
- Aim for high test coverage (85%+ overall, 95%+ for critical components)
EOF < /dev/null
