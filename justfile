set dotenv-load := true

# @ means: surpress printing the executed command

default:
    @just --list


test:
    uv run coverage run -m pytest


ruff:
    uv run ruff format .
    uv run ruff check . --fix


typecheck:
    uv run pyrefly check . --no-progress-bar



o:
    uv tree --outdated --depth 1


c:
    @just ruff
    @just typecheck
    @just test


publish:
    uv build
    uv publish
    rm -rf dist
    rm -rf statica.egg-info
