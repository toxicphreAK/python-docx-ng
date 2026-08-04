BEHAVE = behave
MAKE   = make
PYTHON = python
TWINE  = $(PYTHON) -m twine

.PHONY: accept build clean cleandocs coverage docs install opendocs sdist test
.PHONY: test-upload wheel

help:
	@echo "Please use \`make <target>' where <target> is one or more of"
	@echo "  accept       run acceptance tests using behave"
	@echo "  build        generate both sdist and wheel suitable for upload to PyPI"
	@echo "  clean        delete intermediate work product and start fresh"
	@echo "  cleandocs    delete the built documentation site"
	@echo "  coverage     run pytest with coverage"
	@echo "  docs         build the documentation site into site/"
	@echo "  opendocs     serve the documentation with live reload"
	@echo "  register     update metadata (README.rst) on PyPI"
	@echo "  sdist        generate a source distribution into dist/"
	@echo "  test         run unit tests using pytest"
	@echo "  test-upload  upload distribution to TestPyPI"
	@echo "  upload       upload distribution tarball to PyPI"
	@echo "  wheel        generate a binary distribution into dist/"

accept:
	uv run $(BEHAVE) --stop

build:
	uv build

clean:
	# find . -type f -name \*.pyc -exec rm {} \;
	fd -e pyc -I -x rm
	rm -rf dist *.egg-info .coverage .DS_Store

cleandocs:
	rm -rf site

coverage:
	uv run pytest --cov-report term-missing --cov=docx tests/

docs:
	uv run mkdocs build

install:
	pip install -Ue .

opendocs:
	uv run mkdocs serve

sdist:
	uv build --sdist

test:
	uv run pytest -x

test-upload: sdist wheel
	uv run $(TWINE) upload --repository testpypi dist/*

upload: clean sdist wheel
	uv run $(TWINE) upload dist/*

wheel:
	uv build --wheel
