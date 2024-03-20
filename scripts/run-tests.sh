#!/bin/bash

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

set -o errexit
set -o verbose

targets=(service cdk_constants.py app.py)

# Find common security issues (https://bandit.readthedocs.io)
bandit --ini .bandit --recursive "${targets[@]}"

# Python code formatter (https://black.readthedocs.io)
black --line-length 110 --check --diff "${targets[@]}"

# Style guide enforcement (https://flake8.pycqa.org)
flake8 --config .flake8 "${targets[@]}"

# Sort imports (https://pycqa.github.io/isort)
isort --settings-path .isort.cfg --check --diff "${targets[@]}"

# Static type checker (https://mypy.readthedocs.io)
mypy --config-file .mypy.ini "${targets[@]}"

# Check for errors, enforce a coding standard, look for code smells (http://pylint.pycqa.org)
pylint --rcfile .pylintrc "${targets[@]}"

# Check dependencies for security issues (https://pyup.io/safety)
safety check -r service/runtime/requirements.txt -r requirements.txt -r requirements-dev.txt

# Report code complexity (https://radon.readthedocs.io)
radon mi "${targets[@]}"

# Exit with non-zero status if code complexity exceeds thresholds (https://xenon.readthedocs.io)
xenon --exclude "service/runtime/python_packages/*" --max-absolute A --max-modules A --max-average A "${targets[@]}"
