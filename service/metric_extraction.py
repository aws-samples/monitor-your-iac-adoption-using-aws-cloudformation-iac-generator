# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import os
from typing import Any

import aws_cdk as cdk
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda
from constructs import Construct

import cdk_constants as constants
from service.runtime.constants import EnvVarsNames

RUNTIME_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "runtime")
LAMBDA_FUNCTION_CODE_ASSET = _lambda.Code.from_asset(RUNTIME_PATH)

PYTHON_REQUIREMENTS_PATH = os.path.join(RUNTIME_PATH, "python_packages")
PYTHON_REQUIREMENTS_LAYER_CODE_ASSET = _lambda.Code.from_asset(PYTHON_REQUIREMENTS_PATH)

EXTRACT_METRICS_LAMBDA_FUNCTION_HANDLER = "extract_metrics.lambda_handler"


class MetricsExtraction(Construct):
    def __init__(self, scope: Construct, _id: str, **kwargs: Any):
        super().__init__(scope, _id, **kwargs)

        self.python_requirements_layer = _lambda.LayerVersion(
            self,
            "PythonRequirementsLayer",
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_12],
            code=PYTHON_REQUIREMENTS_LAYER_CODE_ASSET,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        self.extract_metrics_lambda_function = _lambda.Function(
            self,
            "ExtractMetricsLambdaFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            code=LAMBDA_FUNCTION_CODE_ASSET,
            handler=EXTRACT_METRICS_LAMBDA_FUNCTION_HANDLER,
            timeout=cdk.Duration.minutes(10),
            layers=[self.python_requirements_layer],
            environment={
                EnvVarsNames.RESOURCE_TYPE_EXCLUDE_LIST_JSON: json.dumps(
                    constants.RESOURCE_TYPE_EXCLUDE_LIST
                ),
                EnvVarsNames.RESOURCE_TYPE_FOCUS_LIST_JSON: json.dumps(constants.RESOURCE_TYPE_FOCUS_LIST),
                EnvVarsNames.CLOUDWATCH_METRICS_NAMESPACE: constants.CLOUDWATCH_METRICS_NAMESPACE,
                EnvVarsNames.ACCOUNT_ID: cdk.Aws.ACCOUNT_ID,
                EnvVarsNames.REGION: cdk.Aws.REGION,
            },
        )
        self.allow_role_to_list_resource_scan_resources(self.extract_metrics_lambda_function.role)

    def allow_role_to_list_resource_scan_resources(self, lambda_role: iam.IRole | None) -> None:
        if lambda_role is None:
            raise ValueError("Lambda role is None")

        lambda_role.attach_inline_policy(
            iam.Policy(
                self,
                "AllowListScanResources",
                document=iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["CloudFormation:ListResourceScanResources"],
                            effect=iam.Effect.ALLOW,
                            resources=["*"],
                        )
                    ]
                ),
            )
        )
