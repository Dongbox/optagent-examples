from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Any


@dataclass(frozen=True)
class SequenceAdjacencyMove:
    kind: str
    value: list[int]
    metadata: dict[str, Any]
    delta: int


def greedy_construct_sequence(
    penalty_matrix: list[list[int]],
    *,
    rng: random.Random | None = None,
) -> list[int]:
    size = len(penalty_matrix)
    if size <= 1:
        return list(range(size))
    local_rng = rng or random.Random(0)
    sequence = _path_merge_construct_sequence(penalty_matrix, rng=local_rng)
    return repair_sequence_breaks(sequence, penalty_matrix=penalty_matrix)


def edge_penalties(sequence: list[int], penalty_matrix: list[list[int]]) -> list[int]:
    return [int(penalty_matrix[sequence[index - 1]][sequence[index]]) for index in range(1, len(sequence))]


def break_positions(sequence: list[int], penalty_matrix: list[list[int]]) -> list[int]:
    return [index + 1 for index, penalty in enumerate(edge_penalties(sequence, penalty_matrix)) if penalty > 0]


def _edge_cost(penalty_matrix: list[list[int]], left: int | None, right: int | None) -> int:
    if left is None or right is None:
        return 0
    return int(penalty_matrix[left][right])


def relocate_delta(
    sequence: list[int],
    *,
    source_index: int,
    insert_before: int,
    penalty_matrix: list[list[int]],
) -> int:
    size = len(sequence)
    if size < 3 or source_index < 0 or source_index >= size or insert_before < 0 or insert_before > size:
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
        _edge_cost(penalty_matrix, prev_source, moved)
        + _edge_cost(penalty_matrix, moved, next_source)
        + _edge_cost(penalty_matrix, prev_insert, next_insert)
    )
    new_cost = (
        _edge_cost(penalty_matrix, prev_source, next_source)
        + _edge_cost(penalty_matrix, prev_insert, moved)
        + _edge_cost(penalty_matrix, moved, next_insert)
    )
    return new_cost - old_cost


def apply_relocate(sequence: list[int], *, source_index: int, insert_before: int) -> list[int]:
    updated = list(sequence)
    moved = updated.pop(source_index)
    if insert_before > source_index:
        insert_before -= 1
    updated.insert(insert_before, moved)
    return updated


def two_opt_delta(
    sequence: list[int],
    *,
    start: int,
    end: int,
    penalty_matrix: list[list[int]],
) -> int:
    size = len(sequence)
    if start < 0 or end > size or end - start < 2:
        return 0
    left_prev = sequence[start - 1] if start > 0 else None
    left_curr = sequence[start]
    right_curr = sequence[end - 1]
    right_next = sequence[end] if end < size else None
    old_cost = _edge_cost(penalty_matrix, left_prev, left_curr) + _edge_cost(penalty_matrix, right_curr, right_next)
    new_cost = _edge_cost(penalty_matrix, left_prev, right_curr) + _edge_cost(penalty_matrix, left_curr, right_next)
    return new_cost - old_cost


def apply_two_opt(sequence: list[int], *, start: int, end: int) -> list[int]:
    updated = list(sequence)
    updated[start:end] = reversed(updated[start:end])
    return updated


def repair_sequence_breaks(
    sequence: list[int],
    *,
    penalty_matrix: list[list[int]],
    max_rounds: int = 24,
    break_window: int = 24,
) -> list[int]:
    current = list(sequence)
    if len(current) < 3:
        return current

    for _ in range(max_rounds):
        penalties = edge_penalties(current, penalty_matrix)
        breaks = [index + 1 for index, penalty in enumerate(penalties) if penalty > 0]
        if not breaks:
            break

        best_sequence: list[int] | None = None
        best_delta = 0

        for position in breaks:
            for source_index in range(len(current)):
                if source_index in {position - 1, position}:
                    continue
                delta = relocate_delta(
                    current,
                    source_index=source_index,
                    insert_before=position,
                    penalty_matrix=penalty_matrix,
                )
                if delta < best_delta:
                    best_delta = delta
                    best_sequence = apply_relocate(
                        current,
                        source_index=source_index,
                        insert_before=position,
                    )

            window_start = max(1, position - break_window)
            window_end = min(len(current), position + break_window)
            for start in range(window_start, position):
                for end in range(position + 1, window_end + 1):
                    delta = two_opt_delta(
                        current,
                        start=start,
                        end=end,
                        penalty_matrix=penalty_matrix,
                    )
                    if delta < best_delta:
                        best_delta = delta
                        best_sequence = apply_two_opt(current, start=start, end=end)

        if best_sequence is None or best_delta >= 0:
            break
        current = best_sequence

    return current


def _endpoint_score(penalty_matrix: list[list[int]], node_id: int) -> int:
    return sum(1 for other, penalty in enumerate(penalty_matrix[node_id]) if other != node_id and int(penalty) == 0)


def _pick_best(
    candidates: list[tuple[tuple[int, ...], tuple[Any, ...]]],
    *,
    rng: random.Random,
) -> tuple[Any, ...] | None:
    if not candidates:
        return None
    best_score = max(score for score, _ in candidates)
    best_payloads = [payload for score, payload in candidates if score == best_score]
    return rng.choice(best_payloads)


def _path_merge_construct_sequence(
    penalty_matrix: list[list[int]],
    *,
    rng: random.Random,
) -> list[int]:
    size = len(penalty_matrix)
    paths: list[list[int]] = [[node] for node in range(size)]
    degree = [0] * size

    while True:
        candidates: list[tuple[tuple[int, ...], tuple[int, int, bool, bool]]] = []
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
                        if int(penalty_matrix[left_endpoint][right_endpoint]) != 0:
                            continue
                        candidates.append(
                            (
                                (
                                    _endpoint_score(penalty_matrix, left_endpoint) + _endpoint_score(penalty_matrix, right_endpoint),
                                    len(left_path) + len(right_path),
                                    -abs(len(left_path) - len(right_path)),
                                ),
                                (left_index, right_index, left_is_tail, right_is_tail),
                            )
                        )
        best_merge = _pick_best(candidates, rng=rng)
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
        candidates: list[tuple[tuple[int, ...], tuple[int, int, bool, bool]]] = []
        for left_index, left_path in enumerate(paths):
            for right_index in range(left_index + 1, len(paths)):
                right_path = paths[right_index]
                for reverse_left, reverse_right in (
                    (False, False),
                    (False, True),
                    (True, False),
                    (True, True),
                ):
                    left_candidate = list(reversed(left_path)) if reverse_left else left_path
                    right_candidate = list(reversed(right_path)) if reverse_right else right_path
                    left_endpoint = left_candidate[-1]
                    right_endpoint = right_candidate[0]
                    candidates.append(
                        (
                            (
                                -int(penalty_matrix[left_endpoint][right_endpoint]),
                                _endpoint_score(penalty_matrix, left_endpoint) + _endpoint_score(penalty_matrix, right_endpoint),
                                len(left_candidate) + len(right_candidate),
                            ),
                            (left_index, right_index, reverse_left, reverse_right),
                        )
                    )
        best_join = _pick_best(candidates, rng=rng)
        if best_join is None:
            break
        left_index, right_index, reverse_left, reverse_right = best_join
        left_path = list(reversed(paths[left_index])) if reverse_left else paths[left_index]
        right_path = list(reversed(paths[right_index])) if reverse_right else paths[right_index]
        paths[left_index] = left_path + right_path
        paths.pop(right_index)

    if not paths:
        return []
    return list(paths[0])


def best_break_repair_moves(
    sequence: list[int],
    *,
    penalty_matrix: list[list[int]],
    break_window: int = 24,
    max_breaks: int = 8,
    top_relocates: int = 3,
    top_two_opt: int = 2,
) -> list[SequenceAdjacencyMove]:
    if len(sequence) < 3:
        return []
    positions = break_positions(sequence, penalty_matrix)[:max_breaks]
    candidates: list[SequenceAdjacencyMove] = []
    seen: set[tuple[int, ...]] = set()

    for position in positions:
        relocate_candidates: list[tuple[int, int]] = []
        for source_index in range(len(sequence)):
            if source_index in {position - 1, position}:
                continue
            delta = relocate_delta(
                sequence,
                source_index=source_index,
                insert_before=position,
                penalty_matrix=penalty_matrix,
            )
            if delta < 0:
                relocate_candidates.append((delta, source_index))
        relocate_candidates.sort()
        for delta, source_index in relocate_candidates[:top_relocates]:
            updated = apply_relocate(sequence, source_index=source_index, insert_before=position)
            signature = tuple(updated)
            if signature in seen:
                continue
            seen.add(signature)
            candidates.append(
                SequenceAdjacencyMove(
                    kind="sequence_break_relocate",
                    value=updated,
                    metadata={"source_index": source_index, "insert_before": position},
                    delta=delta,
                )
            )

        start_lb = max(1, position - break_window)
        end_ub = min(len(sequence), position + break_window)
        two_opt_candidates: list[tuple[int, int, int]] = []
        for start in range(start_lb, position):
            for end in range(position + 1, end_ub + 1):
                delta = two_opt_delta(sequence, start=start, end=end, penalty_matrix=penalty_matrix)
                if delta < 0:
                    two_opt_candidates.append((delta, start, end))
        two_opt_candidates.sort()
        for delta, start, end in two_opt_candidates[:top_two_opt]:
            updated = apply_two_opt(sequence, start=start, end=end)
            signature = tuple(updated)
            if signature in seen:
                continue
            seen.add(signature)
            candidates.append(
                SequenceAdjacencyMove(
                    kind="sequence_break_two_opt",
                    value=updated,
                    metadata={"start": start, "end": end},
                    delta=delta,
                )
            )

    return sorted(candidates, key=lambda item: (item.delta, item.kind))


def targeted_break_mutation(
    sequence: list[int],
    *,
    penalty_matrix: list[list[int]],
    rng: random.Random,
    mode: str,
    break_window: int = 24,
) -> list[int] | None:
    candidates = best_break_repair_moves(
        sequence,
        penalty_matrix=penalty_matrix,
        break_window=break_window,
        max_breaks=12,
        top_relocates=4,
        top_two_opt=3,
    )
    if not candidates:
        return None
    if mode == "sequence_two_opt":
        filtered = [item for item in candidates if item.kind == "sequence_break_two_opt"]
    else:
        filtered = [item for item in candidates if item.kind == "sequence_break_relocate"]
    pool = filtered or candidates
    best_delta = min(item.delta for item in pool)
    strongest = [item for item in pool if item.delta == best_delta]
    return list(rng.choice(strongest).value)
