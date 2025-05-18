# AI Agent Rules for the Vulnerability Data Pipeline

This document defines the coding standards and best practices that AI agents should follow when generating or modifying code for this repository.

## Core Principles

1. **Follow Project Standards**: All code must adhere to the comprehensive standards outlined in the root `CLAUDE.md` file.

2. **Alignment with Project Plan**: Before generating code, review the PROJECT_PLAN.md file to ensure solutions align with the current phase objectives and overall project vision.

3. **Modularity**: Create focused, self-contained components that can be tested independently.

4. **Type Safety**: Always include proper type hints for all functions and classes.

5. **Documentation**: Include Google-style docstrings for all public interfaces.

6. **Testing**: Generate appropriate unit and integration tests for all new code.

7. **Security**: Follow security best practices, especially when handling external data sources.

## Code Style Requirements

- **PEP 8 + Black**: Format all Python code to be PEP 8 compliant, with Black's 88-character line limit.
- **Import Order**: Use isort for organizing imports (stdlib → third-party → local).
- **Naming Convention**: snake_case for variables/functions, PascalCase for classes, UPPER_SNAKE_CASE for constants.
- **Function Length**: Aim for functions under 50 lines.
- **Nesting**: Avoid deep nesting (more than 3 levels).
- **Comments**: Use comments for explaining "why", not "what" (code should be self-documenting).

## Error Handling Standards

- Use custom exception classes defined in `exceptions.py`.
- Catch specific exceptions, not generic Exception.
- Include context in exception messages.
- Implement proper cleanup in finally blocks where needed.
- Add structured logging for errors with appropriate context.

## Data Processing Guidelines

- Validate inputs early in the processing pipeline.
- Handle missing or malformed data gracefully.
- Include safeguards against common data processing errors.
- Design for efficiency when dealing with large datasets.
- Ensure consistent data transformation between pipeline stages.

## Testing Requirements

- Apply hypothesis-based testing for behavior validation.
- Include regression tests for known issues.
- Test edge cases explicitly (empty data, malformed inputs, etc.).
- Mock external dependencies in unit tests.
- Maintain high code coverage (85%+ as specified in CLAUDE.md).

## Security Considerations

- Treat all external data as untrusted.
- Implement proper input validation.
- Use secure methods for API authentication.
- Avoid hardcoding sensitive information.
- Follow secure coding practices for parsing external data.

Remember to always reference and follow the project standards in CLAUDE.md, which takes precedence over these guidelines in case of any conflicts.
EOF < /dev/null
