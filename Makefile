#
#
# Makefile for nosetests
#
#
#

all: test

test:

	@echo running all tests

	@REDNOSE=1 nosetests 


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


install:
	python setup.py install
