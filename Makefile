.PHONY: accept build check clean cleandocs coverage docs help install opendocs sdist
.PHONY: test wheel

help:
	@echo "Please use \`make <target>' where <target> is one or more of"
	@echo "  accept       run acceptance tests using behave"
	@echo "  build        generate both sdist and wheel"
	@echo "  check        verify the built distributions render on PyPI"
	@echo "  clean        delete intermediate work product and start fresh"
	@echo "  cleandocs    delete the built documentation site"
	@echo "  coverage     run pytest with coverage"
	@echo "  docs         build the documentation site into site/"
	@echo "  install      create or update the development environment"
	@echo "  opendocs     serve the documentation with live reload"
	@echo "  sdist        generate a source distribution into dist/"
	@echo "  test         run unit tests using pytest"
	@echo "  wheel        generate a binary distribution into dist/"
	@echo ""
	@echo "Releasing is a tag push: .github/workflows/python-publish.yml builds and"
	@echo "publishes to PyPI over trusted publishing. There is no upload target."

accept:
	uv run behave --stop

build:
	uv build

check: build
	uv run twine check dist/*

clean:
	find . -type f -name '*.py[co]' -delete
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf build dist site *.egg-info src/*.egg-info .coverage

cleandocs:
	rm -rf site

coverage:
	uv run pytest --cov-report term-missing --cov=docx tests/

docs:
	uv run mkdocs build

install:
	uv sync

opendocs:
	uv run mkdocs serve

sdist:
	uv build --sdist

test:
	uv run pytest -x

wheel:
	uv build --wheel
