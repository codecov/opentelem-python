from codecs import open
from os import path

from setuptools import find_packages, setup

here = path.abspath(path.dirname(__file__))

with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="codecovopentelem",
    version="0.0.1",
    description="Shared Codecov",
    long_description=long_description,
    url="https://github.com/codecov/opentelem-python",
    author="Codecov",
    author_email="support@codecov.io",
    packages=find_packages(exclude=["contrib", "docs", "tests*"]),
    install_requires=["coverage>=5.5", "requests", "opentelemetry-sdk"],
)
