set dotenv-load := true

# @ means: surpress printing the executed command

default:
	@just --list


########################################################################################
#### MARK: Project


install:
	# Set correct user
	git config user.name "Marcel Kröker"
	git config user.email "kroeker.marcel@gmail.com"
	git config pull.rebase true
	# Install dependencies
	uv sync


alias o := outdated
outdated:
	uv tree --outdated --depth 1


alias up := upgrade
upgrade:
	# Update dependencies
	uv lock --upgrade
	uv sync


publish:
	uv build
	uv publish
	rm -rf dist


########################################################################################
#### MARK: Code Quality


alias r := ruff
ruff:
	uv run ruff format .
	uv run ruff check . --fix


alias tc := typecheck
typecheck:
	uv run pyrefly check . --no-progress-bar


alias t := test
test:
	uv run coverage run -m pytest


alias c := check
check:
	@just ruff
	@just typecheck
	@just test
