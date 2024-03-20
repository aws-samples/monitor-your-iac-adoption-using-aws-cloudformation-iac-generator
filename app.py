#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import aws_cdk as cdk
import cdk_nag

import cdk_constants as constants
from service.service_stack import ServiceStack

app = cdk.App()
cdk.Aspects.of(app).add(cdk_nag.AwsSolutionsChecks())

ServiceStack(
    app,
    "IacAdoptionMonitor",
    env=constants.ENVIRONMENT,
)

app.synth()
