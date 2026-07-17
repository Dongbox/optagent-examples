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

- 调度示例统一使用 `solve(...)`，由 OptAgent 的策略路径处理模型。
- 只有在明确需要验证某个精确后端兼容性时，才在 API 参考中选择对应的 direct
  exact 接口。
- 不把黑盒策略作为固定调度问题的默认建模方式；只有目标依赖外部仿真器
  或无法展开的业务函数时，才进入黑盒求解路径。
<!-- --8<-- [end:problem] -->

<!-- --8<-- [start:job_shop] -->
## 基础 Job Shop

每个工件按固定工序访问指定机器，工序之间有先后关系，同一机器上的工序
不能重叠，目标通常是最小化最大完工时间。`job_shop_small.py` 使用统一
`ModelBuilder` 的 interval、`no_overlap` 和 `precedence` 表达这些约束，
适合作为固定机器调度的最小模型。
<!-- --8<-- [end:job_shop] -->

<!-- --8<-- [start:flow_shop] -->
## Flow Shop

所有工件按相同的工序顺序经过多个阶段。除阶段内容量外，还要把同一个工件
在前后阶段的完成/开始关系串起来。`flow_shop.py` 使用 sequence、interval
和 precedence 描述该结构，并通过统一的 `solve(...)` 入口求解。
<!-- --8<-- [end:flow_shop] -->

<!-- --8<-- [start:flexible_job_shop] -->
## 柔性 Job Shop

同一工序可以选择多个候选机器，不同机器的加工时长可能不同；还可能存在
共享操作员或其他累计资源。`flexible_job_shop_small.py` 使用
`SchedulingModel` 的 task、alternative、`exactly_one_alternative` 和
`chain` 组织任务语义，再用 unary/cumulative resource 施加容量约束。
这类可选执行方式是调度 facade 的典型使用场景。
<!-- --8<-- [end:flexible_job_shop] -->

## 示例文件

- [job_shop_small.py](../scheduling/job_shop_small.py)：基础 Job Shop。
- [flow_shop.py](../scheduling/flow_shop.py)：Flow Shop。
- 复杂柔性调度应沿用第二、第三层建模路径扩展，并保持需求说明与代码同步。
