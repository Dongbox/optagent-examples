from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from examples.mg.program.scripts.preprocess.data import MGCase, MGConnectableInfo, MGScore, MGTask


@dataclass
class _State:
    active: bool
    arranged_weight: float
    required_outer_state: int
    is_outer_phase_violation: bool
    is_thin_model: int
    post_process_model: int
    same_width_flag: int
    roller_flag: bool
    is_discontinuable: bool
    is_temp_discontinuable: bool
    discontinuable_reason: str
    outer_run: int = 0
    transition_run: int = 0
    in_outer_state: int = 0


def _round_costs(costs: dict[str, float]) -> dict[str, float]:
    return {key: round(value, 6) for key, value in sorted(costs.items())}


RULE_GROUPS: dict[str, tuple[str, ...]] = {
    "MGLeftMat": ("MGLeftMat", "MGLeftMat.inactive_reward"),
    "MGSmooth": ("MGSmooth.width", "MGSmooth.temp", "MGSmooth.thickness"),
    "MGHardCamp": ("MGHardCamp",),
    "MGDiscontinuable": ("MGDiscontinuable", "MGDiscontinuable.temp"),
    "MGOuterSandwich": (
        "MGOuterSandwich.outer_phase_violation",
        "MGOuterSandwich.sandwich",
        "MGOuterSandwich.overwidth",
    ),
    "MGThinCamp": ("MGThinCamp",),
    "MGPostProcessCamp": ("MGPostProcessCamp.camp", "MGPostProcessCamp.sandwich"),
    "MGChangeRoller": ("MGChangeRoller", "MGChangeRoller.simple"),
    "MGGrindingBeforeOuter": ("MGGrindingBeforeOuter",),
}


def group_rule_costs(breakdown: dict[str, float]) -> dict[str, float]:
    grouped: dict[str, float] = {}
    consumed: set[str] = set()
    for rule_name, keys in RULE_GROUPS.items():
        grouped[rule_name] = round(sum(float(breakdown.get(key, 0.0)) for key in keys), 6)
        consumed.update(keys)
    for key, value in breakdown.items():
        if key not in consumed:
            grouped[key] = round(float(value), 6)
    return dict(sorted(grouped.items()))


def _connectable(case: MGCase, prev: MGTask, curr: MGTask) -> MGConnectableInfo:
    return case.connectables.get((prev.order_id, curr.order_id), MGConnectableInfo())


def _is_outer_state(case: MGCase, arranged_weight: float) -> int:
    first_stage = arranged_weight < case.context.max_active_weight1
    return int(first_stage if case.context.if_outer_first else not first_stage)


def _connectability_flags(info: MGConnectableInfo) -> tuple[bool, bool, str]:
    if info.connectable_flag:
        return False, False, ""
    if not info.width_flag:
        return True, False, "width_flag=0"
    if not info.thickness_flag:
        return True, False, "thickness_flag=0"
    if not info.temp_flag:
        return False, True, "temp_flag=0"
    if not info.category_flag:
        return True, False, "category_flag=0"
    return True, False, "connectable_flag=0"


def _build_states(case: MGCase, sequence: list[int]) -> tuple[list[int], list[int], dict[int, _State]]:
    states: dict[int, _State] = {}
    active_sequence: list[int] = []
    inactive_sequence: list[int] = []
    previous_state: _State | None = None
    previous_task: MGTask | None = None

    for position, task_index in enumerate(sequence):
        task = case.tasks[task_index]
        if position == 0:
            arranged_weight = task.weight
            required_outer_state = _is_outer_state(case, arranged_weight)
            state = _State(
                active=True,
                arranged_weight=arranged_weight,
                required_outer_state=required_outer_state,
                is_outer_phase_violation=bool(task.is_outer) != bool(required_outer_state),
                is_thin_model=task.is_thin,
                post_process_model=task.post_process,
                same_width_flag=1,
                roller_flag=False,
                is_discontinuable=False,
                is_temp_discontinuable=False,
                discontinuable_reason="",
            )
        elif previous_state is None or previous_task is None:
            raise RuntimeError("internal state construction error")
        elif not previous_state.active:
            state = _State(
                active=False,
                arranged_weight=previous_state.arranged_weight,
                required_outer_state=previous_state.required_outer_state,
                is_outer_phase_violation=previous_state.is_outer_phase_violation,
                is_thin_model=task.is_thin if task.is_thin else previous_state.is_thin_model,
                post_process_model=task.post_process if task.post_process else previous_state.post_process_model,
                same_width_flag=1,
                roller_flag=False,
                is_discontinuable=False,
                is_temp_discontinuable=False,
                discontinuable_reason="inactive prefix already closed",
            )
        else:
            arranged_weight = previous_state.arranged_weight + task.weight
            if arranged_weight >= case.context.active_weight_limit:
                state = _State(
                    active=False,
                    arranged_weight=previous_state.arranged_weight,
                    required_outer_state=previous_state.required_outer_state,
                    is_outer_phase_violation=previous_state.is_outer_phase_violation,
                    is_thin_model=task.is_thin if task.is_thin else previous_state.is_thin_model,
                    post_process_model=task.post_process if task.post_process else previous_state.post_process_model,
                    same_width_flag=1,
                    roller_flag=False,
                    is_discontinuable=False,
                    is_temp_discontinuable=False,
                    discontinuable_reason="reached active weight limit",
                )
            else:
                info = _connectable(case, previous_task, task)
                is_discontinuable, is_temp_discontinuable, reason = _connectability_flags(info)
                required_outer_state = _is_outer_state(case, arranged_weight)
                state = _State(
                    active=True,
                    arranged_weight=arranged_weight,
                    required_outer_state=required_outer_state,
                    is_outer_phase_violation=bool(task.is_outer) != bool(required_outer_state),
                    is_thin_model=task.is_thin if task.is_thin else previous_state.is_thin_model,
                    post_process_model=task.post_process if task.post_process else previous_state.post_process_model,
                    same_width_flag=info.same_width_flag,
                    roller_flag=previous_task.width < task.width and info.same_width_flag == 0,
                    is_discontinuable=is_discontinuable,
                    is_temp_discontinuable=is_temp_discontinuable,
                    discontinuable_reason=reason,
                )

        states[task_index] = state
        if state.active:
            active_sequence.append(task_index)
        else:
            inactive_sequence.append(task_index)
        previous_state = state
        previous_task = task

    return active_sequence, inactive_sequence, states


def _apply_outer_state(case: MGCase, active_sequence: list[int], states: dict[int, _State]) -> dict[str, float]:
    costs = defaultdict(float)
    if not case.context.if_outer:
        return costs

    last_active_pos = len(active_sequence) - 1
    for position, task_index in enumerate(active_sequence):
        task = case.tasks[task_index]
        state = states[task_index]
        curr_is_outer = task.is_outer != 0
        curr_is_transition = task.is_outer_transition != 0
        if position == 0:
            if curr_is_outer:
                state.outer_run = 1
                state.in_outer_state = 1
            elif curr_is_transition:
                state.transition_run = 1
                state.in_outer_state = 1
            continue

        prev_task = case.tasks[active_sequence[position - 1]]
        prev_state = states[active_sequence[position - 1]]
        prev_is_outer = prev_task.is_outer != 0
        prev_is_transition = prev_task.is_outer_transition != 0
        prev_in_outer_state = prev_state.in_outer_state != 0
        curr_in_outer_state = (not prev_in_outer_state and curr_is_outer) or (
            prev_in_outer_state and (curr_is_outer or curr_is_transition)
        )
        state.in_outer_state = int(curr_in_outer_state)
        if state.in_outer_state != state.required_outer_state:
            costs["MGOuterSandwich.outer_phase_violation"] += case.rule_weights.outer_phase_violation
        if not curr_in_outer_state and not prev_in_outer_state:
            continue

        if curr_is_outer:
            state.outer_run = prev_state.outer_run + 1 if prev_is_outer else 1
            state.transition_run = 0
            if position == last_active_pos and state.outer_run > 4:
                costs["MGOuterSandwich.sandwich"] += case.rule_weights.outer_sandwich * (state.outer_run - 4)
        else:
            prev_outer_run = prev_state.outer_run
            if not curr_is_transition:
                if prev_outer_run > 0 and prev_outer_run != 4:
                    gap = abs(prev_outer_run - 4)
                    costs["MGOuterSandwich.sandwich"] += case.rule_weights.outer_sandwich * gap * gap
                state.transition_run = 0
                state.outer_run = 0
            else:
                state.transition_run = prev_state.transition_run + 1 if prev_is_transition else 1
                if prev_state.transition_run == 0:
                    if prev_outer_run != 4:
                        gap = abs(prev_outer_run - 4)
                        costs["MGOuterSandwich.sandwich"] += case.rule_weights.outer_sandwich * gap * gap
                    elif task.width < prev_task.out_width:
                        costs["MGOuterSandwich.sandwich"] += case.rule_weights.outer_sandwich
                    elif task.width - prev_task.width > case.context.cross_removal_upper_limit:
                        costs["MGOuterSandwich.overwidth"] += case.rule_weights.outer_overwidth
                else:
                    gap = abs(state.transition_run - 1)
                    costs["MGOuterSandwich.sandwich"] += case.rule_weights.outer_sandwich * gap * gap
                state.outer_run = 0

    return costs


def score_sequence(case: MGCase, sequence: list[int]) -> MGScore:
    normalized = [int(index) for index in sequence]
    active_sequence, inactive_sequence, states = _build_states(case, normalized)
    costs: dict[str, float] = defaultdict(float)

    for position, task_index in enumerate(active_sequence):
        task = case.tasks[task_index]
        state = states[task_index]
        priority = task.left_mat_priority_outer if state.required_outer_state else task.left_mat_priority
        if priority > 0:
            costs["MGLeftMat"] += priority * case.rule_weights.left_mat
        if state.is_discontinuable:
            costs["MGDiscontinuable"] += case.rule_weights.discontinuable
        elif state.is_temp_discontinuable:
            costs["MGDiscontinuable.temp"] += case.rule_weights.discontinuable_temp

        if position == 0:
            continue
        prev_index = active_sequence[position - 1]
        prev_task = case.tasks[prev_index]
        prev_state = states[prev_index]

        width_delta = prev_task.width - task.width
        if state.roller_flag:
            costs["MGSmooth.width"] += width_delta * case.rule_weights.smooth_width
            costs["MGChangeRoller"] += case.rule_weights.change_roller
            ok_followers = True
            for follower_index in active_sequence[position : position + 2]:
                if case.tasks[follower_index].is_simple == 0:
                    ok_followers = False
                    break
            if len(active_sequence[position : position + 2]) < 2:
                ok_followers = False
            if not ok_followers:
                costs["MGChangeRoller.simple"] += case.rule_weights.change_roller_simple
        else:
            costs["MGSmooth.width"] += abs(width_delta) * case.rule_weights.smooth_width

        costs["MGSmooth.temp"] += abs(prev_task.temp - task.temp) * case.rule_weights.smooth_temp
        costs["MGSmooth.thickness"] += abs(prev_task.thickness - task.thickness) * case.rule_weights.smooth_thickness

        if prev_state.is_thin_model != 0 and prev_state.is_thin_model != state.is_thin_model:
            costs["MGThinCamp"] += case.rule_weights.thin_camp
        if prev_state.post_process_model != 0 and prev_state.post_process_model != state.post_process_model:
            costs["MGPostProcessCamp.camp"] += case.rule_weights.post_process_camp
        if task.zinc_layer and prev_task.zinc_layer and task.zinc_layer != prev_task.zinc_layer:
            costs["MGHardCamp"] += case.rule_weights.hard_camp
        if task.is_outer and not prev_task.is_outer:
            grinding_sum = prev_task.grinding_class
            if position >= 2:
                grinding_sum += case.tasks[active_sequence[position - 2]].grinding_class
            costs["MGGrindingBeforeOuter"] += grinding_sum * case.rule_weights.grinding_before_outer

    for position, task_index in enumerate(active_sequence[:-1]):
        task = case.tasks[task_index]
        next_state = states[active_sequence[position + 1]]
        state = states[task_index]
        if task.post_process != 0 and next_state.post_process_model != state.post_process_model:
            costs["MGPostProcessCamp.sandwich"] += case.rule_weights.post_process_sandwich

    outer_costs = _apply_outer_state(case, active_sequence, states)
    for key, value in outer_costs.items():
        costs[key] += value

    inactive_left_priority = sum(case.tasks[index].left_mat_priority for index in inactive_sequence)
    inactive_left_reward = inactive_left_priority * case.rule_weights.left_mat
    if inactive_left_reward:
        costs["MGLeftMat.inactive_reward"] -= inactive_left_reward
    diagnostics = {
        "active_count": len(active_sequence),
        "inactive_count": len(inactive_sequence),
        "active_weight": round(sum(case.tasks[index].weight for index in active_sequence), 6),
        "inactive_left_priority": inactive_left_priority,
        "inactive_left_reward": round(inactive_left_reward, 6),
        "active_order_ids": [case.tasks[index].order_id for index in active_sequence],
        "grouped_rule_costs": group_rule_costs(costs),
    }
    total = float(sum(costs.values()))
    return MGScore(
        total_cost=round(total, 6),
        active_sequence=active_sequence,
        inactive_sequence=inactive_sequence,
        breakdown=_round_costs(costs),
        diagnostics=diagnostics,
    )


def build_penalty_matrix(case: MGCase) -> list[list[int]]:
    matrix: list[list[int]] = []
    for prev in case.tasks:
        row: list[int] = []
        for curr in case.tasks:
            if prev.index == curr.index:
                row.append(0)
                continue
            info = _connectable(case, prev, curr)
            penalty = 0
            if not info.connectable_flag:
                penalty += 10_000
            penalty += int(abs(prev.width - curr.width))
            penalty += int(abs(prev.thickness - curr.thickness) * 100)
            penalty += int(abs(prev.temp - curr.temp))
            row.append(penalty)
        matrix.append(row)
    return matrix


def score_sequence_external(sequence: list[int], case: MGCase) -> float:
    return score_sequence(case, sequence).total_cost
