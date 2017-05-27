.PHONY: clean-pyc clean-build docs clean
define BROWSER_PYSCRIPT
import os, webbrowser, sys
try:
	from urllib import pathname2url
except:
	from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT
BROWSER := python -c "$$BROWSER_PYSCRIPT"
VERSION = `python setup.py --version`

help:
	@echo "clean - remove all build, test, coverage and Python artifacts"
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "clean-test - remove test and coverage artifacts"
	@echo "lint - check style with flake8"
	@echo "test - run tests quickly with the default Python"
	@echo "test-all - run tests on every Python version with tox"
	@echo "coverage - check code coverage quickly with the default Python"
	@echo "docs - generate Sphinx HTML documentation, including API docs"
	@echo "release - package and upload a release"
	@echo "dist - package"
	@echo "install - install the package to the active Python's site-packages"
	@echo "VERSION: $(VERSION)"

clean: clean-build clean-pyc clean-test

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test:
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/

lint:
	flake8 webquills tests

test:
	py.test

test-all:
	tox

coverage:
	coverage run --source webquills setup.py test
	coverage report -m
	coverage html
	$(BROWSER) htmlcov/index.html

docs:
	rm -f docs/webquills.rst
	rm -f docs/modules.rst
	sphinx-apidoc -o docs/ webquills
	$(MAKE) -C docs clean
	$(MAKE) -C docs html
	$(BROWSER) docs/_build/html/index.html

release: clean dist
	# TODO twine python setup.py bdist_wheel upload

dist: dist/lambda-archivechanged.zip
	python setup.py sdist
	python setup.py bdist_wheel
	ls -l dist

install: clean
	python setup.py develop

dist/lambda-archivechanged.zip:
	mkdir -p build/archivechanged
	mkdir -p dist
	pip install -t build/archivechanged/ .
	rm -rf build/archivechanged/*.dist-info build/archivechanged/*.egg-info
	# boto3 is provided by Lambda, so do not package it or its deps
	rm -rf build/archivechanged/boto3 build/archivechanged/botocore
	rm -rf build/archivechanged/jmespath build/archivechanged/docutils
	rm -rf build/archivechanged/s3transfer build/archivechanged/dateutil
	# shaves ~1MB, but how much time cost to recompile?
	find ./build/archivechanged -name '*.pyc' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +
	cd build/archivechanged/ && zip -r ../../dist/lambda-archivechanged.zip *

public: dist
	aws s3 cp --acl public-read --recursive dist s3://dist.webquills.net/$(VERSION)/

awsinstall: public
	quill setup dist.webquills.net
	quill upgrade dist.webquills.net
