# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from typing import Any

import aws_cdk as cdk
from aws_cdk import aws_cloudwatch as cloudwatch
from constructs import Construct

import cdk_constants as constants

DEFAULT_DASHBOARD_INTERVAL = cdk.Duration.days(7)
DEFAULT_PERIOD = cdk.Duration.days(1)

DIMENSIONS_MAP = dimensions_map = {
    "AccountID": cdk.Aws.ACCOUNT_ID,
    "Region": cdk.Aws.REGION,
}

DASHBOARD_NAME = "iac-adoption"

TOTAL = "total"
MANAGED = "managed"
MATH_EXPRESSION_PERCENTAGE = f"IF(total==0,100,100*({MANAGED}/{TOTAL}))"

SUMMARY_PANEL_WIDTH = 16
SUMMARY_PANEL_WIDGET_HEIGHT = 6

RESOURCE_PANEL_WIDTH = 4
RESOURCE_PANEL_WIDGET_HEIGHT = 5


class Dashboard(Construct):
    def __init__(self, scope: Construct, _id: str, **kwargs: Any) -> None:
        super().__init__(scope, _id, **kwargs)

        self.dashboard = cloudwatch.Dashboard(
            self,
            "Dashboard",
            dashboard_name=DASHBOARD_NAME,
            default_interval=DEFAULT_DASHBOARD_INTERVAL,
            period_override=cloudwatch.PeriodOverride.AUTO,
        )

        summary_panel = Dashboard._create_summary_panel_row()
        resource_panels = Dashboard._create_resource_panels_row()

        self.dashboard.add_widgets(summary_panel, resource_panels)  # type: ignore

    @staticmethod
    def _create_summary_panel_row() -> cloudwatch.Row:
        header = cloudwatch.TextWidget(
            markdown="## All AWS resources",
            height=1,
            width=SUMMARY_PANEL_WIDTH,
            background=cloudwatch.TextWidgetBackground.TRANSPARENT,
        )

        total_metric = cloudwatch.Metric(
            namespace=constants.CLOUDWATCH_METRICS_NAMESPACE,
            metric_name="TotalResources",
            statistic="Max",
            label="Total Resources",
            period=DEFAULT_PERIOD,
            dimensions_map=DIMENSIONS_MAP,
        )

        managed_metric = cloudwatch.Metric(
            namespace=constants.CLOUDWATCH_METRICS_NAMESPACE,
            metric_name="ManagedResources",
            statistic="Max",
            label="Managed Resources",
            period=DEFAULT_PERIOD,
            dimensions_map=DIMENSIONS_MAP,
        )

        percentage_math_expression = cloudwatch.MathExpression(
            expression=MATH_EXPRESSION_PERCENTAGE,
            label="Managed resources (%)",
            period=DEFAULT_PERIOD,
            using_metrics={
                TOTAL: total_metric,
                MANAGED: managed_metric,
            },
        )

        gauge = cloudwatch.GaugeWidget(
            title="",
            width=SUMMARY_PANEL_WIDTH / 2,
            height=SUMMARY_PANEL_WIDGET_HEIGHT,
            metrics=[percentage_math_expression],
        )

        bars = cloudwatch.GraphWidget(
            title="",
            width=SUMMARY_PANEL_WIDTH / 2,
            height=SUMMARY_PANEL_WIDGET_HEIGHT,
            left=[total_metric],
            right=[managed_metric],
            left_y_axis=cloudwatch.YAxisProps(label=TOTAL),
            right_y_axis=cloudwatch.YAxisProps(label=MANAGED),
            view=cloudwatch.GraphWidgetView.BAR,
            period=DEFAULT_PERIOD,
            legend_position=cloudwatch.LegendPosition.BOTTOM,
        )

        percentage_time_series = cloudwatch.GraphWidget(
            title="",
            width=SUMMARY_PANEL_WIDTH / 2,
            height=SUMMARY_PANEL_WIDGET_HEIGHT,
            left=[percentage_math_expression],
            left_y_axis=cloudwatch.YAxisProps(label="Percent", show_units=False, min=0),
            view=cloudwatch.GraphWidgetView.TIME_SERIES,
            period=DEFAULT_PERIOD,
            legend_position=cloudwatch.LegendPosition.BOTTOM,
        )

        count_time_series = cloudwatch.GraphWidget(
            title="",
            width=SUMMARY_PANEL_WIDTH / 2,
            height=SUMMARY_PANEL_WIDGET_HEIGHT,
            left=[total_metric, managed_metric],
            left_y_axis=cloudwatch.YAxisProps(min=0),
            view=cloudwatch.GraphWidgetView.TIME_SERIES,
            period=DEFAULT_PERIOD,
            legend_position=cloudwatch.LegendPosition.BOTTOM,
        )

        column = cloudwatch.Column(
            header,
            cloudwatch.Row(gauge, bars),  # type: ignore
            cloudwatch.Row(percentage_time_series, count_time_series),  # type: ignore
        )

        row = cloudwatch.Row(column)  # type: ignore
        return row

    @staticmethod
    def _create_resource_panels_row() -> cloudwatch.Row:
        resource_panel_columns = list(
            map(
                Dashboard._create_resource_panel,
                constants.RESOURCE_TYPE_FOCUS_LIST,
            )
        )
        row = cloudwatch.Row(*resource_panel_columns)  # type: ignore
        return row

    @staticmethod
    def _create_resource_panel(resource_type: str) -> cloudwatch.Column:
        _, service, resource = resource_type.split(constants.RESOURCE_TYPE_DELIMETER)

        total_metric = cloudwatch.Metric(
            namespace=constants.CLOUDWATCH_METRICS_NAMESPACE,
            metric_name=f"Total{service}{resource}s",
            statistic="Max",
            label=f"Total {service} {resource}s",
            period=DEFAULT_PERIOD,
            dimensions_map=DIMENSIONS_MAP,
        )

        managed_metric = cloudwatch.Metric(
            namespace=constants.CLOUDWATCH_METRICS_NAMESPACE,
            metric_name=f"Managed{service}{resource}s",
            statistic="Max",
            label=f"Managed {service} {resource}s",
            period=DEFAULT_PERIOD,
            dimensions_map=DIMENSIONS_MAP,
        )

        percentage_math_expression = cloudwatch.MathExpression(
            expression=MATH_EXPRESSION_PERCENTAGE,
            label="Managed resources (%)",
            period=DEFAULT_PERIOD,
            using_metrics={
                TOTAL: total_metric,
                MANAGED: managed_metric,
            },
        )

        header = cloudwatch.TextWidget(
            markdown=f"### {service} {resource}s",
            width=RESOURCE_PANEL_WIDTH,
            height=1,
            background=cloudwatch.TextWidgetBackground.TRANSPARENT,
        )

        gauge = cloudwatch.GaugeWidget(
            title="",
            width=RESOURCE_PANEL_WIDTH,
            height=RESOURCE_PANEL_WIDGET_HEIGHT,
            metrics=[percentage_math_expression],
        )

        bars = cloudwatch.GraphWidget(
            title="",
            width=RESOURCE_PANEL_WIDTH,
            height=RESOURCE_PANEL_WIDGET_HEIGHT,
            left=[total_metric],
            right=[managed_metric],
            left_y_axis=cloudwatch.YAxisProps(label=TOTAL),
            right_y_axis=cloudwatch.YAxisProps(label=MANAGED),
            view=cloudwatch.GraphWidgetView.BAR,
            period=DEFAULT_PERIOD,
            legend_position=cloudwatch.LegendPosition.BOTTOM,
        )

        column = cloudwatch.Column(header, gauge, bars)
        return column
