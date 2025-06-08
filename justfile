set dotenv-load := true

# @ means: surpress printing the executed command

default:
    @just --list


test:
    uv run coverage run -m pytest


ruff:
    uv run ruff check .


mypy:
    uv run mypy statica


publish:
    uv build
    uv publish
    rm -rf dist
    rm -rf statica.egg-info

