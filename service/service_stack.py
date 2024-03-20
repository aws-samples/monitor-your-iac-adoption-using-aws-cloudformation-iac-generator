# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from typing import Any

import aws_cdk as cdk
import cdk_nag
from constructs import Construct

from service.dashboard import Dashboard
from service.metric_extraction import MetricsExtraction
from service.orchestration import Orchestration
from service.scheduling import Scheduling


class ServiceStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs: Any) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.metric_extraction = MetricsExtraction(self, "MetricExtraction")
        self.orchestration = Orchestration(self, "Orchestration", self.metric_extraction)
        Scheduling(self, "Schduling", self.orchestration)

        Dashboard(self, "Dashboard")

        self._add_cdk_nag_suppressions()

    def _add_cdk_nag_suppressions(self) -> None:
        aws_managed_policies_suppression = cdk_nag.NagPackSuppression(
            id="AwsSolutions-IAM4",
            reason="Allow AWS managed policies",
        )
        cdk_nag.NagSuppressions.add_stack_suppressions(
            stack=self, suppressions=[aws_managed_policies_suppression]
        )

        aws_wildcard_policy_suppression = cdk_nag.NagPackSuppression(
            id="AwsSolutions-IAM5",
            reason="Allow wildcard policies",
        )
        cdk_nag.NagSuppressions.add_resource_suppressions(
            self.metric_extraction,
            suppressions=[aws_wildcard_policy_suppression],
            apply_to_children=True,
        )
        cdk_nag.NagSuppressions.add_resource_suppressions(
            self.orchestration,
            suppressions=[aws_wildcard_policy_suppression],
            apply_to_children=True,
        )
