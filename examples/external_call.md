
```python
# 1. 声明一个“函数对象”，此时还没有调用
f = model.create_double_external_function(callback)

# 2. 建立调用表达式，把当前决策值传入 callback
y = model.call(f, x1, x2)

# 3. 让调用结果影响模型
model.minimize(y)
# 或
model.constraint(y)
```

`create_*_external_function()` 只声明函数。没有 `call()`，求解器不知道用什么参数调用它；`call()` 的结果如果最终没有连接到目标或约束，也不会影响优化结果。

但不一定必须“直接放入目标函数”：

- 标量返回值可以作为目标。
- 返回布尔语义的整数值可以作为约束。
- 未启用 surrogate 时，返回值通常还可以继续参与其他表达式。
- 数组返回值通常需要先取元素或聚合，再用于目标或约束。

例如普通 external function：

```python
simulation = model.create_double_array_external_function(run_simulation)
outputs = model.call(simulation, design)

cost = model.at(outputs, 0)
emissions = model.at(outputs, 1)

model.minimize(cost)
model.constraint(emissions <= 100)
```

启用 surrogate modeling 后限制更严格：一个模型最多一个 surrogate external function、只能有一个 `call`，结果原则上必须作为目标或约束的根结果，不能随意嵌套组合。复杂的黑盒约束可以让 callback 直接返回 `0/1` 或约束违反量。

**四种声明方法**

| 方法 | callback 返回类型 | 典型用途 |
| --- | --- | --- |
| `create_double_external_function` | 浮点标量 | 成本、收益、损失、仿真响应 |
| `create_int_external_function` | 整数标量 | 整数指标或 `0/1` 黑盒约束 |
| `create_double_array_external_function` | 浮点数组 | 一次仿真返回成本、排放、温度等多个响应 |
| `create_int_array_external_function` | 整数数组 | 一次计算返回多个计数或离散状态 |

**为什么需要 external**

Hexaly 原生表达式本质上是一棵由已知算子组成的数学表达式树。下面这些可以原生表达，不需要 external：

```python
objective = (
    (1 - 8*x1 + 7*x1**2 - 7*x1**3/3 + x1**4/4)
    * x2**2
    * model.exp(-x2)
)
model.minimize(objective)
```

因此 Hosaki 函数并非必须使用 external。官方示例只是借简单函数演示 surrogate API。

真正需要 external 的情况是计算无法合理转换为 Hexaly 表达式，例如：

- 离散事件仿真。
- 百万次 Monte Carlo 仿真。
- 有限元、流体力学或其他工程模拟器。
- 已有的 C++、Java、Python 业务算法。
- 机器学习模型推理。
- 复杂路径规划、排队系统或生产系统模拟。
- 一个封装好的第三方计算库。
- 数据相关循环、递归或复杂分支逻辑，而 Hexaly 没有对应算子。

例如：

```python
def simulate_capacity(args):
    capacity = args.get(0)

    total_profit = 0.0
    for scenario in one_million_scenarios:
        demand = run_demand_simulation(scenario)
        total_profit += calculate_profit(capacity, demand)

    return total_profit / len(one_million_scenarios)
```

这种计算没有必要把一百万个场景和完整控制流展开成巨大的模型表达式，适合通过 external function 接入。

最重要的职责区分是：

- **External function 解决表达能力和既有系统集成问题。**
- **Surrogate modeling 解决 external function 单次计算太昂贵、不能频繁调用的问题。**

如果计算能够用 Hexaly 原生算子清晰表达，应优先使用原生表达式。它能向求解器暴露更多数学结构、边界和增量计算机会。External function 对求解器而言是不透明黑盒，通常搜索信息更少，也会产生语言回调开销。



> **External function 提供的是“把 Hexaly 原生表达式之外的计算接入优化模型”的能力。**

这个外部计算可以来自：

- 当前 Python/C++/Java 进程中的普通函数或既有算法；
- 仿真器、有限元程序等外部软件；
- 第三方计算库；
- 机器学习模型；
- 数据库或远程服务接口。

不过，“external”主要表示该计算对 Hexaly 求解器是**不透明的黑盒**，并不意味着一定会启动外部软件或发起网络请求。例如：

```python
def calculate(args):
    x = args.get(0)
    return legacy_library.evaluate(x)

f = model.create_double_external_function(calculate)
result = model.call(f, x)
model.minimize(result)
```

这里 `legacy_library.evaluate()` 即使就在同一进程中，仍然属于 external function，因为 Hexaly 无法分析其内部计算结构。

还要注意：它不适合当作任意的“外部系统操作接口”。Hexaly 可能并行、多次、以不可预期的顺序调用它，也可能传入模型可行域之外的点。因此回调应当：

- 相同输入产生相同输出；
- 不依赖调用顺序；
- 不修改外部状态；
- 支持并发调用，或自行保证线程安全；
- 不执行下单、写数据库、发送通知等有副作用的操作；
- 能安全处理整个决策变量定义域内的输入。
