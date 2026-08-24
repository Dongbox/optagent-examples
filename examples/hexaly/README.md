
| 问题              | 核心结构                         | 新增难点          |
| --------------- | ---------------------------- | ------------- |
| CFLP            | `set + partition`            | 客户分配          |
| CVRP            | `list + partition`           | 客户分配 + 顺序     |
| CARP            | `list + disjoint + contains` | 边方向选择 + 顺序    |
| CVRPTW          | `list + 时间递推`                | 顺序 + 时间窗      |
| CVRPTW + Breaks | `list + 时间递推 + break`        | 时间传播过程中动态插入休息 |

## 运行

在仓库根目录安装本地包及开发依赖：

```bash
./.venv/bin/python -m pip install -e .
```

使用 Jupyter 打开任一 notebook：

```bash
./.venv/bin/jupyter notebook examples/examples/hexaly/<example>/<example>.ipynb
```

a–j 示例使用 `optagent` 的建模与结果读取接口；k–l 的原生 Hexaly 示例保留原生命周期，便于后续接口兼容对照。
