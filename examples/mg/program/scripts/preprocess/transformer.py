from __future__ import annotations

from typing import Any


class _FallbackTransformer:
    """Import-time placeholder used only when APS is not installed."""

    ALIGNERS: list[Any] = []
    VALIDATORS: list[Any] = []
    FILTERS: list[Any] = []
    GENERATORS: list[Any] = []

    def __init__(self, in_addr: str, out_addr: str, task_timeout: int = 1000) -> None:
        self.in_addr = in_addr
        self.out_addr = out_addr
        self.task_timeout = task_timeout
        self.last_report: dict[str, Any] | None = None

    def run(self) -> bool:
        raise RuntimeError("APS preprocess package is required to run MG preprocess.")


try:  # pragma: no cover - APS is optional for the repository test suite.
    from aps.orm import Table
    from aps.preprocess import Transformer

    from .generators import tConnectablesGenerator, tInfoGenerator, tProcessGenerator
    from .tables import iTables, tTables
    from .validators import iProcessGradeCatVaild
except Exception:  # noqa: BLE001
    Table = None  # type: ignore[assignment]
    Transformer = _FallbackTransformer  # type: ignore[assignment, misc]
    iTables = None  # type: ignore[assignment]
    tTables = None  # type: ignore[assignment]
    iProcessGradeCatVaild = None  # type: ignore[assignment]
    tProcessGenerator = None  # type: ignore[assignment]
    tConnectablesGenerator = None  # type: ignore[assignment]
    tInfoGenerator = None  # type: ignore[assignment]


class CustomTransformer(Transformer):  # type: ignore[misc, valid-type]
    """MG custom preprocess transformer.

    In the original MG project this class inherits ``aps.preprocess.Transformer``
    and registers project-specific validators/generators. The OptAgent example
    keeps the same class and ``main(in_addr, out_addr)`` contract so the formal
    `program/scripts/preprocess` stage has the same shape.
    """

    ALIGNERS: list[Any] = []
    VALIDATORS: list[Any] = [iProcessGradeCatVaild] if iProcessGradeCatVaild is not None else []
    FILTERS: list[Any] = []
    GENERATORS: list[Any] = (
        [tProcessGenerator, tConnectablesGenerator, tInfoGenerator]
        if tProcessGenerator is not None and tConnectablesGenerator is not None and tInfoGenerator is not None
        else []
    )
    def _load_data(self) -> Any:
        if Transformer is _FallbackTransformer:
            return None

        # Match the original MG extension: custom output tables are explicitly
        # instantiated before delegating the common APS loading workflow.
        for table_class in Table.groups["output"].values():  # type: ignore[union-attr]
            self.output_dataset[table_class.table_name] = table_class()
        return super()._load_data()

    def run(self) -> bool:
        if Transformer is _FallbackTransformer:
            return bool(_FallbackTransformer.run(self))
        return bool(super().run())


def main(in_addr: str, out_addr: str) -> bool:
    """Run MG preprocess stage using the APS Transformer-compatible contract."""

    transformer = CustomTransformer(in_addr, out_addr, task_timeout=1000)
    return bool(transformer.run())
