# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from typing import Any

import aws_cdk as cdk
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_logs as logs
from aws_cdk import aws_stepfunctions as stepfunctions
from aws_cdk import aws_stepfunctions_tasks as stepfunctions_tasks
from constructs import Construct

from service.metric_extraction import LAMBDA_FUNCTION_CODE_ASSET
from service.metric_extraction import MetricsExtraction

DESCRIBE_RESOURCE_SCAN_STATUS_JSON_PATH = "$.Payload.Status"
TIME_TO_WAIT_BETWEEN_POLLING_MINUTES = 10

START_SCAN_LAMBDA_FUNCTION_HANDLER = "start_scan.lambda_handler"
DESCRIBE_SCAN_LAMBDA_FUNCTION_HANDLER = "describe_scan.lambda_handler"


# pylint: disable=too-few-public-methods
class ResourceScanStatus:
    IN_PROGRESS = "IN_PROGRESS"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    COMPLETE = "COMPLETE"


# pylint: disable=too-few-public-methods
class ScanConditions:
    IN_PROGRESS = stepfunctions.Condition.string_equals(
        DESCRIBE_RESOURCE_SCAN_STATUS_JSON_PATH, ResourceScanStatus.IN_PROGRESS
    )
    COMPLETE = stepfunctions.Condition.string_equals(
        DESCRIBE_RESOURCE_SCAN_STATUS_JSON_PATH, ResourceScanStatus.COMPLETE
    )
    FAILED = stepfunctions.Condition.or_(
        stepfunctions.Condition.string_equals(
            DESCRIBE_RESOURCE_SCAN_STATUS_JSON_PATH, ResourceScanStatus.FAILED
        ),
        stepfunctions.Condition.string_equals(
            DESCRIBE_RESOURCE_SCAN_STATUS_JSON_PATH, ResourceScanStatus.EXPIRED
        ),
    )


class Orchestration(Construct):
    def __init__(self, scope: Construct, _id: str, metric_extraction: MetricsExtraction, **kwargs: Any):
        super().__init__(scope, _id, **kwargs)

        self.state_machine = self._create_state_machine(metric_extraction)

    def _create_state_machine(self, metric_extraction: MetricsExtraction) -> stepfunctions.StateMachine:
        state_machine_definition = self._create_state_machine_definition(metric_extraction)

        log_group = logs.LogGroup(
            self,
            "LogGroup",
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        state_machine = stepfunctions.StateMachine(
            self,
            id="StateMachine",
            definition_body=stepfunctions.DefinitionBody.from_chainable(state_machine_definition),
            logs=stepfunctions.LogOptions(level=stepfunctions.LogLevel.ALL, destination=log_group),
            tracing_enabled=True,
        )

        return state_machine

    def _create_state_machine_definition(self, metric_extraction: MetricsExtraction) -> stepfunctions.Chain:
        states = States(self, "States", metric_extraction)

        # Tell black formatter not to format these expressions using "fmt: off/on"
        # fmt: off

        state_machine_definition = (
            states.start_resource_scan
            .next(states.wait)
            .next(states.describe_resource_scan)
            .next(
                states.is_scan_complete_choice
                .when(ScanConditions.FAILED, states.scan_failed)
                .when(ScanConditions.IN_PROGRESS, states.wait)
                .when(ScanConditions.COMPLETE, (
                    states.extract_managed_resources_metrics
                    .next(states.put_metric_data)
                    .next(states.success)
                ))
                .otherwise(states.scan_failed)
            )
        )
        # fmt: on

        return state_machine_definition


class States(Construct):
    # pylint: disable=too-many-instance-attributes
    def __init__(self, scope: Construct, _id: str, metric_extraction: MetricsExtraction, **kwargs: Any):
        super().__init__(scope, _id, **kwargs)

        # Temporary Lambda function, delete when StepFunctions introduce StartResourceScan action
        start_scan_lambda_function = self._create_start_resource_scan_lambda_function(
            metric_extraction.python_requirements_layer
        )

        # Temporary Lambda function, delete when StepFunctions introduce DescribeResourceScan action
        describe_scan_lambda_function = self._create_describe_resource_scan_lambda_function(
            metric_extraction.python_requirements_layer
        )

        self.start_resource_scan = stepfunctions_tasks.LambdaInvoke(
            self,
            "StartResourceScan",
            lambda_function=start_scan_lambda_function,
        )

        self.wait = stepfunctions.Wait(
            self,
            f"Wait{int(TIME_TO_WAIT_BETWEEN_POLLING_MINUTES)}Minutes",
            time=stepfunctions.WaitTime.duration(cdk.Duration.minutes(TIME_TO_WAIT_BETWEEN_POLLING_MINUTES)),
        )

        self.describe_resource_scan = stepfunctions_tasks.LambdaInvoke(
            self,
            "DescribeResourceScan",
            lambda_function=describe_scan_lambda_function,
            payload=stepfunctions.TaskInput.from_json_path_at("$.Payload"),
        )

        self.is_scan_complete_choice = stepfunctions.Choice(self, "IsScanCompleteChoice")

        self.scan_failed = stepfunctions.Fail(self, "ScanFailed")

        self.extract_managed_resources_metrics = stepfunctions_tasks.LambdaInvoke(
            self,
            "ExtractManagedResourcesMetrics",
            lambda_function=metric_extraction.extract_metrics_lambda_function,
            payload=stepfunctions.TaskInput.from_json_path_at("$.Payload"),
        )

        self.put_metric_data = stepfunctions_tasks.CallAwsService(
            self,
            "PutMetricData",
            service="cloudwatch",
            action="putMetricData",
            iam_resources=["*"],
            parameters={
                "MetricData": stepfunctions.JsonPath.string_at("$.Payload.MetricData"),
                "Namespace": stepfunctions.JsonPath.string_at("$.Payload.Namespace"),
            },
        )

        self.success = stepfunctions.Succeed(self, "Success")

    def _create_start_resource_scan_lambda_function(
        self, python_requirements_layer: _lambda.LayerVersion
    ) -> _lambda.Function:
        start_scan_lambda_function = _lambda.Function(
            self,
            "StartScanLambdaFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            code=LAMBDA_FUNCTION_CODE_ASSET,
            handler=START_SCAN_LAMBDA_FUNCTION_HANDLER,
            timeout=cdk.Duration.minutes(10),
            layers=[python_requirements_layer],
        )

        lambda_role = start_scan_lambda_function.role
        if lambda_role is None:
            raise ValueError("Lambda role is None")

        lambda_role.attach_inline_policy(
            iam.Policy(
                self,
                "AllowStartScan",
                document=iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["*"],  # This is required for the resource scan to find resources
                            effect=iam.Effect.ALLOW,
                            resources=["*"],
                        )
                    ]
                ),
            )
        )

        return start_scan_lambda_function

    def _create_describe_resource_scan_lambda_function(
        self, python_requirements_layer: _lambda.LayerVersion
    ) -> _lambda.Function:
        describe_scan_lambda_function = _lambda.Function(
            self,
            "DescribeScanLambdaFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            code=LAMBDA_FUNCTION_CODE_ASSET,
            handler=DESCRIBE_SCAN_LAMBDA_FUNCTION_HANDLER,
            timeout=cdk.Duration.minutes(10),
            layers=[python_requirements_layer],
        )

        lambda_role = describe_scan_lambda_function.role
        if lambda_role is None:
            raise ValueError("Lambda role is None")

        lambda_role.attach_inline_policy(
            iam.Policy(
                self,
                "AllowDescribeScan",
                document=iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["CloudFormation:DescribeResourceScan"],
                            effect=iam.Effect.ALLOW,
                            resources=["*"],
                        )
                    ]
                ),
            )
        )

        return describe_scan_lambda_function
