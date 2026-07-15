<!-- --8<-- [start:problem] -->
# 线性与混合整数优化

## 问题概览

这类问题可以把业务需求写成变量、线性表达式、约束和目标函数。典型
场景包括分配、背包、设施选址，以及可以显式线性化的路径问题。

## 需求定义

- **输入**：候选对象、成本或收益、容量、距离矩阵和业务参数。
- **决策**：选择、分配、开设设施，或选择一条满足访问关系的路径。
- **约束**：容量、供需平衡、唯一分配、流守恒和子回路消除。
- **目标**：最大化收益，或最小化成本、距离和资源使用量。

## 规模与数据来源

规模主要由变量数、约束数、非零系数数目和路径节点数决定。TSP 的公开
问题可以参考 [TSPLIB95 对称 TSP 数据集](https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/STSP.html)，
其中每个实例以节点数、坐标或显式距离矩阵描述。

## 建模方案

统一使用 `ModelBuilder`。普通分配、背包和设施选址直接使用整数或布尔
变量；TSP 则使用弧选择变量、每个节点恰好进入和离开一次的约束，以及
MTZ 等子回路消除约束。这样 TSP 仍然是一个可交给精确 MP 后端的模型，
不需要使用 Python 黑盒评分函数。

对于只包含有界整数和结构化序列转移成本的模型，也可以使用
`sequence_var` + `sequence_transition_sum`，再选择 CP-SAT 路径。

## 求解方案

- 需要通用、快速验证模型时使用 `solve(...)`。
- 线性或混合整数模型需要 OptX 精确路径时使用 `solve_optx(...)`。
- 需要通过 MP 语义选择后端时使用 `solve_milp(...)`。
- 结构化序列成本完整落在 CP-SAT 支持范围内时使用 `solve_cpsat(...)`。
<!-- --8<-- [end:problem] -->

<!-- --8<-- [start:assignment] -->
## 指派问题

每个工人必须分配到一个任务，每个任务也必须被一名工人承担；收益由工人和
任务的组合决定。使用二元变量、唯一分配约束和线性收益目标即可表达。

`assignment_optx.py` 通过 `solve_milp(..., backend="optx")` 调用 OptX 精确
混合整数后端，适合需要明确最优性语义的指派模型。
<!-- --8<-- [end:assignment] -->

<!-- --8<-- [start:knapsack] -->
## 背包问题

在总容量有限时选择物品，使总价值最大。每个物品只有选择或不选择两种
状态，容量约束和价值目标构成一个 0/1 混合整数模型。

`knapsack_mathopt.py` 保持 `ModelBuilder` 的业务表达不变，通过 MathOpt MP
适配器求解，适合需要第三方 MP 后端的场景。
<!-- --8<-- [end:knapsack] -->

<!-- --8<-- [start:facility] -->
## 设施选址

在固定开设成本和客户服务成本之间做权衡：决定开设哪些设施，并把每个客户
分配给一个已开设设施。开设变量、分配变量、容量和服务半径共同形成模型。

`facility_location_small.py` 使用整数变量表达开设与分配，并通过 MILP 路径
求解。
<!-- --8<-- [end:facility] -->

<!-- --8<-- [start:routing] -->
## 路径与 TSP

给定节点和距离，要求每个节点恰好访问一次并回到起点，使总距离最小。弧
选择变量负责访问关系，入度/出度约束形成闭环，MTZ 顺序变量消除子回路。

`routing_linearized_small.py` 将 TSP 显式线性化后交给 OptX；简单 TSP 不应
为了展示策略而改写成黑盒模型。
<!-- --8<-- [end:routing] -->

## 示例文件

- [assignment_optx.py](../linear/assignment_optx.py)：二元指派和 OptX 精确求解。
- [knapsack_mathopt.py](../linear/knapsack_mathopt.py)：0/1 背包和第三方 MathOpt MP 适配器。
- [facility_location_small.py](../linear/facility_location_small.py)：设施开设与分配。
- [routing_linearized_small.py](../linear/routing_linearized_small.py)：线性化 TSP。

<!-- --8<-- [start:tsp] -->
## TSP：最短闭合访问路径

### 问题需求

给定一组节点和节点间距离，要求每个节点恰好访问一次，并回到起点，
使总路径长度最小。仅有入度和出度约束时可能产生多个独立回路，因此
还必须加入子回路消除约束。

### 线性建模

`routing_linearized_small.py` 使用二元弧变量 `x[i, j]` 表示是否选择边，
用入度和出度约束形成一个 1-factor，再用顺序变量和 MTZ 约束排除子回路。
目标函数是所选弧的距离加总。

完整代码见 `routing_linearized_small.py`，公开文档页会链接到该文件的固定提交。

### 结构化序列成本

如果问题只需要一个有界整数距离矩阵，也可以用
`sequence_transition_sum(..., include_return_edge=True)` 表达闭环成本，
并通过 `solve_cpsat(...)` 求解。该路线仍然是结构化精确建模，不是黑盒
优化。包含外部模拟器或不可展开评分逻辑时，才转到黑盒问题页。
<!-- --8<-- [end:tsp] -->
