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
    # Don't start a new resource scan and if `ResourceScanId` exists in `event`
    # return the existing `ResourceScanId` instead
    resource_scan_id = event.get(RESOURCE_SCAN_ID_EVENT_KEY)
    if resource_scan_id:
        return {RESOURCE_SCAN_ID_EVENT_KEY: resource_scan_id}

    return json.loads(
        json.dumps(
            CLOUDFORMATION_CLIENT.start_resource_scan(),
            default=str,
        )
    )
