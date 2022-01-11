testsuite.install:
	pip install pytest pytest-mock responses pytest-cov
	python setup.py develop
	
testsuite.run:
	python -m pytest --cov=./ --cov-report=xml:coverage.xml .