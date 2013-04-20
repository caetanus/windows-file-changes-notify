#
#
# Makefile for nosetests
#
#
#

all: unit integration

test:

	@echo running all tests

	@REDNOSE=1 nosetests tests/integration/*.py tests/unit/*.py

unit:

	@echo running unit tests
	@REDNOSE=1 nosetests tests/unit/*.py

integration:
	@echo running integration tests
	@REDNOSE=1 nosetests tests/integration/*.py

coverage:
	@echo running all tests with coverage
	@nosetests --all-modules --with-coverage --cover-html --cover-html-dir=code_coverage/ --cover-package=tcf_engine --exclude='.*twisted_adapter.*'


clean:
	@echo removing pyc files
	@find . -iname '*.pyc' -exec rm -f \{\} \;
	@echo removing vim backups
	@find . -iname '.*.sw?' -exec rm -f \{\} \;
	@echo removing build sources
	@rm -rf src/
	@rm -rf tcf_engine/src/
	@rm -rf  *.egg-info
	@rm -rf  build/
	@rm -rf  dist/
	@rm -rf code_coverage

