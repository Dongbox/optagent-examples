from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any

from optagent import ModelBuilder


@dataclass
class VariableSpec:
    name: str
    lb: float | None = 0.0
    ub: float | None = None
    is_integer: bool = False
    is_binary: bool = False


@dataclass
class ParsedMpsModel:
    name: str
    objective_row: str
    objective_sense: str
    objective_terms: list[tuple[str, float]]
    row_senses: dict[str, str]
    row_terms: dict[str, list[tuple[str, float]]]
    rhs_values: dict[str, float]
    variables: dict[str, VariableSpec]
    source_path: Path

    def summary(self) -> dict[str, Any]:
        variable_count = len(self.variables)
        binary_count = sum(1 for spec in self.variables.values() if spec.is_binary)
        integer_count = sum(1 for spec in self.variables.values() if spec.is_integer and not spec.is_binary)
        continuous_count = variable_count - binary_count - integer_count
        constraint_names = [name for name in self.row_senses if name != self.objective_row]
        nnz = len(self.objective_terms) + sum(len(self.row_terms.get(name, ())) for name in constraint_names)
        return {
            "name": self.name,
            "source_path": str(self.source_path),
            "objective_row": self.objective_row,
            "objective_sense": self.objective_sense,
            "variable_count": variable_count,
            "binary_variable_count": binary_count,
            "integer_variable_count": integer_count,
            "continuous_variable_count": continuous_count,
            "constraint_count": len(constraint_names),
            "nonzero_count": nnz,
        }


def parse_mps(path: str | Path, *, objective_sense: str = "min") -> ParsedMpsModel:
    resolved_path = Path(path)
    name = resolved_path.stem
    row_senses: dict[str, str] = {}
    row_terms: dict[str, list[tuple[str, float]]] = {}
    rhs_values: dict[str, float] = {}
    variables: dict[str, VariableSpec] = {}
    objective_row: str | None = None
    objective_terms: list[tuple[str, float]] = []
    section: str | None = None

    with resolved_path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n")
            stripped = line.strip()
            if not stripped or stripped.startswith("*"):
                continue
            head = stripped.split()[0]
            if head in {"NAME", "ROWS", "COLUMNS", "RHS", "BOUNDS", "ENDATA"}:
                section = head
                if head == "NAME":
                    tokens = stripped.split(maxsplit=1)
                    if len(tokens) == 2:
                        name = tokens[1]
                if head == "ENDATA":
                    break
                continue

            if section == "ROWS":
                sense, row_name = stripped.split()[:2]
                row_senses[row_name] = sense
                if sense == "N" and objective_row is None:
                    objective_row = row_name
                continue

            if section == "COLUMNS":
                tokens = stripped.split()
                if len(tokens) >= 2 and tokens[1] == "'MARKER'":
                    continue
                var_name = tokens[0]
                spec = variables.setdefault(var_name, VariableSpec(name=var_name))
                for index in range(1, len(tokens), 2):
                    if index + 1 >= len(tokens):
                        break
                    row_name = tokens[index]
                    coefficient = float(tokens[index + 1])
                    if row_name == objective_row:
                        objective_terms.append((var_name, coefficient))
                    else:
                        row_terms.setdefault(row_name, []).append((var_name, coefficient))
                variables[var_name] = spec
                continue

            if section == "RHS":
                tokens = stripped.split()
                for index in range(1, len(tokens), 2):
                    if index + 1 >= len(tokens):
                        break
                    rhs_values[tokens[index]] = float(tokens[index + 1])
                continue

            if section == "BOUNDS":
                tokens = stripped.split()
                if len(tokens) < 3:
                    continue
                bound_type = tokens[0]
                var_name = tokens[2]
                value = float(tokens[3]) if len(tokens) > 3 else None
                spec = variables.setdefault(var_name, VariableSpec(name=var_name))
                _apply_bound(spec, bound_type, value)
                continue

    if objective_row is None:
        raise ValueError(f"no objective row found in {resolved_path}")

    return ParsedMpsModel(
        name=name,
        objective_row=objective_row,
        objective_sense=objective_sense,
        objective_terms=objective_terms,
        row_senses=row_senses,
        row_terms=row_terms,
        rhs_values=rhs_values,
        variables=variables,
        source_path=resolved_path,
    )


@dataclass
class BuiltMpsProgram:
    program: Any
    parsed: ParsedMpsModel
    variable_node_ids: dict[str, int]
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> dict[str, Any]:
        payload = self.parsed.summary()
        payload.update(self.metadata)
        return payload


INDEXED_NAME_PATTERN = re.compile(r"^(?P<family>[A-Za-z]+)")


def build_program_from_mps(
    path: str | Path,
    *,
    objective_sense: str = "min",
    preferred_backend: str | None = None,
) -> BuiltMpsProgram:
    parsed = parse_mps(path, objective_sense=objective_sense)
    summary = parsed.summary()

    builder = ModelBuilder(
        metadata={
            "case": parsed.name,
            "source_format": "mps",
            "problem_family": "linear_mip",
            "nonzero_count": summary["nonzero_count"],
            **({"preferred_backend": preferred_backend} if preferred_backend else {}),
        },
    )
    const_cache: dict[float, Any] = {}
    variables: dict[str, Any] = {}
    family_counts: dict[str, int] = {}

    def const_expr(value: float) -> Any:
        normalized = float(value)
        expr = const_cache.get(normalized)
        if expr is None:
            expr = builder.const(normalized)
            const_cache[normalized] = expr
        return expr

    for name, spec in parsed.variables.items():
        family = _variable_family(name)
        family_counts[family] = family_counts.get(family, 0) + 1
        if spec.is_integer or spec.is_binary:
            lb = _coerce_int_bound(spec.lb)
            ub = _coerce_int_bound(spec.ub)
            default = _default_for_integer_var(lb, ub)
            expr = builder.int_var(default=default, lb=lb, ub=ub, name=name)
            node = builder.graph.nodes[expr.node_id]
            node.metadata["family"] = family
            node.metadata["source_name"] = name
            variables[name] = expr
        else:
            lb = float(spec.lb) if spec.lb is not None else None
            ub = float(spec.ub) if spec.ub is not None else None
            default = _default_for_float_var(lb, ub)
            expr = builder.float_var(default=default, lb=lb, ub=ub, name=name)
            node = builder.graph.nodes[expr.node_id]
            node.metadata["family"] = family
            node.metadata["source_name"] = name
            node.metadata["step"] = _heuristic_float_step(lb, ub)
            variables[name] = expr

    objective_expr = _weighted_sum(builder, const_expr, variables, parsed.objective_terms)
    if parsed.objective_sense == "max":
        builder.maximize(objective_expr, name=parsed.objective_row)
    else:
        builder.minimize(objective_expr, name=parsed.objective_row)

    for row_name, sense in parsed.row_senses.items():
        if row_name == parsed.objective_row:
            continue
        lhs_expr = _weighted_sum(builder, const_expr, variables, parsed.row_terms.get(row_name, []))
        rhs_expr = const_expr(parsed.rhs_values.get(row_name, 0.0))
        if sense == "L":
            builder.constraint(lhs_expr <= rhs_expr, name=row_name)
        elif sense == "G":
            builder.constraint(lhs_expr >= rhs_expr, name=row_name)
        elif sense == "E":
            builder.constraint(lhs_expr == rhs_expr, name=row_name)
        else:
            raise ValueError(f"unsupported row sense {sense!r} for row {row_name}")

    program = builder.freeze()
    return BuiltMpsProgram(
        program=program,
        parsed=parsed,
        variable_node_ids={name: expr.node_id for name, expr in variables.items()},
        metadata={
            "objective_term_count": len(parsed.objective_terms),
            "constraint_term_count": sum(len(terms) for terms in parsed.row_terms.values()),
            "variable_families": family_counts,
        },
    )


def _weighted_sum(builder: ModelBuilder, const_expr: Any, variables: dict[str, Any], terms: list[tuple[str, float]]) -> Any:
    if not terms:
        return const_expr(0.0)
    exprs: list[Any] = []
    for variable_name, coefficient in terms:
        variable_expr = variables[variable_name]
        if coefficient == 1:
            exprs.append(variable_expr)
        elif coefficient == -1:
            exprs.append(-variable_expr)
        else:
            exprs.append(variable_expr * const_expr(coefficient))
    if len(exprs) == 1:
        return exprs[0]
    return builder.sum(*exprs)


def _apply_bound(spec: VariableSpec, bound_type: str, value: float | None) -> None:
    if bound_type == "UP":
        spec.ub = value
        return
    if bound_type == "LO":
        spec.lb = value
        return
    if bound_type == "FX":
        spec.lb = value
        spec.ub = value
        return
    if bound_type == "FR":
        spec.lb = None
        spec.ub = None
        return
    if bound_type == "MI":
        spec.lb = None
        return
    if bound_type == "PL":
        spec.ub = None
        return
    if bound_type == "BV":
        spec.is_integer = True
        spec.is_binary = True
        spec.lb = 0.0
        spec.ub = 1.0
        return
    if bound_type == "LI":
        spec.is_integer = True
        spec.lb = value
        return
    if bound_type == "UI":
        spec.is_integer = True
        spec.ub = value
        return
    raise ValueError(f"unsupported MPS bound type: {bound_type}")


def _coerce_int_bound(value: float | None) -> int | None:
    if value is None:
        return None
    rounded = int(round(value))
    if abs(value - rounded) > 1e-9:
        raise ValueError(f"expected integer bound, got {value}")
    return rounded


def _default_for_integer_var(lb: int | None, ub: int | None) -> int:
    if lb is not None and ub is not None and lb == ub:
        return lb
    if lb is not None and lb > 0:
        return lb
    if ub is not None and ub < 0:
        return ub
    return 0


def _default_for_float_var(lb: float | None, ub: float | None) -> float:
    if lb is not None and ub is not None and abs(lb - ub) <= 1e-12:
        return lb
    if lb is not None and lb > 0.0:
        return lb
    if ub is not None and ub < 0.0:
        return ub
    return 0.0


def _heuristic_float_step(lb: float | None, ub: float | None) -> float:
    if lb is not None and ub is not None:
        span = abs(ub - lb)
        if span <= 10.0:
            return 1.0
        if span <= 100.0:
            return 2.0
        if span <= 1_000.0:
            return 5.0
        return max(10.0, span / 100.0)
    return 1.0


def _variable_family(name: str) -> str:
    match = INDEXED_NAME_PATTERN.match(name)
    if match is None:
        return "unknown"
    return match.group("family")
