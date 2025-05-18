# Code Generation Prompt Template

Generate code for [specific feature/module description].

## Context

**Project Phase:** [Specify current phase from PROJECT_PLAN.md]
**Component:** [Specify which component this code is for (e.g., datasources, filter, etc.)]
**Purpose:** [Describe the specific purpose of this code]

## Requirements

1. The code should implement [specific functionality details]
2. It must integrate with [existing components/interfaces]
3. Consider [specific constraints or edge cases]

## Coding Standards

All code must follow the standards outlined in the root CLAUDE.md, including:
- PEP 8 compliance with Black formatting (88 char lines)
- Google-style docstrings with type hints
- Custom exception handling
- Comprehensive unit tests
- Modularity and single responsibility

## Test Requirements

Include tests that:
- Validate core functionality
- Test edge cases
- Mock external dependencies
- Maintain code coverage targets (85%+)

## Example Usage

```python
# Example of how the code would be used
```

Additional notes or considerations: [any other relevant information]
EOF < /dev/null
