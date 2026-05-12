from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any


def to_namespace(mapping: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(**mapping)


@dataclass
class ResourceFlowCase:
    case_name: str
    formulation: str
    planning_period: int
    config: Any
    model_input: Any
    processed_contract_count: int
    filtered_contract_count: int
    source: str
    metadata: dict[str, Any]

    def summary(self) -> dict[str, Any]:
        return {
            "case": self.case_name,
            "formulation": self.formulation,
            "planning_period": self.planning_period,
            "processed_contracts": self.processed_contract_count,
            "filtered_contracts": self.filtered_contract_count,
            "source": self.source,
            **self.metadata,
        }
