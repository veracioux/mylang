# Contributing to mylang

Bug fixes are always welcome!

## Feature Requests

This project is in early stages, so I'm picky about new features. **All feature requests must be discussed and approved via GitHub issues before submitting a pull request.** Please create an issue first to discuss the feature proposal.

## Development Setup

This project uses [PDM](https://pdm-project.org/) for dependency management. To set up the development environment:

```bash
pdm install
```

## Running the Language

To run mylang code:

```bash
# Run a mylang file
pdm run mylang path/to/file.my

# Start REPL
pdm run mylang
```

## Testing

Run tests with pytest:

```bash
pdm run pytest
```

## Code Quality

The project uses several tools for code quality:

- **Black** for code formatting (120 character line length)
- **Flake8** for linting (120 character line length)
- **Pylint** for static analysis
- **Pyright** for type checking

Run all quality checks:

```bash
pdm run black .
pdm run flake8 .
pdm run pylint mylang tests
pdm run pyright
```

## Development Scripts

- `scripts/ast.sh` - Debug AST output for mylang code

## Project Structure

- `mylang/` - Language implementation
- `tests/` - Test files and test runners
- `brainstorm/` - Development notes and experiments
