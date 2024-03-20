#!/bin/bash

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

set -o errexit
set -o verbose

# Install AWS CDK Toolkit locally
npm install

# Install project dependencies
python3 -m pip install -r service/runtime/requirements.txt -r requirements.txt -r requirements-dev.txt

# Install runtime dependencies for lambda layer creation
python3 -m pip install -r service/runtime/requirements.txt --target service/runtime/python_packages/python/