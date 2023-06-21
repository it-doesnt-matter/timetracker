set windows-shell := ["pwsh.exe", "-NoLogo", "-Command"]

run FILE="main":
    cd {{justfile_directory()}}/src && python {{FILE}}.py

ruff:
    cd {{justfile_directory()}}/src && ruff check .

sort:
    cd {{justfile_directory()}}/src && isort .

black:
    cd {{justfile_directory()}}/src && black . --diff --color

mypy:
    cd {{justfile_directory()}}/src && mypy .

test:
    cd {{justfile_directory()}}/tests && pytest
