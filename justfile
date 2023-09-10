set windows-shell := ["pwsh.exe", "-NoLogo", "-Command"]

ruff:
    cd {{justfile_directory()}}/src && ruff check .

ruff_tests:
    cd {{justfile_directory()}}/tests && ruff check .

sort:
    cd {{justfile_directory()}}/src && isort .

sort_tests:
    cd {{justfile_directory()}}/tests && isort .

black:
    cd {{justfile_directory()}}/src && black . --diff --color

mypy:
    cd {{justfile_directory()}}/src && mypy .

test:
    cd {{justfile_directory()}}/tests && pytest -rP
