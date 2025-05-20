# Contributing to Gutenberg EPUB Downloader

First off, thank you for considering contributing to Gutenberg EPUB Downloader! It's people like you that make it a great tool for everyone.

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to [william.zujkowski@gmail.com](mailto:william.zujkowski@gmail.com).

## How Can I Contribute?

### Reporting Bugs

This section guides you through submitting a bug report. Following these guidelines helps maintainers and the community understand your report, reproduce the behavior, and find related reports.

**Before Submitting A Bug Report:**

* Check the [issues](https://github.com/williamzujkowski/gutenburg_epubs/issues) for a list of current known issues.
* Perform a cursory search to see if the problem has already been reported. If it has and the issue is still open, add a comment to the existing issue instead of opening a new one.

**How Do I Submit A Good Bug Report?**

Bugs are tracked as GitHub issues. Create an issue and provide the following information:

* Use a clear and descriptive title for the issue to identify the problem.
* Describe the exact steps which reproduce the problem.
* Provide specific examples to demonstrate the steps.
* Describe the behavior you observed after following the steps and point out what exactly is the problem with that behavior.
* Explain which behavior you expected to see instead and why.
* Include screenshots and animated GIFs which show you following the described steps and clearly demonstrate the problem.
* If the problem wasn't triggered by a specific action, describe what you were doing before the problem happened.
* Include details about your configuration and environment.

### Suggesting Enhancements

This section guides you through submitting an enhancement suggestion, including completely new features and minor improvements to existing functionality.

**Before Submitting An Enhancement Suggestion:**

* Check if the enhancement has already been suggested.
* Determine which repository the enhancement should be suggested in.
* Perform a cursory search to see if the enhancement has already been suggested. If it has, add a comment to the existing issue instead of opening a new one.

**How Do I Submit A Good Enhancement Suggestion?**

Enhancement suggestions are tracked as GitHub issues. Create an issue and provide the following information:

* Use a clear and descriptive title for the issue to identify the suggestion.
* Provide a step-by-step description of the suggested enhancement in as many details as possible.
* Provide specific examples to demonstrate the steps.
* Describe the current behavior and explain which behavior you expected to see instead and why.
* Explain why this enhancement would be useful to most users.
* List some other tools or applications where this enhancement exists.
* Specify which version you're using.
* Specify the name and version of the OS you're using.

### Pull Requests

* Fill in the required template
* Do not include issue numbers in the PR title
* Include screenshots and animated GIFs in your pull request whenever possible
* Follow the Python style guides
* Include tests for any new functionality
* End all files with a newline
* Avoid platform-dependent code

## Development Workflow

### Setting up the development environment

1. Fork the repository to your GitHub account
2. Clone your fork to your local machine
   ```
   git clone https://github.com/your-username/gutenburg_epubs.git
   cd gutenburg_epubs
   ```
3. Create a virtual environment and install dependencies
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements-dev.txt
   pip install -e .
   ```
4. Set up pre-commit hooks
   ```
   pre-commit install
   ```

### Making Changes

1. Create a new branch for your changes
   ```
   git checkout -b feature/your-feature-name
   ```
2. Make your changes
3. Run the tests to ensure your changes don't break existing functionality
   ```
   pytest
   ```
4. Format your code and run linters
   ```
   ruff check .
   ruff format .
   mypy src/
   ```
5. Commit your changes (using a clear and descriptive commit message)
   ```
   git commit -m "Add feature: your feature description"
   ```
6. Push your changes to your fork
   ```
   git push origin feature/your-feature-name
   ```
7. Create a Pull Request from your fork to the main repository

### Style Guide

This project uses:
- [ruff](https://github.com/charliermarsh/ruff) for linting and formatting
- [mypy](http://mypy-lang.org/) for static type checking
- [Black](https://black.readthedocs.io/en/stable/) compatible formatting

Key style points:
- Use type hints for all function definitions
- Maximum line length is 88 characters
- Use double quotes for strings
- Follow the import order: standard library, third-party packages, local modules
- Use descriptive variable names
- Write comprehensive docstrings in the format shown in existing code

### Testing

- Write tests for all new functionality
- Ensure all tests pass before submitting a pull request
- Maintain or improve code coverage

### Documentation

- Update the README.md if your changes add new features or change existing ones
- Add docstrings to all functions and classes
- Comment complex code sections

## Git Commit Messages

* Use the present tense ("Add feature" not "Added feature")
* Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
* Limit the first line to 72 characters or less
* Reference issues and pull requests liberally after the first line
* Consider starting the commit message with an applicable prefix:
    * `feat:` for new features
    * `fix:` for bug fixes
    * `docs:` for documentation changes
    * `style:` for formatting changes
    * `refactor:` for code restructuring
    * `test:` for test additions or corrections
    * `chore:` for maintenance tasks

## Licensing

By contributing to this project, you agree that your contributions will be licensed under the project's [MIT License](LICENSE).

Thank you for your contributions! ❤️