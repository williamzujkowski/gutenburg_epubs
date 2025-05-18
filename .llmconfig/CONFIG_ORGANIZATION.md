# Claude Configuration Organization

This document outlines the organization of Claude AI configuration files across the repository.

## Organization Principles

1. **Clear Hierarchy**:
   - Root CLAUDE.md: Contains comprehensive project standards and guidance
   - .llmconfig files: Provide specific implementation details and examples

2. **Modularity**:
   - Each configuration file has a clear, specific purpose
   - Files are organized in thematic directories

3. **Discoverability**:
   - Files use consistent naming conventions
   - Directory structure reflects logical categories

## File Structure and Purpose

### Root Directory

- **CLAUDE.md**: The primary entry point for Claude. Contains comprehensive project standards, coding guidelines, and testing manifesto. Imports all other configuration files.

### .llmconfig Directory

#### Core Configuration Files:

- **CLAUDE.md**: Project-specific instructions for Claude when working with this codebase
- **agent-rules.md**: Specific coding standards and best practices for AI agents
- **PROJECT_PLAN.md**: Current implementation plans, phase information, and priorities

#### Subdirectories:

- **prompt-templates/**: Standardized templates for requesting specific types of work
  - code_generation.md: Template for requesting new code implementation
  - test_generation.md: Template for requesting test suite creation

- **context/**: Subject-specific contextual information
  - code_standards.md: Specific code standards context for this project
  - vulnerability_domain.md: Domain knowledge about vulnerabilities (to be added)

- **examples/**: Example implementations that follow project standards
  - good_module.py: Reference implementation of a well-structured module
  - good_test.py: Reference implementation of comprehensive tests

- **system-prompts/**: System-level instructions for Claude
  - code_assistant.md: System prompt for code assistance tasks

## Usage Guidelines

1. Keep the root CLAUDE.md focused on comprehensive standards and principles
2. Use .llmconfig files for specific implementation details and examples
3. When adding new configuration files, follow existing naming and organization patterns
4. Update this document when changing the configuration organization