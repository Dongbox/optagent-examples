<!-- --8<-- [start:problem] -->
# 调度优化

## 问题概览

调度问题要决定任务的开始时间、加工资源和工序顺序，同时满足机器容量、
工序先后、可选加工方式和交期等约束。常见问题族包括 Job Shop、Flexible
Job Shop 和资源约束项目调度。

## 需求定义

- **输入**：任务、工序顺序、加工时长、候选机器、资源需求和时间窗口。
- **决策**：每个工序选择的资源、开始时间、结束时间和是否存在。
- **约束**：前后关系、机器不重叠、累计资源容量、释放时间和交期。
- **目标**：最小化最大完工时间、总延期、切换成本或资源负载。

## 规模与数据来源

复杂度可以按任务数、工序数、机器数、候选加工方式数、资源维度和时间
窗口长度衡量。公开问题可以参考 [JSPLIB](https://github.com/tamy0612/JSPLIB)、
[FJSPLIB](https://github.com/optimizamento/FJSPlib) 和
[PSPLIB](http://www.om-db.wi.tum.de/psplib/)，它们分别覆盖 Job Shop、
Flexible Job Shop 和资源约束项目调度。

## 三层建模路径

1. **基础调度**：使用 `ModelBuilder` 的 `interval_var`、`no_overlap` 和
   `precedence` 表达固定机器与工序链。
2. **柔性调度**：使用 `SchedulingModel` 的任务、资源、alternative 和
   `exactly_one_alternative` 表达候选机器。
3. **资源约束调度**：在专用调度模型上增加 cumulative 资源、时间日历、
   运输滞后和复合目标；特殊约束再回到底层 `ModelBuilder`。

## 求解方案

- 调度模型完整落在 CP-SAT 支持范围内时，优先使用 `solve_cpsat(...)`。
- 需要快速验证统一模型，或模型包含尚未映射到精确后端的结构时，可使用
  `solve(...)`。
- 不把黑盒策略作为固定调度问题的默认建模方式；只有目标依赖外部仿真器
  或无法展开的业务函数时，才进入黑盒求解路径。
<!-- --8<-- [end:problem] -->

## 示例文件

- [job_shop_small.py](../scheduling/job_shop_small.py)：基础 Job Shop。
- [flow_shop_cp_sat.py](../scheduling/flow_shop_cp_sat.py)：Flow Shop 和 CP-SAT。
- 复杂柔性调度应沿用第二、第三层建模路径扩展，并保持需求说明与代码同步。
