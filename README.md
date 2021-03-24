# Ysdtools - A collection of useful tools

[![Release](https://img.shields.io/pypi/v/ysdtools)](https://pypi.org/project/ysdtools/)  
[![build](https://github.com/gavinying/ysdtools-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gavinying/ysdtools-python/actions)
[![codecov](https://codecov.io/gh/gavinying/ysdtools-python/branch/master/graph/badge.svg?token=TDBFIHJDZG)](https://codecov.io/gh/gavinying/ysdtools-python)
[![Read the Docs](https://readthedocs.org/projects/ysdtools-python/badge/?version=latest)](https://ysdtools-python.readthedocs.io/en/latest)

**This project is not designed for production, only for personal use!**

## Table of Contents

- [Project Setup](#project-setup)
    - [Initialize Project](#initialize-project)
    - [Build and Test](#build-and-test)
    - [Document Project](#document-project)
    - [Setup CI Pipeline](#setup-ci-pipeline)
    - [CodeCov](#codecov)
    - [Read The Docs](#read-the-docs)
    - [Deploy to PyPI](#deploy-to-pypi)
- [Install](#install)
- [Usage](#usage)
- [Maintainers](#maintainers)
- [License](#license)

## Project Setup
This project uses [poetry](https://python-poetry.org/) to setup project. Project setup process is based on https://testdriven.io/blog/python-project-workflow

### Initialize Project

First, let's create a python project with poetry, 

```bash
$ poetry new --name ysdtools ysdtools-python

Package name [ysdtools]:
Version [0.1.0]:
Description []:
Author [Your name <your@email.com>, n to skip]:
License []:
Compatible Python versions [>3.7,<4.0]:

Would you like to define your main dependencies interactively? (yes/no) [yes] no
Would you like to define your development dependencies interactively? (yes/no) [yes] no
Do you confirm generation? (yes/no) [yes]
```

Now you will have a folder `ysdtools-python`, and modify the config file `pyproject.toml` inside according to your project need. 
Your project name must be unique since you'll be uploading it to PyPI. So, to avoid name collisions add a unique string to the package name in pyproject.toml.

> For more details on Poetry, check out `https://python-poetry.org/docs/basic-usage`

Create a new repository on Github named `ysdtools-python`, and initialize with the newly created project.

Inside the project folder, add a few python dependencies for testing and code quality check, 
```bash
$ poetry add --dev pytest pytest-cov black isort flake8 bandit safety
```
Add the new poetry.lock file as well as the updated pyproject.toml file to git,
```bash
$ git add poetry.lock pyproject.toml
```

### Build and Test

Now the project layout looks like this,
```bash
ysdtools-python
├── poetry.lock
├── pyproject.toml
├── tests
│   ├── __init__.py
│   └── test_ysdtools.py
└── ysdtools
    ├── __init__.py
    └── ysdlog.py
```
Run the script,
```bash
$ poetry run python ysdtools/ysdlog.py
```
Run the test,
```bash
$ poetry run python -m pytest tests
```

### Document Project

We use Google python style for docstrings, 
> If you are not familiar with docstrings or documentation, please refer to [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)

Assuming you have [Sphinx](https://www.sphinx-doc.org/en/master/usage/quickstart.html) installed, run the following to scaffold out the files and folders for Sphinx in the project root:
```bash
$ sphinx-quickstart docs

> Separate source and build directories (y/n) [n]: n
> Project name: Ysdtools
> Author name(s): Your Name
> Project release []: 0.1.0
> Project language [en]: en
```
Next, let's update the `docs/conf.py`, set the correct source path,
```bash
import os
import sys
sys.path.insert(0, os.path.abspath('../'))
```
Add autodoc extention, 
```bash
extensions = [
    'sphinx.ext.autodoc',
]
```

Create a new page `docs/ysdlog.rst` with the following content,
```bash
ysdtools.ysdlog
====================================
.. automodule:: ysdtools.ysdlog
    :members:
```

Update `docs/index.rst` like so, 
```bash
Welcome to ysdtools's documentation!
====================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   ysdlog
```

### Setup CI Pipeline
Let's setup CI pipeline with Github Actions,
add the following files and folders to the project root:
```bash
.github
└── workflows
    └── ci.yml
```
Inside ci.yml, 
```bash
name: Push
on: [push, pull_request]

jobs:
  test:
    strategy:
      fail-fast: false
      matrix:
        python-version: [3.8]
        poetry-version: [1.1.5]
        os: [ubuntu-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: ${{ matrix.python-version }}
      - name: Run image
        uses: abatilo/actions-poetry@v2.0.0
        with:
          poetry-version: ${{ matrix.poetry-version }}
      - name: Install dependencies
        run: poetry install
      - name: Run tests
        run: poetry run pytest --cov=./ --cov-report=xml
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v1
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
  code-quality:
    strategy:
      fail-fast: false
      matrix:
        python-version: [3.8]
        poetry-version: [1.1.5]
        os: [ubuntu-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: ${{ matrix.python-version }}
      - name: Run image
        uses: abatilo/actions-poetry@v2.0.0
        with:
          poetry-version: ${{ matrix.poetry-version }}
      - name: Install dependencies
        run: poetry install
      - name: Run black
        run: poetry run black . --check
      - name: Run isort
        run: poetry run isort . --check-only
      - name: Run flake8
        run: poetry run flake8 .
      - name: Run bandit
        run: poetry run bandit -r . -x ./tests,./docs
      - name: Run saftey
        run: poetry run safety check
```
There are two jobs defined: test and code-quality. As the names' suggest, the tests run in the test job while our code quality checks run in the code-quality job.

> Now on every push to the GitHub repository, tests and code quality jobs will run.

Before we commit the changes, it is better to pass all local test first,
```bash
$ poetry run black . --check
$ poetry run isort . --check-only
$ poetry run flake8 .
$ poetry run bandit -r . -x ./tests,./docs
$ poetry run safety check
```

Finally, we can commit and push the code,
```bash
$ git commit -m 'CI pipeline ready'
$ git push -u origin master
```
You should see your workflow running on the "Actions" tab on your GitHub repository. Make sure it passes before moving on.

### CodeCov
Next, we'll configure CodeCov to track code coverage. Navigate to http://codecov.io/, and log in with your GitHub account and find your repository.

Run the GitHub Actions workflow again. Once done, you should be able to see the coverage report on CodeCov.

If the github repository is private, you can generate an API token from CodeCov, and put it as an environment variable `CODECOV_TOKEN` in Github `project->settings->secrets`.

### Read The Docs
We'll use Read the Docs to host our documentation. Navigate to https://readthedocs.org, and log in using your GitHub account.

> Read The Docs cloud only support public repository for free.

### Deploy to PyPI
Finally, in order to make the project "pip-installable", we'll publish it to PyPI.

Add the following code in `pyproject.toml`,
```bash
packages = [
    { include = "ysdtools" },
]
```

Add a new file called `cd.yml` to ".github/workflows":
```bash
name: Release
on:
  release:
    types:
      - created

jobs:
  publish:
    strategy:
      fail-fast: false
      matrix:
        python-version: [3.8]
        poetry-version: [1.1.5]
        os: [ubuntu-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: ${{ matrix.python-version }}
      - name: Run image
        uses: abatilo/actions-poetry@v2.0.0
        with:
          poetry-version: ${{ matrix.poetry-version }}
      - name: Publish
        env:
          PYPI_TOKEN: ${{ secrets.PYPI_TOKEN }}
        run: |
          poetry config pypi-token.pypi $PYPI_TOKEN
          poetry publish --build
```

Next, we'll need to create a PyPI token. Create an account on PyPI if you don't already have one. Then, once signed in, click "Account settings" and add a new API token. Copy the token. You'll now need to add it to your GitHub repository's secrets. Within the repo, click the "Settings" tab, and then click "Secrets". Use PYPI_TOKEN for the secret name and the token value as the secret value.


## Install
Install via pip,
```bash
$ pip install ysdtools
```

## Usage
A basic usage is as,
```bash
from ysdtools import ysdlog
ysdlog.info("Start logging...")
```

## Maintainers
Ying Shaodong <helloysd@gmail.com>

## License
[MIT](LICENSE) © Ying Shaodong
