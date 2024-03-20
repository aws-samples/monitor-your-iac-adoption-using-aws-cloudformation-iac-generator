# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# This file is named cdk_constants.py to avoid conflict with the runtime constants file.

import os

import aws_cdk as cdk

ENVIRONMENT = cdk.Environment(
    account=os.environ["CDK_DEFAULT_ACCOUNT"],
    region=os.environ["CDK_DEFAULT_REGION"],
)


RESOURCE_TYPE_FOCUS_LIST = [
    "AWS::EC2::Instance",
    "AWS::Lambda::Function",
    "AWS::S3::Bucket",
    "AWS::RDS::DBCluster",
]

RESOURCE_TYPE_EXCLUDE_LIST = [
    "AWS::Logs::LogStream",
    "AWS::Logs::LogGroup",
    "AWS::IAM::ManagedPolicy",
]

RESOURCE_TYPE_DELIMETER = "::"

CLOUDWATCH_METRICS_NAMESPACE = "IacAdoption"
