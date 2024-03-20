# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from typing import Any

from aws_cdk import aws_iam as iam
from aws_cdk import aws_scheduler as scheduler
from constructs import Construct

from service.orchestration import Orchestration

FLEXIBLE_TIME_WINDOW = scheduler.CfnSchedule.FlexibleTimeWindowProperty(
    mode="FLEXIBLE",
    maximum_window_in_minutes=60,
)
SCHEDULE_EXPRESSION_DAILY = "rate(1 day)"
STATE_MACHINE_INPUT = "{}"


class Scheduling(Construct):
    def __init__(self, scope: Construct, _id: str, orchestration: Orchestration, **kwargs: Any) -> None:
        super().__init__(scope, _id, **kwargs)

        # IAM role allowing scheduler to execute orchestration.state_machine
        scheduler_execution_role = self._create_scheduler_iam_execution_role(orchestration)

        target = self._create_schedule_target(orchestration, scheduler_execution_role)

        # Schedule the execution of orchestration.state_machine
        self.event_bridge_schedule = scheduler.CfnSchedule(
            self,
            "Schedule",
            flexible_time_window=FLEXIBLE_TIME_WINDOW,
            schedule_expression=SCHEDULE_EXPRESSION_DAILY,
            target=target,
        )

    def _create_schedule_target(
        self, orchestration: Orchestration, target_execution_role: iam.Role
    ) -> scheduler.CfnSchedule.TargetProperty:
        return scheduler.CfnSchedule.TargetProperty(
            arn=orchestration.state_machine.state_machine_arn,
            role_arn=target_execution_role.role_arn,
            input=STATE_MACHINE_INPUT,
        )

    def _create_scheduler_iam_execution_role(self, orchestration: Orchestration) -> iam.Role:
        return iam.Role(
            self,
            "Role",
            assumed_by=iam.ServicePrincipal("scheduler.amazonaws.com"),
            inline_policies={
                "AllowExecution": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["states:StartExecution"],
                            effect=iam.Effect.ALLOW,
                            resources=[orchestration.state_machine.state_machine_arn],
                        )
                    ]
                )
            },
        )
