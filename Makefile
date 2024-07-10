.PHONY: install
install: ## Install the poetry environment and install the pre-commit hooks
	@echo "🚀 Creating virtual environment using pyenv and poetry"
	@poetry self add poetry-plugin-export
	@poetry install
	@poetry run pre-commit install --allow-missing-config
	@poetry shell

.PHONY: check
check: ## Run code quality tools.
	@echo "🚀 Checking Poetry lock file consistency with 'pyproject.toml': Running poetry check --lock"
	@poetry check --lock
	@echo "🚀 Exporting 'requirements.txt' file: Running poetry export"
	@poetry export -f requirements.txt -o requirements.txt --without-hashes
	@echo "🚀 Linting code: Running pre-commit"
	@poetry run pre-commit run -a
	@echo "🚀 Checking for obsolete dependencies: Running deptry"
	@poetry run deptry .

.PHONY: test
test: ## Test the code with pytest
	@echo "🚀 Testing code: Running pytest"
	@poetry run pytest --doctest-modules

.PHONY: build
build: clean-build ## Build wheel file using poetry
	@echo "🚀 Creating wheel file"
	@poetry build

.PHONY: clean-build
clean-build: ## clean build artifacts
	@rm -rf dist

.PHONY: publish
publish: ## Publish a release to PyPI.
	@echo "🚀 Publishing: Dry run."
	@poetry config pypi-token.pypi ${PYPI_TOKEN}
	@if poetry publish --dry-run; then \
		echo "Dry run successful. Proceeding with publishing..."; \
		poetry publish; \
	else \
		echo "Dry run failed. Version might already exist or other error occurred."; \
	fi

.PHONY: build-and-publish
build-and-publish: build publish ## Build and publish.

.PHONY: docker
docker: ## Build docker using docker buildx
	@echo "🚀 Login to docker registry"
	@echo "${DOCKER_PASSWORD}" | docker login -u "${DOCKER_USERNAME}" --password-stdin "${DOCKER_REGISTRY}"
	@echo "🚀 Set up QEMU"
	@docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
	@echo "🚀 Create the builder if not exists"
	@docker buildx inspect mybuilder &>/dev/null || docker buildx create --name mybuilder ; docker buildx use mybuilder
	@echo "🚀 Creating docker image file"
	@docker buildx build --platform linux/amd64,linux/arm64 -t ${DOCKER_REGISTRY}/${DOCKER_USERNAME}/modsim:latest --push .

.PHONY: docs
docs: ## Build docs into html files
	@poetry run pandoc --from=markdown --to=rst CHANGELOG.md -o docs/changelog.rst
	@poetry run sphinx-build docs/ docs/_build/html

.PHONY: docs-serve
docs-serve: ## Build and serve the docs for local dev
	@poetry run pandoc --from=markdown --to=rst CHANGELOG.md -o docs/changelog.rst
	@poetry run sphinx-autobuild docs/ docs/_build/html

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
