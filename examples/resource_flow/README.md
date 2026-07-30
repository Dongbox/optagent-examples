<!-- --8<-- [start:problem] -->
# 资源流与网络流

## 问题概览

资源流问题描述资源在时间窗口、工序或设备之间的转移与消耗。它与网络
流共享节点、边、容量、流量守恒和成本等结构，但资源流通常还包含时间、
批次、设备和生产计划语义。

## 需求定义

- **输入**：资源、任务、时间窗口、设备容量、转移关系和初始状态。
- **决策**：每个任务的流向、开始时间、处理方式和资源使用量。
- **约束**：流量守恒、设备容量、时间顺序、库存或状态转移。
- **目标**：最小化生产成本、延期、切换和资源浪费。

## 规模与数据来源

规模主要由时间窗口数、任务数、资源节点数、转移边数和容量维度决定。
经典最大流、最小费用流等网络流问题可以作为相邻问题参考；当前公开
可运行案例聚焦于带生产时间语义的资源流，数据使用仓库内小型、可复现
的压缩 JSON fixture。

## 建模方案

同一问题提供两种结构化表达：`cp_builder.py` 用整数时间和容量语义构造
CP 模型，`milp_builder.py` 用代数变量和线性约束构造 MILP。两者都使用
`ModelBuilder`，差异在于表达式图和直接求解后端，而不是业务需求本身。

## 求解方案

- CP 表达完整时使用 `solve_cpsat(...)`。
- 代数模型需要 OptX 时使用 `solve_milp(..., backend="optx")` 或
  `solve_optx(...)`。
- 对含外部评估器的扩展场景才使用 `solve(...)`；资源流本身不默认使用
  黑盒策略。
<!-- --8<-- [end:problem] -->

<!-- --8<-- [start:solve_case] -->
## 资源流统一求解

资源流案例需要在多个时间窗口内安排需求、库存和生产转移，同时满足节点
容量、流量守恒和交付约束。`solve_case.py` 是统一运行入口：同一份业务
输入可以选择 CP 或 MILP 结构化表达，再调用对应的精确后端；传入
`--mode search` 时则进入由求解器自动选择并并行执行算法组合的公开搜索入口。
<!-- --8<-- [end:solve_case] -->

<!-- --8<-- [start:rolling] -->
## 滚动时间窗

当完整规划期过大或未来状态会随着执行更新时，可在有限窗口内反复建模和
求解，把已执行窗口的库存与状态传递给下一窗口。`rolling.py` 保留上一窗口
的命名变量值作为 warm start，并通过 `advance_window_input` 推进业务输入。
这仍是结构化 CP-SAT 工作流，不需要黑盒策略。
<!-- --8<-- [end:rolling] -->

## 示例文件

- [case_loader.py](../resource_flow/case_loader.py)：加载小型可复现案例。
- [cp_builder.py](../resource_flow/cp_builder.py)：CP-SAT 表达。
- [milp_builder.py](../resource_flow/milp_builder.py)：MILP 表达。
- [solve_case.py](../resource_flow/solve_case.py)：统一运行入口。
- [rolling.py](../resource_flow/rolling.py)：滚动时间窗工作流。
