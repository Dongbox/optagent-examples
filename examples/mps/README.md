# MPS Examples

该目录保留原始 `window_*.mps` 作为数据文件，并提供一个 OptAgent 建模入口，把窗口模型在运行时重建为 `ModelBuilder` 定义。默认运行方式走 heuristic preset，而不是直接走 exact backend。

运行方式：

```bash
PYTHONPATH=. python examples/mps/solve_window.py --window 0 --summary-only
PYTHONPATH=. python examples/mps/solve_window.py --window 0
PYTHONPATH=. python examples/mps/solve_window.py --window 0 --mode hybrid
PYTHONPATH=. python examples/mps/solve_window.py --window 0 --backend highs_native
PYTHONPATH=. python examples/mps/solve_window.py --window 0 --backend mathopt_mp
```

说明：

* `mps_builder.py` 会把当前 MPS 子集重建为 OptAgent 变量、目标和约束，并给连续变量附上更适合 heuristic 的步长 metadata。
* `resource_flow_heuristic_preset.json` 是默认 preset，显式走 `annealing -> tabu` 的 heuristic orchestration。
* `resource_flow_hybrid_preset.json` 提供 heuristic warm start 后接 exact refine 的路径。
* `resource_flow_exact_preset.json` 仅在 `--mode exact` 时使用。
* 默认 `--backend auto` 只影响 `hybrid` / `exact` 模式；纯 heuristic 模式不会调用 MP backend。
* 对于这些大窗口，建议先用 `--summary-only` 确认建模规模，再执行完整求解。
