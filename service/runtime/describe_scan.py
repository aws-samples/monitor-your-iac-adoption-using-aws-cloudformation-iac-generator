# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
from typing import Any

import boto3
from aws_lambda_powertools.utilities.typing import LambdaContext
from constants import RESOURCE_SCAN_ID_EVENT_KEY

CLOUDFORMATION_CLIENT = boto3.client("cloudformation")


# pylint: disable=unused-argument
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> Any:
    resource_scan_id = event.get(RESOURCE_SCAN_ID_EVENT_KEY)
    if not resource_scan_id:
        raise ValueError("ResourceScanId is required")

    return json.loads(
        json.dumps(
            CLOUDFORMATION_CLIENT.describe_resource_scan(ResourceScanId=resource_scan_id),
            default=str,
        )
    )
