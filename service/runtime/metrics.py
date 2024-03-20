# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from dataclasses import dataclass
from typing import Callable, Iterator, Self

from mypy_boto3_cloudformation.type_defs import ScannedResourceTypeDef

type ScannedResourceFilter = Callable[[ScannedResourceTypeDef], bool]  # type: ignore[valid-type]


# pylint: disable=too-few-public-methods
class ScannedResourceKeys:
    ManagedByStack = "ManagedByStack"
    ResourceType = "ResourceType"


RESOURCE_TYPE_DELIMETER = "::"


@dataclass
class Metric:
    name: str
    filter: ScannedResourceFilter


class ManagedResourceMetrics:
    def __init__(self, metric_name: str, scanned_resource_filter: ScannedResourceFilter) -> None:
        self.total_resource_metric = Metric(
            name=f"Total{metric_name}",
            filter=scanned_resource_filter,
        )
        self.managed_resource_metric = Metric(
            name=f"Managed{metric_name}",
            filter=create_is_managed_resource_filter(scanned_resource_filter),
        )

    def __iter__(self) -> Iterator[Metric]:
        return iter([self.total_resource_metric, self.managed_resource_metric])

    @classmethod
    def from_resource_type(cls, resource_type: str) -> Self:
        """
        Creates a new instance of ManagedResourceMetrics from a resource type
        The resource type must be supported by IaC Generator, see docs:
        https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/resource-import-supported-resources.html
        """

        if not validate_resource_type(resource_type):
            raise ValueError()

        metric_name = generate_metric_name_from_resource_type(resource_type)
        scanned_resource_filter = generate_resource_type_filter(resource_type)

        return cls(metric_name, scanned_resource_filter)


def generate_metric_name_from_resource_type(resource_type: str) -> str:
    _, service, resource = resource_type.split(RESOURCE_TYPE_DELIMETER)
    return f"{service}{resource}s"


def generate_resource_type_filter(resource_type: str) -> ScannedResourceFilter:
    return lambda scanned_resource: scanned_resource.get(ScannedResourceKeys.ResourceType) == resource_type


def validate_resource_type(resource_type: str) -> bool:
    resource_type_parts = resource_type.split(RESOURCE_TYPE_DELIMETER)
    if len(resource_type_parts) != 3:
        return False
    if resource_type_parts[0] != "AWS":
        return False
    return True


def is_managed(scanned_resource: ScannedResourceTypeDef) -> bool:
    return scanned_resource.get(ScannedResourceKeys.ManagedByStack, False)  # type: ignore


def create_is_managed_resource_filter(
    resource_filter: ScannedResourceFilter,
) -> ScannedResourceFilter:
    return lambda scanned_resource: is_managed(scanned_resource) and resource_filter(scanned_resource)
