# DBT microservice

A microservice for executing dbt commands via an API.

## Development Setup

1. Install Poetry:
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

2. Clone the repository:
```bash
git clone https://github.com/arthurintelligence/dbt-microservice.git dbt-microservice
cd dbt-microservice
```

3. Install dependencies:
```bash
poetry install
```

4. Install pre-commit hooks:
```bash
poetry run pre-commit install
```

## Development Commands

- Run tests:
```bash
poetry run pytest
```

- Format code:
```bash
poetry run black .
poetry run isort .
```

- Type checking:
```bash
poetry run mypy .
```

- Lint code:
```bash
poetry run flake8
```

## Project Structure

```
project/
    app/               # Application code
    tests/             # Test files
    pyproject.toml     # Poetry configuration
    README.md          # This file
```
