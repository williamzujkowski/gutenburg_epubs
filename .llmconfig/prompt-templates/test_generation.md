# Test Generation Prompt Template

Generate comprehensive tests for [specific component/module].

## Context

**Project Phase:** [Specify current phase from PROJECT_PLAN.md]
**Component:** [Specify which component these tests are for]
**Purpose:** [Describe what functionality the tests should verify]

## Testing Requirements

The tests should verify:
1. [Core functionality to test]
2. [Edge cases to consider]
3. [Error handling scenarios]

## Testing Standards

All tests must follow the standards outlined in the root CLAUDE.md, including:
- Hypothesis tests for behavior validation
- Regression tests for known edge cases
- Property-based testing where applicable
- High code coverage (85%+ target)
- Mocking external dependencies
- Descriptive test names and docstrings

## Implementation Details

```python
# Provide relevant code snippets or interfaces being tested
```

Additional considerations: [any other relevant information]
EOF < /dev/null
