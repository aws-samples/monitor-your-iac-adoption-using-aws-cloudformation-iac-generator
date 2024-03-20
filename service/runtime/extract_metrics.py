# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import os
from collections import defaultdict
from typing import Any, DefaultDict

import boto3
from aws_lambda_powertools.utilities.typing import LambdaContext
from constants import RESOURCE_SCAN_ID_EVENT_KEY
from constants import EnvVarsNames
from metrics import ManagedResourceMetrics
from metrics import ScannedResourceKeys
from mypy_boto3_cloudformation.type_defs import ScannedResourceTypeDef

CLOUDFORMATION_CLIENT = boto3.client("cloudformation")

RESOURCE_TYPE_FOCUS_LIST_JSON = os.getenv(EnvVarsNames.RESOURCE_TYPE_FOCUS_LIST_JSON, "[]")
RESOURCE_TYPE_FOCUS_LIST = json.loads(RESOURCE_TYPE_FOCUS_LIST_JSON)

RESOURCE_TYPE_EXCLUDE_LIST_JSON = os.getenv(EnvVarsNames.RESOURCE_TYPE_EXCLUDE_LIST_JSON, "[]")
RESOURCE_TYPE_EXCLUDE_LIST = json.loads(RESOURCE_TYPE_EXCLUDE_LIST_JSON)

CLOUDWATCH_METRICS_NAMESPACE = os.getenv(EnvVarsNames.CLOUDWATCH_METRICS_NAMESPACE)
ACCOUNT_ID = os.getenv(EnvVarsNames.ACCOUNT_ID)
REGION = os.getenv(EnvVarsNames.REGION)


# pylint: disable=unused-argument
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    resource_scan_id = event.get(RESOURCE_SCAN_ID_EVENT_KEY)

    if not resource_scan_id:
        raise ValueError("ResourceScanId is required")

    metrics_to_collect = construct_metric_to_collect_list()
    metric_values = extract_metrics_from_resource_scan(resource_scan_id, metrics_to_collect)
    metrics = generate_cloudwatch_metrics(metric_values)

    return metrics


def construct_metric_to_collect_list() -> list[ManagedResourceMetrics]:
    metrics_to_collect = [ManagedResourceMetrics("Resources", all_resources_predicate)]

    focus_managed_resource_metrics = map(ManagedResourceMetrics.from_resource_type, RESOURCE_TYPE_FOCUS_LIST)
    metrics_to_collect.extend(focus_managed_resource_metrics)

    return metrics_to_collect


# pylint: disable=unused-argument
def all_resources_predicate(scanned_resource: ScannedResourceTypeDef) -> bool:
    return True


def extract_metrics_from_resource_scan(
    resource_scan_id: str,
    metrics_to_collect: list[ManagedResourceMetrics],
) -> DefaultDict[str, int]:
    metric_values: DefaultDict[str, int] = defaultdict(int)
    next_token = ""
    while True:
        # The first call to `list_resource_scan_resources` must not include `NextToken` argument
        # The second call onward must include `NextToken` argument
        #
        # The response from `list_resource_scan_resources` contains a `NextToken` which
        # should be used to retrieve the next page of results.
        response = CLOUDFORMATION_CLIENT.list_resource_scan_resources(
            ResourceScanId=resource_scan_id,
            **({"NextToken": next_token} if next_token else {}),  # type: ignore
        )
        next_token = response.get("NextToken", "")

        current_page_metric_values = extract_metric_values_from_scanned_resources(
            response["Resources"], metrics_to_collect
        )

        for metric_name, value in current_page_metric_values.items():
            metric_values[metric_name] += value

        if is_last_page(next_token):
            break

    return metric_values


def extract_metric_values_from_scanned_resources(
    scanned_resources: list[ScannedResourceTypeDef],
    metrics_to_collect: list[ManagedResourceMetrics],
) -> DefaultDict[str, int]:
    metric_values: DefaultDict[str, int] = defaultdict(int)

    for scanned_resource in scanned_resources:
        if scanned_resource.get(ScannedResourceKeys.ResourceType, "") in RESOURCE_TYPE_EXCLUDE_LIST:
            continue

        for managed_resource_metrics in metrics_to_collect:
            for metric in managed_resource_metrics:
                metric_values[metric.name] += metric.filter(scanned_resource)

    return metric_values


def is_last_page(next_token: str) -> bool:
    return not next_token


def generate_cloudwatch_metrics(metric_values: DefaultDict[str, int]) -> dict[str, Any]:
    if len(metric_values) == 0:
        raise ValueError("No metrics to send")

    dimensions = generate_cloudwatch_dimensions()

    metric_data = [
        generate_cloudwatch_metric_datum(metric_name, value, unit="Count", dimensions=dimensions)
        for metric_name, value in metric_values.items()
    ]

    return {
        "MetricData": metric_data,
        "Namespace": CLOUDWATCH_METRICS_NAMESPACE,
    }


def generate_cloudwatch_metric_datum(
    metric_name: str,
    value: int,
    unit: str,
    dimensions: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "MetricName": metric_name,
        "Value": value,
        "Unit": unit,
        "Dimensions": dimensions,
    }


def generate_cloudwatch_dimensions() -> list[dict[str, str]]:
    dimensions = []
    if ACCOUNT_ID:
        dimensions.append({"Name": "AccountID", "Value": ACCOUNT_ID})
    if REGION:
        dimensions.append({"Name": "Region", "Value": REGION})

    return dimensions
