testsuite.install:
	pip install pytest pytest-mock responses pytest-cov
	pip install --upgrade build
	python setup.py develop
	
testsuite.run:
	python -m pytest --cov=./ --cov-report=xml:coverage.xml .

package.build:
	python -m build