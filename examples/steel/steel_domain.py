from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import time
from typing import Any


DATA_PATH = Path(__file__).with_name("data") / "steel_coils.json"
EPS = 1e-6


@dataclass(frozen=True)
class SteelCoilInstance:
    name: str
    coils: list[list[float]]


@dataclass(frozen=True)
class SteelSeedResult:
    sequence: list[int]
    objective: int
    solver_name: str
    strategy: str
    elapsed_seconds: float
    source: str


def _load_data() -> dict[str, list[list[float]]]:
    return json.loads(DATA_PATH.read_text())


def load_steel_instances() -> dict[str, SteelCoilInstance]:
    payload = _load_data()
    bundled = payload["bundled"]
    return {
        "toy": SteelCoilInstance(name="toy_5", coils=payload["toy"]),
        "bundled_head40": SteelCoilInstance(name="bundled_head40", coils=bundled[:40]),
        "bundled": SteelCoilInstance(name=f"bundled_{len(bundled)}", coils=bundled),
    }


def can_weld(left: list[float], right: list[float]) -> bool:
    left_thick, left_thick_up, left_thick_down, left_width, left_width_down, left_width_up, left_temp, left_temp_up, left_temp_down = left
    right_thick, right_thick_up, right_thick_down, right_width, right_width_down, right_width_up, right_temp, right_temp_up, right_temp_down = right
    return (
        right_thick_down - EPS <= left_thick <= right_thick_up + EPS
        and right_width_down - EPS <= left_width <= right_width_up + EPS
        and right_temp_down - EPS <= left_temp <= right_temp_up + EPS
        and left_thick_down - EPS <= right_thick <= left_thick_up + EPS
        and left_width_down - EPS <= right_width <= left_width_up + EPS
        and left_temp_down - EPS <= right_temp <= left_temp_up + EPS
    )


def transition_count(sequence: list[int], coils: list[list[float]]) -> int:
    return sum(0 if can_weld(coils[sequence[index - 1]], coils[sequence[index]]) else 1 for index in range(1, len(sequence)))


def edge_penalties(sequence: list[int], coils: list[list[float]]) -> list[int]:
    return [0 if can_weld(coils[sequence[index - 1]], coils[sequence[index]]) else 1 for index in range(1, len(sequence))]


def build_compatibility_matrix(coils: list[list[float]]) -> list[list[int]]:
    return [
        [1 if row_index != col_index and can_weld(coils[row_index], coils[col_index]) else 0 for col_index in range(len(coils))]
        for row_index in range(len(coils))
    ]


def build_penalty_matrix(coils: list[list[float]]) -> list[list[int]]:
    return [
        [0 if row_index == col_index or can_weld(coils[row_index], coils[col_index]) else 1 for col_index in range(len(coils))]
        for row_index in range(len(coils))
    ]


def edge_penalties_from_matrix(sequence: list[int], compatibility_matrix: list[list[int]]) -> list[int]:
    return [
        0 if compatibility_matrix[sequence[index - 1]][sequence[index]] else 1
        for index in range(1, len(sequence))
    ]


def break_positions_from_penalties(edge_penalties: list[int]) -> list[int]:
    return [index + 1 for index, penalty in enumerate(edge_penalties) if penalty > 0]


def transition_count_from_penalties(edge_penalties: list[int]) -> int:
    return sum(int(penalty) for penalty in edge_penalties)


def analyze_sequence(sequence: list[int], coils: list[list[float]]) -> dict[str, Any]:
    penalties = edge_penalties(sequence, coils)
    breaks = [
        {"prev": sequence[index - 1], "curr": sequence[index], "position": index}
        for index in range(1, len(sequence))
        if penalties[index - 1] > 0
    ]
    pair_count = max(0, len(sequence) - 1)
    direct_weld_count = pair_count - len(breaks)
    return {
        "transition_count": len(breaks),
        "break_positions": [item["position"] for item in breaks],
        "edge_penalties": penalties,
        "direct_weld_count": direct_weld_count,
        "pair_count": pair_count,
        "direct_weld_ratio": direct_weld_count / pair_count if pair_count else 1.0,
        "first_breaks": breaks[:10],
    }


def decode_sequence_from_selected_edges(
    *,
    selected_edges: list[tuple[int, int]],
    coil_count: int,
    depot_index: int,
) -> list[int]:
    successor = {left: right for left, right in selected_edges}
    sequence: list[int] = []
    current = successor[depot_index]
    visited: set[int] = set()
    while current != depot_index:
        if current in visited:
            raise ValueError("selected edges contain a cycle before returning to depot")
        visited.add(current)
        sequence.append(current)
        current = successor[current]
    if len(sequence) != coil_count:
        raise ValueError(f"decoded path length {len(sequence)} does not match expected coil_count={coil_count}")
    return sequence


def selected_edges_from_sequence(sequence: list[int], *, depot_index: int) -> list[tuple[int, int]]:
    if not sequence:
        return [(depot_index, depot_index)]
    edges = [(depot_index, sequence[0])]
    edges.extend((sequence[index - 1], sequence[index]) for index in range(1, len(sequence)))
    edges.append((sequence[-1], depot_index))
    return edges


def order_defaults_from_sequence(sequence: list[int], *, coil_count: int, depot_index: int) -> dict[int, int]:
    order = {depot_index: 0}
    for index, coil_id in enumerate(sequence, start=1):
        order[coil_id] = index
    for node in range(coil_count):
        order.setdefault(node, min(coil_count, node + 1))
    return order


def _edge_cost(compatibility: list[list[int]], left: int | None, right: int | None) -> int:
    if left is None or right is None:
        return 0
    return 0 if compatibility[left][right] else 1


def _relocate_delta(
    sequence: list[int],
    *,
    source_index: int,
    insert_before: int,
    compatibility: list[list[int]],
) -> int:
    size = len(sequence)
    if size < 3:
        return 0
    if source_index < 0 or source_index >= size:
        return 0
    if insert_before < 0 or insert_before > size:
        return 0
    if insert_before == source_index or insert_before == source_index + 1:
        return 0

    moved = sequence[source_index]
    prev_source = sequence[source_index - 1] if source_index > 0 else None
    next_source = sequence[source_index + 1] if source_index + 1 < size else None

    adjusted_insert = insert_before - 1 if insert_before > source_index else insert_before
    prev_insert = sequence[adjusted_insert - 1] if adjusted_insert > 0 else None
    next_insert = sequence[adjusted_insert] if adjusted_insert < size - 1 else None

    old_cost = (
        _edge_cost(compatibility, prev_source, moved)
        + _edge_cost(compatibility, moved, next_source)
        + _edge_cost(compatibility, prev_insert, next_insert)
    )
    new_cost = (
        _edge_cost(compatibility, prev_source, next_source)
        + _edge_cost(compatibility, prev_insert, moved)
        + _edge_cost(compatibility, moved, next_insert)
    )
    return new_cost - old_cost


def _apply_relocate(sequence: list[int], *, source_index: int, insert_before: int) -> list[int]:
    updated = list(sequence)
    moved = updated.pop(source_index)
    if insert_before > source_index:
        insert_before -= 1
    updated.insert(insert_before, moved)
    return updated


def _two_opt_delta(
    sequence: list[int],
    *,
    start: int,
    end: int,
    compatibility: list[list[int]],
) -> int:
    size = len(sequence)
    if start < 0 or end > size or end - start < 2:
        return 0
    left_prev = sequence[start - 1] if start > 0 else None
    left_curr = sequence[start]
    right_curr = sequence[end - 1]
    right_next = sequence[end] if end < size else None
    old_cost = _edge_cost(compatibility, left_prev, left_curr) + _edge_cost(compatibility, right_curr, right_next)
    new_cost = _edge_cost(compatibility, left_prev, right_curr) + _edge_cost(compatibility, left_curr, right_next)
    return new_cost - old_cost


def _apply_two_opt(sequence: list[int], *, start: int, end: int) -> list[int]:
    updated = list(sequence)
    updated[start:end] = reversed(updated[start:end])
    return updated


def _repair_sequence_breaks(
    sequence: list[int],
    *,
    compatibility: list[list[int]],
    max_rounds: int = 24,
) -> list[int]:
    current = list(sequence)
    if len(current) < 3:
        return current

    for _ in range(max_rounds):
        penalties = edge_penalties_from_matrix(current, compatibility)
        breaks = break_positions_from_penalties(penalties)
        if not breaks:
            break

        best_sequence: list[int] | None = None
        best_delta = 0

        for position in breaks:
            for source_index in range(len(current)):
                if source_index in {position - 1, position}:
                    continue
                delta = _relocate_delta(
                    current,
                    source_index=source_index,
                    insert_before=position,
                    compatibility=compatibility,
                )
                if delta < best_delta:
                    best_delta = delta
                    best_sequence = _apply_relocate(
                        current,
                        source_index=source_index,
                        insert_before=position,
                    )

            window_start = max(1, position - 24)
            window_end = min(len(current), position + 24)
            for start in range(window_start, position):
                for end in range(position + 1, window_end + 1):
                    delta = _two_opt_delta(
                        current,
                        start=start,
                        end=end,
                        compatibility=compatibility,
                    )
                    if delta < best_delta:
                        best_delta = delta
                        best_sequence = _apply_two_opt(current, start=start, end=end)

        if best_sequence is None or best_delta >= 0:
            break
        current = best_sequence

    return current


def build_internal_seed(instance: SteelCoilInstance) -> SteelSeedResult:
    compatibility = build_compatibility_matrix(instance.coils)
    coil_count = len(instance.coils)
    started = time.monotonic()
    paths: list[list[int]] = [[node] for node in range(coil_count)]
    degree = [0] * coil_count

    def endpoint_score(node_id: int) -> int:
        return int(sum(compatibility[node_id]))

    while True:
        best_merge: tuple[int, int, bool, bool] | None = None
        best_score: tuple[int, int, int] | None = None
        for left_index, left_path in enumerate(paths):
            left_options = ((left_path[0], False), (left_path[-1], True))
            for right_index in range(left_index + 1, len(paths)):
                right_path = paths[right_index]
                right_options = ((right_path[0], False), (right_path[-1], True))
                for left_endpoint, left_is_tail in left_options:
                    if degree[left_endpoint] >= 2:
                        continue
                    for right_endpoint, right_is_tail in right_options:
                        if degree[right_endpoint] >= 2:
                            continue
                        if compatibility[left_endpoint][right_endpoint] != 1:
                            continue
                        candidate_score = (
                            endpoint_score(left_endpoint) + endpoint_score(right_endpoint),
                            len(left_path) + len(right_path),
                            -abs(len(left_path) - len(right_path)),
                        )
                        if best_score is None or candidate_score > best_score:
                            best_score = candidate_score
                            best_merge = (left_index, right_index, left_is_tail, right_is_tail)
        if best_merge is None:
            break
        left_index, right_index, left_is_tail, right_is_tail = best_merge
        left_path = paths[left_index]
        right_path = paths[right_index]
        if not left_is_tail:
            left_path = list(reversed(left_path))
        if right_is_tail:
            right_path = list(reversed(right_path))
        degree[left_path[-1]] += 1
        degree[right_path[0]] += 1
        paths[left_index] = left_path + right_path
        paths.pop(right_index)

    while len(paths) > 1:
        best_join: tuple[int, int, bool, bool] | None = None
        best_score: tuple[int, int, int] | None = None
        for left_index, left_path in enumerate(paths):
            for right_index in range(left_index + 1, len(paths)):
                right_path = paths[right_index]
                orientations = (
                    (False, False),
                    (False, True),
                    (True, False),
                    (True, True),
                )
                for reverse_left, reverse_right in orientations:
                    left_candidate = list(reversed(left_path)) if reverse_left else left_path
                    right_candidate = list(reversed(right_path)) if reverse_right else right_path
                    left_endpoint = left_candidate[-1]
                    right_endpoint = right_candidate[0]
                    compatible = int(compatibility[left_endpoint][right_endpoint])
                    candidate_score = (
                        compatible,
                        endpoint_score(left_endpoint) + endpoint_score(right_endpoint),
                        len(left_candidate) + len(right_candidate),
                    )
                    if best_score is None or candidate_score > best_score:
                        best_score = candidate_score
                        best_join = (left_index, right_index, reverse_left, reverse_right)
        assert best_join is not None
        left_index, right_index, reverse_left, reverse_right = best_join
        left_path = list(reversed(paths[left_index])) if reverse_left else paths[left_index]
        right_path = list(reversed(paths[right_index])) if reverse_right else paths[right_index]
        paths[left_index] = left_path + right_path
        paths.pop(right_index)

    sequence = paths[0] if paths else []
    sequence = _repair_sequence_breaks(sequence, compatibility=compatibility)
    objective = transition_count(sequence, instance.coils)
    return SteelSeedResult(
        sequence=sequence,
        objective=objective,
        solver_name="internal_path_merge",
        strategy="compatibility_path_merge_break_repair",
        elapsed_seconds=time.monotonic() - started,
        source="internal_seed",
    )


def build_ortools_seed(
    instance: SteelCoilInstance,
    *,
    time_limit_seconds: int = 10,
    strategy: str = "guided_local_search",
) -> SteelSeedResult | None:
    try:
        from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    except Exception:
        return None

    penalty_matrix = build_penalty_matrix(instance.coils)
    coil_count = len(instance.coils)
    depot = coil_count
    matrix = [row + [0] for row in penalty_matrix]
    matrix.append([0] * (coil_count + 1))
    manager = pywrapcp.RoutingIndexManager(coil_count + 1, 1, depot)
    routing = pywrapcp.RoutingModel(manager)

    def transit(from_index: int, to_index: int) -> int:
        left = manager.IndexToNode(from_index)
        right = manager.IndexToNode(to_index)
        return int(matrix[left][right])

    transit_index = routing.RegisterTransitCallback(transit)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_index)
    search = pywrapcp.DefaultRoutingSearchParameters()
    search.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    strategy_map = {
        "guided_local_search": routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH,
        "tabu_search": routing_enums_pb2.LocalSearchMetaheuristic.TABU_SEARCH,
        "simulated_annealing": routing_enums_pb2.LocalSearchMetaheuristic.SIMULATED_ANNEALING,
    }
    search.local_search_metaheuristic = strategy_map.get(
        strategy,
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH,
    )
    search.time_limit.seconds = max(1, int(time_limit_seconds))
    search.log_search = False

    started = time.monotonic()
    solution = routing.SolveWithParameters(search)
    elapsed = time.monotonic() - started
    if solution is None:
        return None

    index = routing.Start(0)
    sequence: list[int] = []
    while not routing.IsEnd(index):
        node = manager.IndexToNode(index)
        if node != depot:
            sequence.append(node)
        index = solution.Value(routing.NextVar(index))
    objective = transition_count(sequence, instance.coils)
    return SteelSeedResult(
        sequence=sequence,
        objective=objective,
        solver_name="ortools_routing",
        strategy=strategy,
        elapsed_seconds=elapsed,
        source="open_source_seed",
    )
