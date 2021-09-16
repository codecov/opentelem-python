testsuite.install:
	pip install pytest pytest-mock responses
	python setup.py develop
	
testsuite.run:
	python -m pytest .